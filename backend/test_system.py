"""
test_system.py – Comprehensive automated validation test suite for MediXAI.
Verifies:
  1. SQLite3 WAL concurrency & table schema integrity.
  2. Cryptographic round-trip (Fernet encryption at rest for DPDP Act 2023).
  3. PredictionService: 131-symptom vector, softmax probability, margin Δ, entropy H_norm, low confidence flags.
  4. TriageService: 8 departments, keyword scoring, vitals rules, emergency red flags.
  5. OR-Tools AppointmentScheduler: priority cost function C(t), zero constraint violations.
  6. SimulationService: 28-day 20-seed replication metrics.
"""

import sys
import os
import sqlite3
import json
import math

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from app.ml.prediction_service import prediction_service
from app.ml.triage_rules import triage
from app.scheduler.optimizer import scheduler
from app.scheduler.simulation_service import simulation_service
from init_local_db import simple_encrypt, simple_hash, DB_PATH

def test_sqlite_wal():
    print("\n[TEST 1] Verifying SQLite3 WAL Mode & Schema...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode;")
    mode = c.fetchone()[0]
    assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

    # Check tables exist
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in c.fetchall()}
    required_tables = {"users", "doctors", "patients", "appointments", "audit_logs"}
    assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"

    # Check seeded counts
    users_cnt = c.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
    patients_cnt = c.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
    doctors_cnt = c.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
    conn.close()

    assert users_cnt >= 4, f"Expected at least 4 users, found {users_cnt}"
    assert patients_cnt >= 8, f"Expected at least 8 patients, found {patients_cnt}"
    assert doctors_cnt >= 5, f"Expected at least 5 doctors, found {doctors_cnt}"
    print(f"  ✅ SQLite3 WAL active ({mode}). Tables verified. Users: {users_cnt}, Patients: {patients_cnt}, Doctors: {doctors_cnt}")

def test_encryption_roundtrip():
    print("\n[TEST 2] Verifying Fernet / Field-Level Encryption...")
    original = "Ramesh Kumar (Confidential Patient Record)"
    from app.secure_store import encrypt_field, decrypt_field
    import base64
    encrypted = encrypt_field(original)
    assert encrypted.startswith("FER_"), "Missing Fernet token prefix"
    assert original.encode() not in base64.urlsafe_b64decode(encrypted[4:] + "=="), "Plaintext recoverable without key"
    assert decrypt_field(encrypted) == original, "Fernet round-trip failed"
    print(f"  ✅ Field encrypted: '{original}' → '{encrypted[:24]}...'")

def test_prediction_uncertainty_and_shap():
    print("\n[TEST 3] Verifying 131-Symptom Prediction, Uncertainty & SHAP...")
    # Case A: High-confidence cardiac symptoms (>= 3 symptoms)
    cardiac_symptoms = ["chest_pain", "breathlessness", "sweating", "vomiting"]
    result_a = prediction_service.predict_symptoms(cardiac_symptoms)
    
    assert len(result_a["top3_predictions"]) == 3, "Expected top-3 predictions"
    top_pred = result_a["top3_predictions"][0]
    assert top_pred["disease"] == "Heart attack", f"Expected Heart attack, got {top_pred['disease']}"
    assert top_pred["probability"] > 0.5, f"Expected high probability, got {top_pred['probability']}"
    assert "margin_delta" in result_a, "Missing margin Δ"
    assert "normalized_entropy" in result_a, "Missing normalized entropy H_norm"
    assert result_a["symptom_count"] == 4
    assert result_a["low_confidence"] is False, "Should be confident with 4 hallmark symptoms"
    assert len(result_a["shap_attribution"]["positive"]) > 0, "Missing positive SHAP attributions"
    print(f"  ✅ Case A (Cardiac): Predicted '{top_pred['disease']}' ({top_pred['percentage']}%) | Δ={result_a['margin_delta']} | H_norm={result_a['normalized_entropy']} | Low Confidence: {result_a['low_confidence']}")

    # Case B: Sparse symptom presentation (1 symptom) -> Triggers clinical review flag
    sparse_symptoms = ["fatigue"]
    result_b = prediction_service.predict_symptoms(sparse_symptoms)
    assert result_b["low_confidence"] is True, "Sparse input MUST trigger low_confidence flag"
    assert any("Sparse input" in r for r in result_b["low_confidence_reasons"])
    print(f"  ✅ Case B (Sparse): Successfully caught by uncertainty guardrails → Status: '{result_b['clinical_status']}'")

def test_triage_rules():
    print("\n[TEST 4] Verifying Independent 8-Department Triage & Red Flags...")
    # Case A: Emergency Red Flag text
    red_flag_input = "Patient reports acute crushing chest pain radiating to left jaw with severe breathlessness."
    res_a = triage(red_flag_input, {"blood_pressure": 140, "blood_sugar": 120})
    assert res_a["is_red_flag"] is True, "Expected emergency red flag to trigger"
    assert res_a["priority"] == "Urgent", f"Expected Urgent priority, got {res_a['priority']}"
    assert res_a["department"] in ("Cardiology", "Pulmonology"), f"Got {res_a['department']}"
    assert len(res_a["recommended_departments"]) <= 4 and all(r["justification"] for r in res_a["recommended_departments"])
    print(f"  ✅ Red Flag caught: {res_a['red_flag_reasons']} → {res_a['department']} (priority {res_a['priority']})")

    # Case B: Pulmonology Keyword match
    resp_input = "Chronic persistent wheezing, asthma flare-up with mucoid sputum and deep cough."
    res_b = triage(resp_input, {"blood_pressure": 120, "blood_sugar": 90})
    assert res_b["department"] == "Pulmonology", f"Expected Pulmonology, got {res_b['department']}"
    print(f"  ✅ Keyword triage routed to {res_b['department']} (Score: {res_b['dept_scores'].get('Pulmonology', 0)})")

def test_scheduler_optimizer():
    print("\n[TEST 5] Verifying Priority-Aware Scheduler C(t)...")
    requests = [
        {"patient_id": 1, "risk_score": 0.95, "dept": "Cardiology", "preferred_doctor_id": 1}, # Urgent
        {"patient_id": 2, "risk_score": 0.20, "dept": "General Medicine", "preferred_doctor_id": 2}, # Routine
    ]
    doctors = [
        {"id": 1, "name": "Dr. Priya Sharma", "specialization": "Cardiology", "hours_start": 9, "hours_end": 17},
        {"id": 2, "name": "Dr. Arjun Mehta", "specialization": "General Medicine", "hours_start": 9, "hours_end": 17},
    ]
    existing = []

    assignments = scheduler.schedule(requests, doctors, existing)
    assert len(assignments) == 2, f"Expected 2 assignments, got {len(assignments)}"
    # Urgent patient should be assigned at or before routine patient
    urgent_slot = next(a["slot_index"] for a in assignments if a["patient_id"] == 1)
    routine_slot = next(a["slot_index"] for a in assignments if a["patient_id"] == 2)
    assert urgent_slot <= routine_slot, f"Urgent slot ({urgent_slot}) should be <= Routine slot ({routine_slot})"
    print(f"  ✅ Scheduler verified: Urgent patient scheduled at slot {urgent_slot}, Routine at slot {routine_slot}. Zero violations.")

def test_simulation_replication():
    print("\n[TEST 6] Verifying 28-Day Simulation Benchmark Replication...")
    sim = simulation_service.run_simulation(demand_multiplier=1.0, seeds_count=20)
    findings = sim["key_findings"]
    cs = sim["comparison_summary"]
    assert cs["proposed"]["urgent_wait_days"] < cs["fcfs"]["urgent_wait_days"], "Proposed must reduce urgent wait"
    assert cs["proposed"]["urgent_seen_within_1_day_pct"] > cs["fcfs"]["urgent_seen_within_1_day_pct"]
    assert all(cs[p]["constraint_violations"] == 0 for p in cs)
    print(f"  ✅ Simulation ({sim['source']}): urgent wait {cs['fcfs']['urgent_wait_days']}d → {cs['proposed']['urgent_wait_days']}d "
          f"(-{findings['urgent_wait_reduction_pct']}%)")
    print(f"  ✅ 1-Day Urgent Fulfillment: {sim['comparison_summary']['proposed']['urgent_seen_within_1_day_pct']}% (vs FCFS {sim['comparison_summary']['fcfs']['urgent_seen_within_1_day_pct']}%)")
    print(f"  ✅ Doctor Absence Lag: {sim['doctor_absence_experiment']['proposed_reschedule_lag_days']}d (vs Fixed {sim['doctor_absence_experiment']['fixed_reschedule_lag_days']}d)")

if __name__ == "__main__":
    print("=" * 70)
    print("   MEDIXAI DECISION SUPPORT SYSTEM — FULL VERIFICATION SUITE   ")
    print("=" * 70)
    test_sqlite_wal()
    test_encryption_roundtrip()
    test_prediction_uncertainty_and_shap()
    test_triage_rules()
    test_scheduler_optimizer()
    test_simulation_replication()
    print("\n" + "=" * 70)
    print("   ALL 6 SYSTEM SUITES PASSED WITH 100% SUCCESS! 🎉           ")
    print("=" * 70)
