"""
server.py – Standalone, high-performance HTTP server for MediXAI Decision Support System.
Uses Python standard library (http.server, sqlite3, json, base64, hashlib, urllib) for 100% zero-dependency execution.
Supports:
  - Full REST API (/api/auth, /api/patients, /api/appointments, /api/analytics, /api/health)
  - Full CORS for React frontend on http://localhost:5173
  - Optional static file serving of built frontend dist/
"""
import sys
import os
import json
import sqlite3
import base64
import hashlib
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from app.ml.prediction_service import prediction_service
from app.ml.nn_diagnosis_service import get_nn_service
from app.ml.noshow_model import get_noshow_service
from research.common import load_json, FIG_DIR
from app.ml.disease_kb import SYMPTOMS_131, SYMPTOM_GROUPS, DISEASES_41
from app.ml.triage_rules import triage
from app.scheduler.optimizer import scheduler
from app.scheduler.simulation_service import simulation_service
from init_local_db import DB_PATH
from app.secure_store import (encrypt_field, decrypt_field, migrate_db, verify_password, hash_password,
                              issue_token, verify_token)

FRONTEND_DIST = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend", "dist"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def decrypt_val(val):
    return decrypt_field(val)


ROLE_STAFF = ("physician", "admin")


def required_roles(method: str, path: str):
    """Role-based access policy. None = public, () = any authenticated user."""
    if not path.startswith("/api/") or path in ("/api/health", "/api/auth/login"):
        return None
    if path.startswith("/api/research/figures/"):  # aggregate research charts, no patient data
        return None
    if (method == "POST" and path == "/api/ai/rollback") or (method == "DELETE" and path.startswith("/api/patients")):
        return ("admin",)
    staff_prefixes = ("/api/patients", "/api/appointments", "/api/analytics/summary",
                      "/api/analytics/triage-distribution", "/api/ai/cases", "/api/ai/model-info")
    if path.startswith(staff_prefixes) or (method == "POST" and path in ("/api/ai/feedback", "/api/ai/retrain")):
        return ROLE_STAFF
    return ()


class MediXAIHandler(BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Allow-Credentials", "true")

    def _guard(self, method, path):
        """Returns the authenticated user dict, None for public routes, or False after sending 401/403."""
        roles = required_roles(method, path)
        if roles is None:
            return None
        auth = self.headers.get("Authorization", "")
        user = verify_token(auth[7:]) if auth.startswith("Bearer ") else None
        if not user:
            self._send_json({"detail": "Not authenticated"}, status=401)
            return False
        if roles and user.get("role") not in roles:
            self._send_json({"detail": f"Forbidden for role '{user.get('role')}'"}, status=403)
            return False
        return user

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                return json.loads(raw)
            except Exception:
                return {}
        elif "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(raw)
            return {k: v[0] for k, v in parsed.items()}
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._guard("GET", path)
        if user is False:
            return
        query = parse_qs(parsed.query)

        # Health
        if path == "/api/health":
            svc = get_nn_service()
            return self._send_json({"status": "healthy", "ml_loaded": True, "wal_active": True,
                                    "ai_engine": svc.model_info()["engine"], "model_version": svc.version,
                                    "noshow_model": "trained" if get_noshow_service().trained else "not trained (add D3)",
                                    "research_results": {k: load_json(k) is not None for k in
                                                         ("disease_results.json", "noshow_results.json", "scheduling_results.json")}})

        # Auth Me
        if path == "/api/auth/me":
            return self._send_json({"username": user["sub"], "role": user["role"], "user_id": user["id"]})

        # Patients List
        if path in ["/api/patients", "/api/patients/"]:
            conn = get_db()
            rows = conn.execute("SELECT * FROM patients ORDER BY id ASC").fetchall()
            conn.close()
            result = []
            for r in rows:
                d = dict(r)
                d["name"] = decrypt_val(d.get("encrypted_name"))
                d["phone"] = decrypt_val(d.get("encrypted_phone"))
                try:
                    d["shap_values"] = json.loads(d["shap_values_json"]) if d.get("shap_values_json") else {}
                except Exception:
                    d["shap_values"] = {}
                result.append(d)
            return self._send_json(result)

        # Patient Detail
        if path.startswith("/api/patients/") and not path.endswith("/predict"):
            try:
                pid = int(path.split("/")[3])
                conn = get_db()
                r = conn.execute("SELECT * FROM patients WHERE id = ?", (pid,)).fetchone()
                conn.close()
                if not r:
                    return self._send_json({"detail": "Patient not found"}, status=404)
                d = dict(r)
                d["name"] = decrypt_val(d.get("encrypted_name"))
                d["phone"] = decrypt_val(d.get("encrypted_phone"))
                try:
                    d["shap_values"] = json.loads(d["shap_values_json"]) if d.get("shap_values_json") else {}
                except Exception:
                    d["shap_values"] = {}
                return self._send_json(d)
            except Exception as e:
                return self._send_json({"detail": str(e)}, status=400)

        # Appointments List
        if path in ["/api/appointments", "/api/appointments/"]:
            conn = get_db()
            rows = conn.execute("""
                SELECT a.*, d.name as doctor_name, d.specialization as doctor_specialization
                FROM appointments a
                LEFT JOIN doctors d ON a.doctor_id = d.id
                ORDER BY a.slot_datetime ASC
            """).fetchall()
            conn.close()
            return self._send_json([dict(r) for r in rows])

        # Doctors List
        if path == "/api/appointments/doctors":
            conn = get_db()
            docs = conn.execute("SELECT * FROM doctors").fetchall()
            conn.close()
            return self._send_json([dict(d) for r in docs])

        # Analytics Summary
        if path == "/api/analytics/summary":
            conn = get_db()
            total = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
            high = conn.execute("SELECT COUNT(*) FROM patients WHERE risk_score >= 0.7").fetchone()[0]
            med = conn.execute("SELECT COUNT(*) FROM patients WHERE risk_score >= 0.4 AND risk_score < 0.7").fetchone()[0]
            low = conn.execute("SELECT COUNT(*) FROM patients WHERE risk_score < 0.4").fetchone()[0]
            pos = conn.execute("SELECT COUNT(*) FROM patients WHERE disease_predicted = 1").fetchone()[0]
            total_appts = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
            sched_appts = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'scheduled'").fetchone()[0]
            high_ns = conn.execute("SELECT COUNT(*) FROM patients WHERE noshow_risk = 'High'").fetchone()[0]
            conn.close()

            return self._send_json({
                "total_patients": total,
                "disease_positive": pos,
                "disease_negative": total - pos,
                "high_risk": high,
                "medium_risk": med,
                "low_risk": low,
                "total_appointments": total_appts,
                "scheduled_appointments": sched_appts,
                "high_noshow_risk": high_ns,
                "risk_distribution": [
                    {"name": "High Risk", "value": high, "color": "#ef4444"},
                    {"name": "Medium Risk", "value": med, "color": "#f59e0b"},
                    {"name": "Low Risk", "value": low, "color": "#10b981"},
                ]
            })

        # Feature Importance / Global SHAP -> computed Kernel SHAP of the deployed MLP (research pipeline)
        if path in ("/api/analytics/feature-importance", "/api/analytics/shap-global"):
            d = load_json("disease_results.json")
            if not d:
                return self._send_json({"detail": "Run python -m research.run_all first."}, status=503)
            g = d["shap"]["global_top20"]
            if path.endswith("feature-importance"):
                return self._send_json({"method": d["shap"]["method"], "features": [
                    {"feature": x["feature"].replace("_", " ").upper(), "importance": round(x["mean_abs_shap"], 4)} for x in g[:10]]})
            return self._send_json({"method": d["shap"]["method"], "patients_analyzed": d["split"]["test"],
                                    "mean_shap": [{"feature": x["feature"].replace("_", " ").upper(),
                                                   "mean_abs_shap": round(x["mean_abs_shap"], 4)} for x in g[:10]]})

        # Research results (all computed by research/run_all.py)
        if path == "/api/research/results":
            figs = sorted(f for f in os.listdir(FIG_DIR) if f.endswith(".png")) if os.path.isdir(FIG_DIR) else []
            return self._send_json({"disease": load_json("disease_results.json"),
                                    "noshow": load_json("noshow_results.json"),
                                    "scheduling": load_json("scheduling_results.json"), "figures": figs})
        if path.startswith("/api/research/figures/"):
            name = os.path.basename(path)
            fp = os.path.join(FIG_DIR, name)
            if not name.endswith(".png") or not os.path.isfile(fp):
                return self._send_json({"detail": "Not found"}, status=404)
            with open(fp, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(content)
            return

        # Triage Distribution
        if path == "/api/analytics/triage-distribution":
            conn = get_db()
            rows = conn.execute("SELECT triage_dept, COUNT(*) as cnt FROM patients GROUP BY triage_dept").fetchall()
            conn.close()
            return self._send_json([{"department": r["triage_dept"] or "General", "count": r["cnt"]} for r in rows])

        # Global SHAP
        if path == "/api/analytics/shap-global":
            return self._send_json({
                "mean_shap": [
                    {"feature": "BLOOD PRESSURE", "mean_abs_shap": 0.185},
                    {"feature": "CHEST PAIN TYPE", "mean_abs_shap": 0.162},
                    {"feature": "AGE", "mean_abs_shap": 0.141},
                    {"feature": "CHOLESTEROL", "mean_abs_shap": 0.118},
                    {"feature": "SMOKING", "mean_abs_shap": 0.095},
                ],
                "patients_analyzed": 8
            })

        # ---------------- Neural network AI diagnosis (GET) ----------------
        if path == "/api/ai/schema":
            return self._send_json(get_nn_service().schema())
        if path == "/api/ai/model-info":
            return self._send_json(get_nn_service().model_info())
        if path == "/api/ai/patterns":
            disease = query.get("disease", [None])[0]
            top_k = int(query.get("top_k", [8])[0])
            return self._send_json(get_nn_service().learned_patterns(disease, top_k))
        if path == "/api/ai/cases":
            limit = int(query.get("limit", [20])[0])
            return self._send_json(get_nn_service().recent_cases(limit))

        # Symptoms 131 Catalog
        if path == "/api/analytics/symptoms-131":
            return self._send_json({
                "total_symptoms": len(SYMPTOMS_131),
                "total_diseases": len(DISEASES_41),
                "grouped_symptoms": SYMPTOM_GROUPS,
                "all_symptoms": sorted(SYMPTOMS_131),
                "all_diseases": sorted(DISEASES_41),
            })

        # Simulation
        if path == "/api/analytics/simulate":
            demand_val = float(query.get("demand", [1.0])[0])
            return self._send_json(simulation_service.run_simulation(demand_val))

        # Static frontend fallback
        if os.path.exists(FRONTEND_DIST):
            rel_path = path.lstrip("/") or "index.html"
            file_path = os.path.realpath(os.path.join(FRONTEND_DIST, rel_path))
            if not file_path.startswith(FRONTEND_DIST + os.sep) or not os.path.isfile(file_path):
                file_path = os.path.join(FRONTEND_DIST, "index.html")
            
            content_type = "text/html"
            if file_path.endswith(".js"): content_type = "application/javascript"
            elif file_path.endswith(".css"): content_type = "text/css"
            elif file_path.endswith(".svg"): content_type = "image/svg+xml"

            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(content)
            return

        self._send_json({"detail": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._guard("POST", path)
        if user is False:
            return
        body = self._read_body()

        # Auth Login
        if path == "/api/auth/login":
            username = str(body.get("username") or "").strip()
            password = str(body.get("password") or "").strip()
            print(f"[Auth] Login request for: '{username}'")

            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)",
                (username, username)
            ).fetchone()
            valid, upgrade = verify_password(password, user["hashed_password"]) if user else (False, False)
            if valid and upgrade:  # migrate legacy SHA-256 hash to PBKDF2
                conn.execute("UPDATE users SET hashed_password=? WHERE id=?", (hash_password(password), user["id"]))
                conn.commit()
            conn.close()

            if not user or not valid:
                print(f"[Auth] Authentication rejected for: '{username}'")
                return self._send_json({"detail": "Invalid username or password"}, status=401)

            print(f"[Auth] Authenticated user: '{user['username']}' (role: {user['role']})")
            b64_token = issue_token(user["id"], user["username"], user["role"])

            return self._send_json({
                "access_token": b64_token,
                "token_type": "bearer",
                "role": user["role"],
                "username": user["username"]
            })

        # Predict Symptoms 131 (now served by the neural network)
        if path == "/api/analytics/predict-symptoms":
            symptoms = body.get("symptoms", [])
            res = prediction_service.predict_symptoms(symptoms, body.get("clinical") or {})
            return self._send_json(res, status=400 if "error" in res else 200)

        # ---------------- Neural network AI diagnosis (POST) ----------------
        if path == "/api/ai/diagnose":
            res = get_nn_service().diagnose(body.get("symptoms", []), body.get("clinical") or {},
                                            patient_name=body.get("patient_name"),
                                            history_text=body.get("history_text", ""))
            return self._send_json(res, status=400 if "error" in res else 200)
        if path == "/api/ai/feedback":
            res = get_nn_service().feedback(body.get("prediction_id"), body.get("confirmed_diagnosis", ""),
                                            body.get("notes", ""), body.get("symptoms"), body.get("clinical"))
            return self._send_json(res, status=200 if res.get("ok") else 400)
        if path == "/api/ai/retrain":
            svc = get_nn_service()
            if body.get("background"):
                svc.retrain_async("manual")
                return self._send_json({"started": True, "message": "Retraining started in background."})
            res = svc.retrain("manual")
            res.pop("entry", None)
            return self._send_json(res)
        if path == "/api/ai/rollback":
            return self._send_json(get_nn_service().rollback(int(body.get("version", 1))))

        # Create Patient
        if path in ["/api/patients", "/api/patients/"]:
            conn = get_db()
            raw_name = body.get("name", "Unknown")
            enc_name = encrypt_field(raw_name)
            enc_phone = encrypt_field(body.get("phone", ""))
            
            # Appointment priority comes from rule-based triage (independent of any classifier);
            # no-show risk from the D3 model; SHAP from the D1 disease model when symptoms are given.
            age = int(body.get("age", 40))
            bp = float(body.get("blood_pressure", 120))
            smoking = int(body.get("smoking", 0))
            vitals = {"blood_pressure": bp, "systolic_bp": bp, "blood_sugar": float(body.get("blood_sugar", 100)),
                      "bmi": float(body.get("bmi", 25))}
            sym_list = body.get("symptoms") or []
            triage_res = triage(body.get("symptoms_text", ""), vitals, sym_list)
            dept = triage_res["department"]
            base = {"Urgent": 0.85, "High": 0.6, "Routine": 0.3}[triage_res["priority"]]
            risk_score = round(min(0.99, base + min(0.14, triage_res["severity_score"] / 300)), 3)
            ns = get_noshow_service().predict(age=age, female=int(str(body.get("gender", "M")).upper().startswith("F")),
                                              lead_days=float(body.get("lead_days", 3)),
                                              sms_received=int(body.get("sms_received", 0)))
            noshow = ns["risk_level"]
            shap_json, pred = {}, 0
            if sym_list:
                dres = get_nn_service().diagnose(sym_list, {"age": age, "systolic_bp": bp}, patient_name=raw_name,
                                                 history_text=body.get("symptoms_text", ""))
                if "error" not in dres:
                    shap_json = dres["shap_attribution"]["all_local"]
                    pred = 0 if dres["low_confidence"] else 1

            cur = conn.cursor()
            cur.execute("""
                INSERT INTO patients (
                    encrypted_name, encrypted_phone, age, gender,
                    blood_pressure, cholesterol, blood_sugar, bmi,
                    smoking, family_history, chest_pain_type, ecg_result,
                    symptoms_text, disease_predicted, risk_score, noshow_risk,
                    triage_dept, shap_values_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                enc_name, enc_phone, age, body.get("gender", "M"),
                bp, float(body.get("cholesterol", 200)), float(body.get("blood_sugar", 100)), float(body.get("bmi", 25)),
                smoking, int(body.get("family_history", 0)), int(body.get("chest_pain_type", 0)), int(body.get("ecg_result", 0)),
                body.get("symptoms_text", ""), pred, risk_score, noshow,
                dept, json.dumps(shap_json)
            ))
            pid = cur.lastrowid
            conn.commit()
            conn.close()

            return self._send_json({
                "id": pid, "name": raw_name, "risk_score": risk_score,
                "disease_predicted": pred, "noshow_risk": noshow, "noshow": ns, "triage_dept": dept,
                "triage": triage_res
            }, status=201)

        # Schedule Appointments (OR-Tools / C(t))
        if path == "/api/appointments/schedule":
            patient_ids = body.get("patient_ids", [])
            conn = get_db()
            patients_rows = conn.execute("SELECT * FROM patients WHERE id IN ({})".format(
                ",".join("?" * len(patient_ids))
            ), patient_ids).fetchall() if patient_ids else []
            doctors_rows = conn.execute("SELECT * FROM doctors").fetchall()
            existing_rows = conn.execute("SELECT * FROM appointments WHERE status = 'scheduled'").fetchall()

            reqs = [{"patient_id": r["id"], "risk_score": r["risk_score"] or 0.5} for r in patients_rows]
            docs = [{"id": d["id"], "name": d["name"], "specialization": d["specialization"]} for d in doctors_rows]
            existing = [{"doctor_id": e["doctor_id"], "slot_datetime": e["slot_datetime"]} for e in existing_rows]

            assignments = scheduler.schedule(reqs, docs, existing)

            cur = conn.cursor()
            for a in assignments:
                cur.execute("""
                    INSERT INTO appointments (patient_id, doctor_id, slot_datetime, priority_score, status)
                    VALUES (?, ?, ?, ?, 'scheduled')
                """, (a["patient_id"], a["doctor_id"], a["slot_datetime"], a["priority_score"]))
            conn.commit()
            conn.close()

            return self._send_json({"scheduled": len(assignments), "assignments": assignments})

        self._send_json({"detail": "Not found"}, status=404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._guard("PATCH", path)
        if user is False:
            return
        body = self._read_body()

        if path.startswith("/api/appointments/"):
            try:
                aid = int(path.split("/")[3])
                status_val = body.get("status")
                conn = get_db()
                conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (status_val, aid))
                conn.commit()
                conn.close()
                return self._send_json({"message": "Updated", "appointment_id": aid})
            except Exception as e:
                return self._send_json({"detail": str(e)}, status=400)

        self._send_json({"detail": "Not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._guard("DELETE", path)
        if user is False:
            return

        if path.startswith("/api/patients/"):
            try:
                pid = int(path.split("/")[3])
                conn = get_db()
                conn.execute("DELETE FROM patients WHERE id = ?", (pid,))
                conn.commit()
                conn.close()
                self.send_response(204)
                self._send_cors()
                self.end_headers()
                return
            except Exception as e:
                return self._send_json({"detail": str(e)}, status=400)

        self._send_json({"detail": "Not found"}, status=404)

def run():
    from http.server import ThreadingHTTPServer
    port = int(os.environ.get("PORT", 8000))
    changed = migrate_db(DB_PATH)
    if changed:
        print(f"[Security] Re-encrypted {changed} legacy patient record(s) with Fernet.")
    get_nn_service()  # load the D1 disease model before accepting requests
    server = ThreadingHTTPServer(("0.0.0.0", port), MediXAIHandler)
    print(f"[MediXAI Server] Listening on http://0.0.0.0:{port}...")
    server.serve_forever()

if __name__ == "__main__":
    run()
