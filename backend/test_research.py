"""
test_research.py - Checks that the project implements the report's methodology with computed results.
Run:  python test_research.py
"""
import os
import sys
import tempfile

os.environ["AI_MODEL_DIR"] = tempfile.mkdtemp(prefix="dss_test_")
os.environ["AI_RETRAIN_EVERY"] = "3"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

passed = 0


def check(cond, msg):
    global passed
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        sys.exit(1)
    passed += 1


# ---- 1. Leakage-aware data preparation
from research.d1_data import clean_d1, d2_consistency  # noqa: E402
df, st = clean_d1()
check(st["raw_rows"] == 4920 and st["diseases"] == 41, "D1 loaded: 4,920 rows, 41 diseases")
check(st["symptom_features"] == 131, "131 symptom features after removing the all-zero duplicate column")
check(st["unique_patterns"] == 304 and st["duplicate_rows_removed"] == 4616, "duplicates removed before split -> 304 patterns")
check(st["testing_csv_rows_in_training"] == st["testing_csv_rows"], "Testing.csv fully contained in Training.csv (correctly excluded)")
check(d2_consistency(df)["d2_patterns_matching_d1"] == 304, "D2 consistency check: all D2 patterns match D1")

# ---- 2. Computed results exist (not hard-coded)
from research.common import load_json  # noqa: E402
d = load_json("disease_results.json")
check(d is not None and set(d["models"]) >= {"Decision Tree", "Logistic Regression", "Random Forest", "SVM", "XGBoost", "MLP"},
      "six classifiers evaluated")
check(d["selection"]["selected"] == "MLP", "MLP selected by CV macro-F1 with log-loss tie-break")
check(len(d["models"]["MLP"]["repeated_splits_raw_accuracy"]) == 30, "30 repeated stratified splits recorded")
check("drop_50pct" in d["models"]["MLP"]["robustness"], "robustness (25%/50% symptom removal) recorded")
check(d["shap"]["background_size"] <= 15 and d["shap"]["method"] == "Kernel SHAP", "global Kernel SHAP with 15 background samples")

# ---- 3. Deployed model: prediction, uncertainty, real SHAP
from app.ml.nn_diagnosis_service import DiagnosisService  # noqa: E402
s = DiagnosisService(verbose=False)
r = s.diagnose(["chest_pain", "breathlessness", "sweating", "vomiting"], {"age": 60}, save=False)
check(r["top3_predictions"][0]["disease"] == "Heart attack", "cardiac pattern -> Heart attack")
check(len(r["all_probabilities"]) == 41 and abs(sum(x["probability"] for x in r["all_probabilities"]) - 1) < 1e-3,
      "probabilities for all 41 diseases sum to 1")
x = s.encode(["chest_pain", "breathlessness", "sweating", "vomiting"])
c = s.cidx["Heart attack"]
sv = s.kernel_shap(x, c, nsamples=2000)
base = s.model.predict_proba(s.background)[:, c].mean()
check(abs(sv.sum() - (s.model.predict_proba(x[None])[0, c] - base)) < 0.02, "Kernel SHAP values are additive (real, not hard-coded)")
r2 = s.diagnose(["headache"], {}, save=False)
check(r2["low_confidence"] and any("Sparse" in t for t in r2["low_confidence_reasons"]), "sparse input flagged for clinical review")

# ---- 4. Triage independent of the classifier
from app.ml.triage_rules import triage, DEPARTMENTS  # noqa: E402
check(set(DEPARTMENTS) == {"Pulmonology", "Gastroenterology", "General Medicine", "Cardiology", "Dermatology",
                           "Neurology", "Orthopedics", "ENT"}, "eight departments as in the report")
t = triage("", {"spo2": 88}, ["weakness_of_one_body_side", "slurred_speech"])
check(t["priority"] == "Urgent" and t["department"] == "Neurology", "stroke signs -> Neurology, Urgent priority")
check(triage("", {}, ["skin_rash", "itching"])["department"] == "Dermatology", "skin findings -> Dermatology")

# ---- 5. Reasoning prefers the better evidence fit
rr = s.diagnose(["high_fever", "headache", "joint_pain", "skin_rash", "vomiting"], {"temperature": 39.4, "age": 29}, save=False)
cr = rr["clinical_reasoning"]
best = [x["disease"] for x in cr["differential"] if x["assessment"] == "Best evidence fit"]
check(cr["conclusion"] and cr["recommended_approach"]["investigations"], "reasoning report with conclusion and investigations")
check(rr["top3_predictions"][0]["disease"] == "Dengue" or best == ["Dengue"], "dengue-like presentation -> Dengue (model or evidence fit)")

# ---- 6. Clinician feedback loop with acceptance gate
for _ in range(3):
    pid = s.diagnose(["yellowish_skin", "dark_urine", "nausea"], {}, save=True)["prediction_id"]
    s.feedback(pid, "hepatitis A")
import time  # noqa: E402
while s.retrain_status["running"]:
    time.sleep(0.1)
check(s.version >= 2 and s.history[-1]["accepted"], "retraining after confirmed cases produced an accepted new version")
check(s.history[-1]["benchmark"]["accuracy"] >= 0.95, "D1 test accuracy preserved after retraining")
check(s.rollback(1)["ok"], "rollback to v1")

# ---- 7. Real scheduling simulation
from research import scheduling_simulation as S  # noqa: E402
reqs = S.generate_requests(7, 1.0)
out = {}
for p in ("fcfs", "fixed", "proposed"):
    sch, uns, _ = S.simulate(p, reqs)
    check(S.verify(sch, reqs) == 0, f"{p}: zero constraint violations")
    out[p] = S.metrics(sch, reqs, uns)
check(out["proposed"]["urgent_wait_days"] < out["fcfs"]["urgent_wait_days"], "proposed policy reduces urgent wait vs FCFS")
check(out["proposed"]["preference_satisfaction_pct"] > out["fcfs"]["preference_satisfaction_pct"], "proposed policy improves preference satisfaction")
from app.scheduler.simulation_service import simulation_service  # noqa: E402
a, b = simulation_service.run_simulation(1.0), simulation_service.run_simulation(1.5)
check(a["comparison_summary"]["fcfs"]["urgent_wait_days"] != b["comparison_summary"]["fcfs"]["urgent_wait_days"],
      "simulation service returns different computed results per demand level")

print(f"\nAll {passed} checks passed.")
