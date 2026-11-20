"""
No-show prediction experiment on D3 (Kaggle "Medical Appointment No Shows", Brazil 2016).

Protocol (report Section 3.6 "Patient No-Show Prediction")
  * Only information available AT BOOKING TIME is used:
      age, gender, scholarship, hypertension, diabetes, alcoholism, handicap,
      SMS reminder, lead time (days between booking and appointment),
      appointment weekday, booking hour, and the patient's appointment history
      (number of earlier appointments and earlier no-shows, counting only
      appointments that took place BEFORE this booking was made -> no future leakage)
  * Patient-wise 80:20 split (GroupShuffleSplit on PatientId) - no patient in both sets
  * 3-fold GroupKFold cross-validation, optimisation metric = average precision (PR-AUC)
  * Models: XGBoost, Random Forest, Logistic Regression; selected by CV PR-AUC
  * Test metrics: ROC-AUC, PR-AUC, Brier score, top-20% risk-bucket lift
  * Risk levels: Low / Medium / High from training-set score quantiles (50th, 80th)

Place the CSV at backend/data/d3/KaggleV2-May-2016.csv and run:
    python -m research.noshow_experiment
"""
from __future__ import annotations

import os
import sys
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, accuracy_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from research.common import DATA_DIR, MODELS_DIR, SEED, save_json

warnings.filterwarnings("ignore")
D3_PATH = os.path.join(DATA_DIR, "d3", "KaggleV2-May-2016.csv")

FEATURES = ["age", "female", "scholarship", "hypertension", "diabetes", "alcoholism", "handicap",
            "sms_received", "lead_days", "appt_weekday", "booking_hour", "prior_appointments",
            "prior_noshows", "prior_noshow_rate"]


def load_d3(path: str = D3_PATH):
    df = pd.read_csv(path)
    raw = len(df)
    df = df.rename(columns={"Hipertension": "Hypertension", "Handcap": "Handicap", "No-show": "NoShow"})
    df["ScheduledDay"] = pd.to_datetime(df["ScheduledDay"], utc=True)
    df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"], utc=True)
    df["lead_days"] = (df["AppointmentDay"].dt.normalize() - df["ScheduledDay"].dt.normalize()).dt.days
    invalid = (df["Age"] < 0) | (df["lead_days"] < 0)
    df = df[~invalid].copy()
    stats = {"raw_records": int(raw), "invalid_removed": int(invalid.sum()), "valid_records": int(len(df))}
    df["y"] = (df["NoShow"].astype(str).str.strip().str.lower() == "yes").astype(int)
    stats["no_show_rate"] = float(df["y"].mean())
    stats["patients"] = int(df["PatientId"].nunique())

    df["age"] = df["Age"]
    df["female"] = (df["Gender"] == "F").astype(int)
    df["scholarship"] = df["Scholarship"]
    df["hypertension"] = df["Hypertension"]
    df["diabetes"] = df["Diabetes"]
    df["alcoholism"] = df["Alcoholism"]
    df["handicap"] = (df["Handicap"] > 0).astype(int)
    df["sms_received"] = df["SMS_received"]
    df["appt_weekday"] = df["AppointmentDay"].dt.weekday
    df["booking_hour"] = df["ScheduledDay"].dt.hour

    # Appointment history known at booking time
    df = df.sort_values(["PatientId", "ScheduledDay"]).reset_index(drop=True)
    prior_n = np.zeros(len(df), dtype=int)
    prior_ns = np.zeros(len(df), dtype=int)
    for _, idx in df.groupby("PatientId").indices.items():
        sched = df["ScheduledDay"].values[idx]
        appt = df["AppointmentDay"].values[idx]
        ys = df["y"].values[idx]
        for k, i in enumerate(idx):
            done = appt < sched[k]  # appointments already completed before this booking
            done[k] = False
            prior_n[i] = int(done.sum())
            prior_ns[i] = int(ys[done].sum())
    df["prior_appointments"] = prior_n
    df["prior_noshows"] = prior_ns
    df["prior_noshow_rate"] = np.where(prior_n > 0, prior_ns / np.maximum(prior_n, 1), -1.0)
    return df, stats


def lift_top(p, y, frac=0.2):
    n = max(1, int(round(frac * len(p))))
    top = np.argsort(-p)[:n]
    return float(y[top].mean() / y.mean())


def run(path: str = D3_PATH, verbose: bool = True, label: str = "D3"):
    if not os.path.exists(path):
        msg = f"D3 not found at {path}. Download Kaggle 'Medical Appointment No Shows' and place it there."
        if verbose:
            print("[noshow] " + msg)
        save_json("noshow_results.json", {"status": "not_run", "message": msg})
        return None
    t0 = time.time()
    df, stats = load_d3(path)
    X = df[FEATURES].values.astype(float)
    y = df["y"].values
    g = df["PatientId"].values
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED).split(X, y, g))
    assert not set(g[tr]) & set(g[te]), "patient leakage"
    stats.update({"train_records": int(len(tr)), "test_records": int(len(te))})
    pos_w = float((y[tr] == 0).sum() / max(1, (y[tr] == 1).sum()))

    models = {
        "XGBoost": (XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=2, tree_method="hist"),
                    {"n_estimators": [300], "max_depth": [4, 6], "learning_rate": [0.05, 0.1], "subsample": [0.8]}),
        "Random Forest": (RandomForestClassifier(random_state=SEED, n_jobs=2),
                          {"n_estimators": [300], "max_depth": [10, 16], "min_samples_leaf": [5, 20]}),
        "Logistic Regression": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
                                {"logisticregression__C": [0.1, 1.0, 10.0]}),
    }
    cv = GroupKFold(n_splits=3)
    res, fitted = {}, {}
    for name, (est, grid) in models.items():
        if verbose:
            print(f"[noshow] {name} grid search ...", flush=True)
        gs = GridSearchCV(est, grid, cv=cv, scoring="average_precision", n_jobs=1)
        gs.fit(X[tr], y[tr], groups=g[tr])
        m = gs.best_estimator_
        p = m.predict_proba(X[te])[:, 1]
        res[name] = {"best_params": gs.best_params_, "cv_pr_auc": float(gs.best_score_),
                     "test": {"roc_auc": float(roc_auc_score(y[te], p)),
                              "pr_auc": float(average_precision_score(y[te], p)),
                              "brier": float(brier_score_loss(y[te], p)),
                              "lift_top20": lift_top(p, y[te]),
                              "accuracy_at_0.5": float(accuracy_score(y[te], p >= 0.5)),
                              "majority_class_accuracy": float(1 - y[te].mean())}}
        fitted[name] = m
    selected = max(res, key=lambda n: res[n]["cv_pr_auc"])
    model = fitted[selected]
    p_tr = model.predict_proba(X[tr])[:, 1]
    thr = {"medium": float(np.quantile(p_tr, 0.5)), "high": float(np.quantile(p_tr, 0.8))}
    p_te = model.predict_proba(X[te])[:, 1]
    lvl = np.where(p_te >= thr["high"], "High", np.where(p_te >= thr["medium"], "Medium", "Low"))
    buckets = {L: {"share": float((lvl == L).mean()), "observed_no_show_rate": float(y[te][lvl == L].mean())}
               for L in ("Low", "Medium", "High")}
    imp = None
    if hasattr(model, "feature_importances_"):
        imp = sorted(({"feature": f, "importance": float(v)} for f, v in zip(FEATURES, model.feature_importances_)),
                     key=lambda d: -d["importance"])
    joblib.dump({"model": model, "features": FEATURES, "thresholds": thr, "name": selected, "dataset": label},
                os.path.join(MODELS_DIR, "noshow_model.joblib"))
    out = {"status": "ok", "dataset": label, "data": stats, "models": res, "selected": selected,
           "selection_rule": "highest 3-fold GroupKFold PR-AUC on the training patients",
           "risk_thresholds": thr, "risk_buckets_test": buckets, "feature_importance": imp,
           "runtime_seconds": round(time.time() - t0, 1)}
    save_json("noshow_results.json", out)
    if verbose:
        for n, r in res.items():
            t = r["test"]
            print(f"[noshow] {n:20s} ROC-AUC {t['roc_auc']:.3f}  PR-AUC {t['pr_auc']:.3f}  Brier {t['brier']:.3f}  lift@20% {t['lift_top20']:.2f}")
        print(f"[noshow] selected {selected} in {out['runtime_seconds']} s")
    return out


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else D3_PATH)
