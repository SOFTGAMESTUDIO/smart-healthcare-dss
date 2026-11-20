"""
nn_diagnosis_service.py - Disease prediction service used by the app (report Section 3.6).

Model
  The deployed model is the scikit-learn Multilayer Perceptron selected by the
  research pipeline (research/disease_experiment.py): trained on the cleaned D1
  dataset (131 binary symptoms, unique patterns, 41 diseases), chosen by
  4-fold cross-validated macro-F1 with log-loss as tie-breaker.

Per prediction
  * probabilities for all 41 diseases, top-3 shown
  * uncertainty checks from the report: symptom count < 3, margin p1 - p2 < 0.20,
    normalised entropy > 0.50  ->  "needs clinical review" instead of a diagnosis
  * Kernel SHAP local explanation (15 background training observations)
  * rule-based triage computed INDEPENDENTLY of the model (department, priority, red flags)
  * clinical reasoning report: evidence for/against each differential, conclusion,
    investigations, management approach, safety-net advice
  * follow-up questions that best separate the leading candidates

Clinician feedback (report "future scope": feedback channels for clinicians)
  Confirmed diagnoses are stored. After AI_RETRAIN_EVERY confirmed cases the MLP is
  retrained on D1-train + confirmed cases and only ACCEPTED if accuracy on the fixed
  D1 test split and on held-out confirmed cases does not drop. Versions can be rolled back.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sqlite3
import sys
import threading
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

warnings.filterwarnings("ignore")
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.ml.clinical_reasoning import assess  # noqa: E402
from app.ml.disease_kb import SYMPTOM_GROUPS  # noqa: E402
from app.ml.symptom_dataset import full_disease_metadata, normalize_clinical, CLINICAL_FIELDS  # noqa: E402
from app.ml.triage_rules import triage  # noqa: E402

RESEARCH_DIR = os.path.join(BACKEND_DIR, "artifacts", "research")
MODEL_PATH = os.environ.get("AI_MODEL_PATH", os.path.join(RESEARCH_DIR, "disease_model.joblib"))
STATE_DIR = os.environ.get("AI_MODEL_DIR", os.path.join(BACKEND_DIR, "artifacts", "deployed"))
VERSIONS_DIR = os.path.join(STATE_DIR, "versions")
CURRENT_PATH = os.path.join(STATE_DIR, "current_model.joblib")
HISTORY_PATH = os.path.join(STATE_DIR, "training_history.json")
CASES_DB = os.path.join(STATE_DIR, "ai_cases.db")
RETRAIN_EVERY = int(os.environ.get("AI_RETRAIN_EVERY", "5"))
REAL_CASE_WEIGHT = 3.0
SHAP_NSAMPLES = int(os.environ.get("AI_SHAP_NSAMPLES", "300"))

ENGINE = "D1-trained MLP (scikit-learn) + Kernel SHAP + rule-based triage"
DISCLAIMER = ("Decision support only - not a medical diagnosis. The model is trained on a small public "
              "dataset (D1, ~300 unique symptom patterns) and must be validated on clinical data before use.")


def _metrics(model, X, y, K):
    from sklearn.metrics import accuracy_score, f1_score
    if len(y) == 0:
        return {"accuracy": None, "macro_f1": None, "top3_accuracy": None, "n": 0}
    p = model.predict_proba(X)
    pred = p.argmax(1)
    top3 = np.argsort(-p, axis=1)[:, :3]
    return {"accuracy": round(float(accuracy_score(y, pred)), 4),
            "macro_f1": round(float(f1_score(y, pred, average="macro", labels=np.unique(y), zero_division=0)), 4),
            "top3_accuracy": round(float(np.mean([y[i] in top3[i] for i in range(len(y))])), 4),
            "n": int(len(y))}


def _train_quick():
    """Train the deployed MLP if the research artifact is missing (same protocol, no grid search)."""
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier
    from sklearn.cluster import KMeans
    from research.d1_data import clean_d1, matrices
    df, _ = clean_d1()
    X, y, feats, classes = matrices(df)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    m = MLPClassifier(hidden_layer_sizes=(64,), alpha=1e-4, max_iter=2000, random_state=42).fit(Xtr, ytr)
    km = KMeans(n_clusters=15, n_init=10, random_state=42).fit(Xtr)
    bg = Xtr[sorted({int(np.argmin(((Xtr - c) ** 2).sum(1))) for c in km.cluster_centers_})]
    art = {"model": m, "features": feats, "classes": classes, "background": bg, "name": "MLP",
           "params": {"hidden_layer_sizes": [64], "alpha": 1e-4},
           "train_X": Xtr, "train_y": ytr, "test_X": Xte, "test_y": yte}
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    joblib.dump(art, MODEL_PATH)
    return art


class DiagnosisService:
    def __init__(self, verbose: bool = True):
        os.makedirs(VERSIONS_DIR, exist_ok=True)
        self.verbose = verbose
        self.lock = threading.RLock()
        self.retrain_lock = threading.Lock()
        self.retrain_status = {"running": False, "last_message": None}
        self.metadata = full_disease_metadata()
        self._init_db()

        if not os.path.exists(MODEL_PATH):
            self._log("[AI] Research model not found - training deployed MLP on D1 ...")
            _train_quick()
        base = joblib.load(MODEL_PATH)
        self.features: List[str] = base["features"]
        self.classes: List[str] = base["classes"]
        self.fidx = {f: i for i, f in enumerate(self.features)}
        self.cidx = {c: i for i, c in enumerate(self.classes)}
        self.background = base["background"]
        self.params = base["params"]
        self.Xtr, self.ytr, self.Xte, self.yte = base["train_X"], base["train_y"], base["test_X"], base["test_y"]
        self._d2 = self._load_d2()
        self.typical = self._typical_from_d1()

        self.history = self._load_history()
        if os.path.exists(CURRENT_PATH) and self.history:
            self.model = joblib.load(CURRENT_PATH)
        else:
            self.model = base["model"]
            joblib.dump(self.model, CURRENT_PATH)
            shutil.copy(CURRENT_PATH, os.path.join(VERSIONS_DIR, "model_v1.joblib"))
            self.history = [{"version": 1, "accepted": True, "kind": "base",
                             "timestamp": datetime.now().isoformat(timespec="seconds"),
                             "train_samples": int(len(self.ytr)), "real_cases": 0,
                             "benchmark": _metrics(self.model, self.Xte, self.yte, len(self.classes)),
                             "message": "MLP selected by the research pipeline (4-fold CV on D1)."}]
            self._save_history()
        self._explainer = None
        self._patterns_cache: Dict[int, Dict] = {}
        self._log(f"[AI] Diagnosis engine ready: {ENGINE}, model v{self.version}, "
                  f"{len(self.features)} symptoms, {len(self.classes)} diseases")

    # ------------------------------------------------------------ helpers
    def _log(self, m):
        if self.verbose:
            print(m)

    def _db(self):
        c = sqlite3.connect(CASES_DB, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self):
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS ai_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, patient_name TEXT,
                symptoms_json TEXT NOT NULL, clinical_json TEXT NOT NULL, predicted TEXT, confidence REAL,
                top3_json TEXT, model_version INTEGER, confirmed_diagnosis TEXT, confirmed_at TEXT,
                notes TEXT, used_in_version INTEGER)""")

    def _load_history(self):
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH) as f:
                return json.load(f)
        return []

    def _save_history(self):
        with open(HISTORY_PATH, "w") as f:
            json.dump(self.history, f, indent=1)

    @property
    def version(self) -> int:
        acc = [h for h in self.history if h.get("accepted")]
        return acc[-1]["version"] if acc else 1

    def _load_d2(self):
        try:
            from research.d1_data import load_descriptions
            return load_descriptions()
        except Exception:
            return {}

    def _typical_from_d1(self) -> Dict[str, List[tuple]]:
        """Symptom frequency per disease across the D1 patterns (data-driven 'typical findings')."""
        X = np.vstack([self.Xtr, self.Xte])
        y = np.concatenate([self.ytr, self.yte])
        out = {}
        for c, name in enumerate(self.classes):
            freq = X[y == c].mean(axis=0)
            order = np.argsort(-freq)
            out[name] = [(self.features[j], float(freq[j])) for j in order if freq[j] > 0]
        return out

    def encode(self, symptoms: List[str]) -> np.ndarray:
        x = np.zeros(len(self.features))
        for s in symptoms:
            if s in self.fidx:
                x[self.fidx[s]] = 1.0
        return x

    def _shap_explainer(self):
        if self._explainer is None:
            import shap
            self._explainer = shap.KernelExplainer(lambda X: self.model.predict_proba(X), self.background)
        return self._explainer

    def kernel_shap(self, x: np.ndarray, cls: int, nsamples: int = SHAP_NSAMPLES) -> np.ndarray:
        import shap
        with self.lock:
            model = self.model
        expl = shap.KernelExplainer(lambda X: model.predict_proba(X)[:, cls], self.background)
        return np.asarray(expl.shap_values(x[None, :], nsamples=nsamples, silent=True)).reshape(-1)

    # ---------------------------------------------------------- diagnose
    def diagnose(self, symptoms: List[str], clinical: Optional[dict] = None, patient_name: Optional[str] = None,
                 history_text: str = "", save: bool = True, explain: bool = True) -> Dict[str, Any]:
        raw_clin = {k: v for k, v in (clinical or {}).items() if v not in (None, "")}
        sym = [s for s in dict.fromkeys(symptoms or []) if s in self.fidx]
        unknown = [s for s in (symptoms or []) if s not in self.fidx]
        if not sym:
            return {"error": "Select at least one symptom from the catalog.", "unknown_symptoms": unknown,
                    "engine": ENGINE}
        clin = normalize_clinical(raw_clin)
        provided = set(raw_clin) | ({"gender_female"} if "gender" in raw_clin else set())

        with self.lock:
            model, version = self.model, self.version
        x = self.encode(sym)
        p = model.predict_proba(x[None, :])[0]
        order = np.argsort(-p)
        K = len(self.classes)
        p1, p2 = float(p[order[0]]), float(p[order[1]])
        margin = p1 - p2
        H = float(-(p * np.log(p + 1e-12)).sum() / math.log(K))
        reasons = []
        if len(sym) < 3:
            reasons.append(f"Sparse input: only {len(sym)} symptom(s) reported (minimum 3).")
        if margin < 0.20:
            reasons.append(f"Close differential: top two probabilities differ by {margin:.2f} (< 0.20).")
        if H > 0.50:
            reasons.append(f"Spread-out probabilities: normalised entropy {H:.2f} (> 0.50).")
        low = bool(reasons)

        top3 = []
        for i in order[:3]:
            d = self.classes[i]
            meta, d2 = self.metadata.get(d, {}), self._d2.get(d, {})
            hall = [s for s, f in self.typical[d] if f >= 0.8]
            top3.append({"disease": d, "probability": round(float(p[i]), 4), "percentage": round(float(p[i]) * 100, 1),
                         "department": meta.get("department", "General Medicine"), "urgency": meta.get("urgency", "Routine"),
                         "description": d2.get("description") or meta.get("description", ""),
                         "precautions": d2.get("precautions") or meta.get("precautions", []),
                         "matched_symptoms": [s for s in sym if any(s == t for t, _ in self.typical[d])],
                         "hallmark_symptoms": hall})

        # Kernel SHAP for the top class
        shap_items = []
        if explain:
            sv = self.kernel_shap(x, int(order[0]))
            idx = np.argsort(-np.abs(sv))
            for j in idx[:15]:
                if abs(sv[j]) < 1e-4:
                    break
                shap_items.append({"feature": self.features[j], "label": self.features[j].replace("_", " ").capitalize(),
                                   "present": bool(x[j]), "value": round(float(sv[j]), 4)})
        pos = [a for a in shap_items if a["value"] > 0][:6]
        neg = [a for a in shap_items if a["value"] < 0][:5]

        tri = triage(history_text, raw_clin, sym)
        probs = {self.classes[i]: float(p[i]) for i in range(K)}
        reasoning = assess(sym, clin, provided, probs, self.metadata, tri["red_flag_reasons"],
                           typical={d: [s for s, f in v] for d, v in self.typical.items()},
                           hallmarks={d: [s for s, f in v if f >= 0.8] for d, v in self.typical.items()})
        follow = self._follow_up(model, x, sym, [int(i) for i in order[:3]])

        if pos:
            names = ", ".join(a["label"].lower() for a in pos[:3])
            expl_text = (f"Kernel SHAP: {names} contributed most to the probability of {top3[0]['disease']} "
                         f"({top3[0]['percentage']}%).")
        else:
            expl_text = f"No single symptom dominates the prediction of {top3[0]['disease']}."

        result = {
            "engine": ENGINE, "prediction_id": None,
            "model": {"type": f"MLPClassifier {[len(self.features)] + list(model.hidden_layer_sizes) + [K]}",
                      "version": version, "trained_on": "D1 (cleaned, unique patterns)",
                      "test_accuracy": self.history[-1]["benchmark"]["accuracy"] if self.history else None},
            "top3_predictions": top3,
            "all_probabilities": [{"disease": self.classes[i], "probability": round(float(p[i]), 5)} for i in order],
            "confidence_level": "High" if (p1 >= 0.8 and not low) else "Moderate" if p1 >= 0.5 else "Low",
            "margin_delta": round(margin, 4), "normalized_entropy": round(H, 4), "symptom_count": len(sym),
            "low_confidence": low,
            "clinical_status": "Needs clinical review" if low else "High confidence suggestion",
            "low_confidence_reasons": reasons,
            "triage": tri, "red_flags": tri["red_flag_reasons"],
            "explanation_text": expl_text,
            "shap_attribution": {"method": f"Kernel SHAP (background={len(self.background)}, nsamples={SHAP_NSAMPLES})",
                                 "explained_output": f"P({top3[0]['disease']})",
                                 "positive": [{"feature": a["feature"], "value": a["value"]} for a in pos],
                                 "negative": [{"feature": a["feature"], "value": a["value"]} for a in neg],
                                 "all_local": {a["feature"]: a["value"] for a in shap_items[:10]},
                                 "items": shap_items},
            "clinical_reasoning": reasoning,
            "follow_up_questions": follow,
            "inputs_used": {"symptoms": sym, "clinical": raw_clin, "ignored_unknown_symptoms": unknown,
                            "note": "Vitals are used by triage/red flags and the reasoning report; the D1 model uses symptoms only."},
            "disclaimer": DISCLAIMER,
        }
        if save:
            with self._db() as c:
                cur = c.execute("""INSERT INTO ai_cases (created_at, patient_name, symptoms_json, clinical_json, predicted,
                                   confidence, top3_json, model_version) VALUES (?,?,?,?,?,?,?,?)""",
                                (datetime.now().isoformat(timespec="seconds"), patient_name, json.dumps(sym),
                                 json.dumps(raw_clin), top3[0]["disease"], p1,
                                 json.dumps([{"disease": t["disease"], "probability": t["probability"]} for t in top3]), version))
                result["prediction_id"] = cur.lastrowid
        return result

    def _follow_up(self, model, x, sym, top_idx):
        cands = []
        for i in top_idx:
            for s, f in self.typical[self.classes[i]]:
                if f >= 0.3 and s not in sym and s not in cands:
                    cands.append(s)
        if not cands:
            return []
        V = np.repeat(x[None, :], len(cands), axis=0)
        for r, s in enumerate(cands):
            V[r, self.fidx[s]] = 1
        P = model.predict_proba(V)
        p0 = model.predict_proba(x[None, :])[0]
        a, b = top_idx[0], top_idx[1]
        base = math.log(p0[a] + 1e-9) - math.log(p0[b] + 1e-9)
        out = []
        for r, s in enumerate(cands):
            shift = (math.log(P[r, a] + 1e-9) - math.log(P[r, b] + 1e-9)) - base
            out.append({"symptom": s, "question": f"Does the patient have {s.replace('_', ' ')}?",
                        "if_yes_favours": self.classes[int(np.argmax(P[r]))],
                        "if_yes_top_probability": round(float(P[r].max()), 3), "discrimination": round(abs(shift), 3)})
        return sorted(out, key=lambda o: -o["discrimination"])[:5]

    # ----------------------------------------------------- learned patterns
    def learned_patterns(self, disease: Optional[str] = None, top_k: int = 8) -> dict:
        """Kernel SHAP averaged over the D1 patterns of each disease (what the model relies on)."""
        v = self.version
        cache = self._patterns_cache.setdefault(v, {})
        names = [disease] if disease else self.classes
        for d in names:
            if d not in self.cidx:
                return {"error": f"Unknown disease '{d}'"}
            if d in cache:
                continue
            ci = self.cidx[d]
            X = np.vstack([self.Xtr, self.Xte])
            y = np.concatenate([self.ytr, self.yte])
            Xd = X[y == ci]
            import shap
            with self.lock:
                model = self.model
            expl = shap.KernelExplainer(lambda Z: model.predict_proba(Z)[:, ci], self.background)
            sv = np.asarray(expl.shap_values(Xd, nsamples=200, silent=True)).reshape(len(Xd), -1)
            mean = sv.mean(axis=0)
            order = np.argsort(-mean)
            cache[d] = {"accuracy_on_d1_patterns": round(float((model.predict(Xd) == ci).mean()), 3),
                        "patterns": int(len(Xd)),
                        "top_features": [{"feature": self.features[j], "label": self.features[j].replace("_", " "),
                                          "type": "symptom", "importance": round(float(mean[j]), 4),
                                          "frequency_in_d1": round(float(Xd[:, j].mean()), 2)}
                                         for j in order[:12] if mean[j] > 0.002]}
        if disease:
            t = cache[disease]
            return {"version": v, "disease": disease, "method": "mean Kernel SHAP over D1 patterns",
                    "accuracy_on_benchmark": t["accuracy_on_d1_patterns"], **t, "top_features": t["top_features"][:top_k]}
        return {"version": v, "diseases": {d: cache[d] for d in names}}

    # ------------------------------------------------- feedback / retrain
    def feedback(self, prediction_id, confirmed_diagnosis, notes="", symptoms=None, clinical=None):
        if confirmed_diagnosis not in self.cidx and confirmed_diagnosis != "Other":
            return {"ok": False, "message": f"Unknown diagnosis '{confirmed_diagnosis}'."}
        now = datetime.now().isoformat(timespec="seconds")
        with self._db() as c:
            if prediction_id:
                if not c.execute("SELECT id FROM ai_cases WHERE id=?", (int(prediction_id),)).fetchone():
                    return {"ok": False, "message": f"Prediction {prediction_id} not found."}
                c.execute("UPDATE ai_cases SET confirmed_diagnosis=?, confirmed_at=?, notes=?, used_in_version=NULL WHERE id=?",
                          (confirmed_diagnosis, now, notes, int(prediction_id)))
                case_id = int(prediction_id)
            else:
                sym = [s for s in (symptoms or []) if s in self.fidx]
                if not sym:
                    return {"ok": False, "message": "Provide prediction_id or symptoms."}
                cur = c.execute("""INSERT INTO ai_cases (created_at, symptoms_json, clinical_json, confirmed_diagnosis,
                                   confirmed_at, notes) VALUES (?,?,?,?,?,?)""",
                                (now, json.dumps(sym), json.dumps(clinical or {}), confirmed_diagnosis, now, notes))
                case_id = cur.lastrowid
        pending = self.pending_count()
        trig = False
        if confirmed_diagnosis != "Other" and pending >= RETRAIN_EVERY and not self.retrain_status["running"]:
            threading.Thread(target=self.retrain, args=(f"auto: {pending} new confirmed cases",), daemon=True).start()
            trig = True
        return {"ok": True, "case_id": case_id, "pending_cases": pending, "retrain_every": RETRAIN_EVERY,
                "self_training_triggered": trig,
                "message": ("Case saved. Retraining started in the background." if trig else
                            f"Case saved. The model retrains after {max(0, RETRAIN_EVERY - pending)} more confirmed case(s).")}

    def pending_count(self):
        with self._db() as c:
            return c.execute("SELECT COUNT(*) FROM ai_cases WHERE confirmed_diagnosis IS NOT NULL "
                             "AND confirmed_diagnosis != 'Other' AND used_in_version IS NULL").fetchone()[0]

    def retrain(self, reason="manual"):
        if not self.retrain_lock.acquire(blocking=False):
            return {"started": False, "message": "A retraining run is already in progress."}
        self.retrain_status = {"running": True, "last_message": "Training ..."}
        try:
            from sklearn.base import clone
            with self._db() as c:
                rows = c.execute("SELECT * FROM ai_cases WHERE confirmed_diagnosis IS NOT NULL ORDER BY id").fetchall()
            rows = [r for r in rows if r["confirmed_diagnosis"] in self.cidx]
            if not rows:
                msg = "No clinician-confirmed cases yet - nothing new to learn."
                self.retrain_status = {"running": False, "last_message": msg}
                return {"started": False, "message": msg}
            Xr = np.array([self.encode(json.loads(r["symptoms_json"])) for r in rows])
            yr = np.array([self.cidx[r["confirmed_diagnosis"]] for r in rows])
            ids = np.array([r["id"] for r in rows])
            hold = (ids % 5 == 0) if len(rows) >= 10 else np.zeros(len(rows), bool)
            X = np.vstack([self.Xtr, Xr[~hold]])
            y = np.concatenate([self.ytr, yr[~hold]])
            w = np.concatenate([np.ones(len(self.ytr)), np.full(int((~hold).sum()), REAL_CASE_WEIGHT)])
            with self.lock:
                current = self.model
            cand = clone(current)
            cand.fit(X, y, sample_weight=w)
            K = len(self.classes)
            cb, nb = _metrics(current, self.Xte, self.yte, K), _metrics(cand, self.Xte, self.yte, K)
            cr, nr = _metrics(current, Xr[hold], yr[hold], K), _metrics(cand, Xr[hold], yr[hold], K)
            ok = nb["accuracy"] >= cb["accuracy"] - 0.02 and (nr["n"] == 0 or nr["accuracy"] >= cr["accuracy"])
            newv = self.version + 1
            if ok:
                msg = (f"Accepted v{newv}: learned from {int((~hold).sum())} confirmed case(s). "
                       f"D1 test accuracy {cb['accuracy']:.3f} -> {nb['accuracy']:.3f}"
                       + (f"; held-out confirmed cases {cr['accuracy']:.3f} -> {nr['accuracy']:.3f}" if nr["n"] else ""))
            else:
                msg = f"Rejected candidate (accuracy would drop); keeping v{self.version}."
            self.history.append({"version": newv if ok else None, "accepted": ok, "kind": "clinician-feedback",
                                 "reason": reason, "timestamp": datetime.now().isoformat(timespec="seconds"),
                                 "train_samples": int(len(y)), "real_cases": int((~hold).sum()),
                                 "benchmark": nb, "benchmark_before": cb, "real_holdout": nr, "message": msg})
            self._save_history()
            if ok:
                with self.lock:
                    self.model = cand
                    joblib.dump(cand, CURRENT_PATH)
                    shutil.copy(CURRENT_PATH, os.path.join(VERSIONS_DIR, f"model_v{newv}.joblib"))
                with self._db() as c:
                    c.executemany("UPDATE ai_cases SET used_in_version=? WHERE id=? AND used_in_version IS NULL",
                                  [(newv, int(i)) for i in ids])
            self._log("[AI] " + msg)
            self.retrain_status = {"running": False, "last_message": msg}
            return {"started": True, "accepted": ok, "message": msg}
        except Exception as e:
            self.retrain_status = {"running": False, "last_message": f"Retraining failed: {e}"}
            raise
        finally:
            self.retrain_lock.release()

    def retrain_async(self, reason):
        threading.Thread(target=self.retrain, args=(reason,), daemon=True).start()

    def rollback(self, version: int):
        path = os.path.join(VERSIONS_DIR, f"model_v{int(version)}.joblib")
        if not os.path.exists(path):
            return {"ok": False, "message": f"Version {version} not found."}
        with self.lock:
            shutil.copy(path, CURRENT_PATH)
            self.model = joblib.load(CURRENT_PATH)
        b = _metrics(self.model, self.Xte, self.yte, len(self.classes))
        self.history.append({"version": int(version), "accepted": True, "kind": "rollback",
                             "timestamp": datetime.now().isoformat(timespec="seconds"), "benchmark": b,
                             "message": f"Rolled back to v{version}."})
        self._save_history()
        return {"ok": True, "message": f"Now serving v{version}.", "benchmark": b}

    # -------------------------------------------------------------- info
    def model_info(self):
        from research.common import load_json
        res = load_json("disease_results.json") or {}
        with self._db() as c:
            total = c.execute("SELECT COUNT(*) FROM ai_cases").fetchone()[0]
            conf = c.execute("SELECT COUNT(*) FROM ai_cases WHERE confirmed_diagnosis IS NOT NULL").fetchone()[0]
            agree = c.execute("SELECT COUNT(*) FROM ai_cases WHERE confirmed_diagnosis IS NOT NULL AND predicted=confirmed_diagnosis").fetchone()[0]
            wp = c.execute("SELECT COUNT(*) FROM ai_cases WHERE confirmed_diagnosis IS NOT NULL AND predicted IS NOT NULL").fetchone()[0]
        m = self.model
        cur = next((h for h in reversed(self.history) if h.get("accepted")), {})
        mlp = (res.get("models") or {}).get("MLP", {})
        return {
            "engine": ENGINE,
            "architecture": {"type": "Multilayer Perceptron (scikit-learn)",
                             "layers": [len(self.features), *m.hidden_layer_sizes, len(self.classes)],
                             "activation": m.activation, "output": "Softmax", "optimizer": m.solver,
                             "regularisation": f"L2 alpha={m.alpha}",
                             "parameters": int(sum(w.size for w in m.coefs_) + sum(b.size for b in m.intercepts_)),
                             "selected_by": (res.get("selection") or {}).get("rule")},
            "inputs": {"symptoms": len(self.features), "clinical": [f[4] for f in CLINICAL_FIELDS],
                       "note": "vitals feed triage, red flags and the reasoning report"},
            "diseases": len(self.classes), "version": self.version,
            "benchmark": cur.get("benchmark"),
            "research_metrics": {"cv_macro_f1": mlp.get("cv_macro_f1"), "cv_log_loss": mlp.get("cv_log_loss"),
                                 "test": mlp.get("test"), "repeated_splits": mlp.get("repeated_splits"),
                                 "robustness": mlp.get("robustness")},
            "real_cases": {"total_predictions": total, "confirmed": conf, "pending_for_training": self.pending_count(),
                           "retrain_every": RETRAIN_EVERY, "live_agreement": round(agree / wp, 3) if wp else None},
            "retrain_status": self.retrain_status,
            "history": [{k: h.get(k) for k in ("version", "accepted", "kind", "reason", "timestamp", "train_samples",
                                               "real_cases", "benchmark", "real_holdout", "message")} for h in self.history],
            "last_training_curve": {"epoch": list(range(1, len(m.loss_curve_) + 1)), "train_loss": [round(v, 4) for v in m.loss_curve_],
                                    "val_loss": None} if hasattr(m, "loss_curve_") else None,
        }

    def schema(self):
        groups = {g: [s for s in v if s in self.fidx] for g, v in SYMPTOM_GROUPS.items()}
        return {"symptom_groups": groups, "all_symptoms": sorted(self.features), "diseases": sorted(self.classes),
                "clinical_fields": [{"name": n, "default": d, "label": lab, "unit": u} for n, d, _c, _s, lab, u in CLINICAL_FIELDS]}

    def recent_cases(self, limit=20):
        with self._db() as c:
            rows = c.execute("SELECT * FROM ai_cases ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [{"id": r["id"], "created_at": r["created_at"], "patient_name": r["patient_name"],
                 "symptoms": json.loads(r["symptoms_json"]), "predicted": r["predicted"], "confidence": r["confidence"],
                 "confirmed_diagnosis": r["confirmed_diagnosis"], "model_version": r["model_version"],
                 "used_in_version": r["used_in_version"]} for r in rows]


# Backward-compatible names
NeuralDiagnosisService = DiagnosisService
_service: Optional[DiagnosisService] = None
_lock = threading.Lock()


def get_nn_service() -> DiagnosisService:
    global _service
    with _lock:
        if _service is None:
            _service = DiagnosisService()
    return _service
