"""
init_local_db.py – 100% standard library (sqlite3 + hashlib + base64 + hmac) database initializer.
Creates healthcare_dss.db with WAL mode, creates all schemas, and seeds test data.
Zero external pip dependencies required.
"""
import sqlite3
import os
import json
import base64
import hashlib
from datetime import datetime, timedelta

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BACKEND_DIR, "healthcare_dss.db")
KEY_FILE = os.path.join(BACKEND_DIR, "fernet_key.bin")

# Generate standard 32-byte urlsafe key if not present
if not os.path.exists(KEY_FILE):
    raw_key = os.urandom(32)
    b64_key = base64.urlsafe_b64encode(raw_key)
    with open(KEY_FILE, "wb") as f:
        f.write(b64_key)
    print(f"[Key] Generated new Fernet key at {KEY_FILE}")

def simple_encrypt(text: str) -> str:
    """Fernet field encryption (kept under the old name for compatibility)."""
    from app.secure_store import encrypt_field
    return encrypt_field(text)

def simple_hash(password: str) -> str:
    """PBKDF2-HMAC-SHA256 password hash (kept under the old name for compatibility)."""
    from app.secure_store import hash_password
    return hash_password(password)

def init():
    print(f"[DB] Initializing SQLite database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Apply WAL Pragmas for race-condition-proof high concurrency
    cursor.execute("PRAGMA journal_mode = WAL;")
    wal_status = cursor.fetchone()
    print(f"[DB] PRAGMA journal_mode set to: {wal_status[0] if wal_status else 'WAL'}")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 2. Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        hashed_password VARCHAR(200) NOT NULL,
        role VARCHAR(20) DEFAULT 'patient',
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        specialization VARCHAR(100) NOT NULL,
        available_hours_start INTEGER DEFAULT 9,
        available_hours_end INTEGER DEFAULT 17
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        encrypted_name VARCHAR(500) NOT NULL,
        encrypted_phone VARCHAR(500),
        age INTEGER NOT NULL,
        gender VARCHAR(1) NOT NULL,
        blood_pressure REAL NOT NULL,
        cholesterol REAL NOT NULL,
        blood_sugar REAL NOT NULL,
        bmi REAL NOT NULL,
        smoking INTEGER DEFAULT 0,
        family_history INTEGER DEFAULT 0,
        chest_pain_type INTEGER DEFAULT 0,
        ecg_result INTEGER DEFAULT 0,
        symptoms_text TEXT,
        disease_predicted INTEGER,
        risk_score REAL,
        noshow_risk VARCHAR(10),
        triage_dept VARCHAR(50),
        shap_values_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id),
        doctor_id INTEGER NOT NULL REFERENCES doctors(id),
        slot_datetime TIMESTAMP NOT NULL,
        duration_minutes INTEGER DEFAULT 30,
        priority_score REAL DEFAULT 0.5,
        status VARCHAR(20) DEFAULT 'scheduled',
        department VARCHAR(50),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action VARCHAR(100) NOT NULL,
        resource VARCHAR(100),
        resource_id INTEGER,
        ip_address VARCHAR(50),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Seed Users
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        users = [
            ("admin", "admin@hospital.org", simple_hash("admin123"), "admin", 1),
            ("drpriya", "priya.sharma@hospital.org", simple_hash("doctor123"), "physician", 1),
            ("drarjun", "arjun.mehta@hospital.org", simple_hash("doctor123"), "physician", 1),
            ("nurse1", "nurse1@hospital.org", simple_hash("nurse123"), "patient", 1),
        ]
        cursor.executemany(
            "INSERT INTO users (username, email, hashed_password, role, is_active) VALUES (?, ?, ?, ?, ?)",
            users
        )
        print("[DB Seed] Created 4 users.")

    # 4. Seed Doctors
    cursor.execute("SELECT COUNT(*) FROM doctors;")
    if cursor.fetchone()[0] == 0:
        doctors = [
            ("Dr. Priya Sharma", "Cardiology", 9, 17),
            ("Dr. Arjun Mehta", "General Medicine", 9, 17),
            ("Dr. Kavya Reddy", "Pulmonology", 10, 18),
            ("Dr. Rahul Singh", "Endocrinology", 9, 15),
            ("Dr. Ananya Iyer", "Neurology", 11, 19),
        ]
        cursor.executemany(
            "INSERT INTO doctors (name, specialization, available_hours_start, available_hours_end) VALUES (?, ?, ?, ?)",
            doctors
        )
        print("[DB Seed] Created 5 doctors.")

    # 5. Seed Patients with clinical features and precomputed SHAP values
    cursor.execute("SELECT COUNT(*) FROM patients;")
    if cursor.fetchone()[0] == 0:
        sample_patients = [
            (
                simple_encrypt("Ramesh Kumar"), simple_encrypt("+91-9845012345"), 68, "M",
                175.0, 310.0, 240.0, 32.4, 1, 1, 3, 2,
                "Severe substernal chest pain radiating to left arm, shortness of breath, heavy sweating",
                1, 0.89, "Low", "Emergency",
                json.dumps({
                    "age": 0.18, "gender": 0.05, "blood_pressure": 0.22,
                    "cholesterol": 0.19, "blood_sugar": 0.14, "bmi": 0.11,
                    "smoking": 0.20, "family_history": 0.15, "chest_pain_type": 0.25,
                    "ecg_result": 0.18
                })
            ),
            (
                simple_encrypt("Sunita Rao"), simple_encrypt("+91-9876543210"), 59, "F",
                158.0, 275.0, 185.0, 29.1, 0, 1, 2, 1,
                "Occasional palpitations, fatigue on moderate exertion, mild dizziness",
                1, 0.74, "Medium", "Cardiology",
                json.dumps({
                    "age": 0.12, "gender": -0.04, "blood_pressure": 0.16,
                    "cholesterol": 0.14, "blood_sugar": 0.10, "bmi": 0.08,
                    "smoking": -0.05, "family_history": 0.12, "chest_pain_type": 0.14,
                    "ecg_result": 0.09
                })
            ),
            (
                simple_encrypt("Vijay Nair"), simple_encrypt("+91-9123456789"), 72, "M",
                185.0, 330.0, 290.0, 33.8, 1, 1, 3, 2,
                "Acute retrosternal crushing pain, diaphoresis, severe hypertension crisis",
                1, 0.94, "Low", "Emergency",
                json.dumps({
                    "age": 0.21, "gender": 0.06, "blood_pressure": 0.26,
                    "cholesterol": 0.22, "blood_sugar": 0.18, "bmi": 0.14,
                    "smoking": 0.22, "family_history": 0.17, "chest_pain_type": 0.28,
                    "ecg_result": 0.20
                })
            ),
            (
                simple_encrypt("Ananya Sen"), simple_encrypt("+91-9988776655"), 34, "F",
                115.0, 170.0, 88.0, 21.5, 0, 0, 0, 0,
                "Mild persistent dry cough, seasonal allergy symptoms, nasal congestion",
                0, 0.12, "Low", "Pulmonology",
                json.dumps({
                    "age": -0.15, "gender": -0.05, "blood_pressure": -0.12,
                    "cholesterol": -0.10, "blood_sugar": -0.08, "bmi": -0.09,
                    "smoking": -0.07, "family_history": -0.06, "chest_pain_type": -0.11,
                    "ecg_result": -0.08
                })
            ),
            (
                simple_encrypt("Deepa Menon"), simple_encrypt("+91-9445566778"), 45, "F",
                136.0, 218.0, 124.0, 26.2, 0, 1, 1, 0,
                "Mild breathlessness when climbing stairs, slight fatigue, occasional headache",
                0, 0.48, "Medium", "General Medicine",
                json.dumps({
                    "age": 0.02, "gender": -0.03, "blood_pressure": 0.07,
                    "cholesterol": 0.05, "blood_sugar": 0.04, "bmi": 0.03,
                    "smoking": -0.05, "family_history": 0.09, "chest_pain_type": 0.05,
                    "ecg_result": -0.02
                })
            ),
            (
                simple_encrypt("Suresh Babu"), simple_encrypt("+91-9334455667"), 52, "M",
                148.0, 242.0, 145.0, 28.3, 1, 0, 1, 1,
                "Chest tightness on brisk walking, tingling sensation in left fingertips",
                1, 0.62, "Low", "Cardiology",
                json.dumps({
                    "age": 0.08, "gender": 0.04, "blood_pressure": 0.11,
                    "cholesterol": 0.09, "blood_sugar": 0.07, "bmi": 0.06,
                    "smoking": 0.16, "family_history": -0.04, "chest_pain_type": 0.08,
                    "ecg_result": 0.06
                })
            ),
            (
                simple_encrypt("Preethi Seshadri"), simple_encrypt("+91-9112233445"), 28, "F",
                110.0, 165.0, 82.0, 20.8, 0, 0, 0, 0,
                "Routine corporate annual health checkup, no current complaints",
                0, 0.08, "Low", "General Medicine",
                json.dumps({
                    "age": -0.19, "gender": -0.06, "blood_pressure": -0.15,
                    "cholesterol": -0.13, "blood_sugar": -0.10, "bmi": -0.12,
                    "smoking": -0.08, "family_history": -0.07, "chest_pain_type": -0.14,
                    "ecg_result": -0.10
                })
            ),
            (
                simple_encrypt("Karan Malhotra"), simple_encrypt("+91-9223344556"), 41, "M",
                128.0, 205.0, 110.0, 25.1, 1, 0, 0, 0,
                "Acid reflux, epigastric discomfort after spicy meals, bloating",
                0, 0.32, "High", "Gastroenterology",
                json.dumps({
                    "age": -0.03, "gender": 0.03, "blood_pressure": 0.02,
                    "cholesterol": 0.02, "blood_sugar": 0.01, "bmi": 0.01,
                    "smoking": 0.12, "family_history": -0.05, "chest_pain_type": -0.08,
                    "ecg_result": -0.06
                })
            ),
        ]

        cursor.executemany("""
            INSERT INTO patients (
                encrypted_name, encrypted_phone, age, gender,
                blood_pressure, cholesterol, blood_sugar, bmi,
                smoking, family_history, chest_pain_type, ecg_result,
                symptoms_text, disease_predicted, risk_score, noshow_risk,
                triage_dept, shap_values_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_patients)
        print(f"[DB Seed] Created {len(sample_patients)} patients with DPDP encrypted identifiers & SHAP attributions.")

    # 6. Seed Appointments
    cursor.execute("SELECT COUNT(*) FROM appointments;")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        appts = [
            (1, 1, (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), 30, 0.89, "scheduled", "Cardiology", "Urgent priority case"),
            (2, 1, (now + timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S"), 30, 0.74, "scheduled", "Cardiology", "Evaluation of palpitations"),
            (5, 2, (now + timedelta(days=2, hours=1)).strftime("%Y-%m-%d %H:%M:%S"), 30, 0.48, "scheduled", "General Medicine", "Routine consultation"),
        ]
        cursor.executemany("""
            INSERT INTO appointments (
                patient_id, doctor_id, slot_datetime, duration_minutes,
                priority_score, status, department, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, appts)
        print(f"[DB Seed] Created {len(appts)} initial scheduled appointments.")

    conn.commit()
    conn.close()
    print("[DB Seed] Database initialization and WAL mode setup completed successfully! ✅")

if __name__ == "__main__":
    init()
