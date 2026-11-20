# XAI Healthcare Decision Support System

> **An Explainable-AI–powered clinical Decision Support System (DSS) built for Indian healthcare workflows, fully compliant with the Digital Personal Data Protection (DPDP) Act 2023.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│   React 18 + Vite  │  TailwindCSS  │  Recharts  │  Axios       │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST / JSON
┌───────────────────────────────▼─────────────────────────────────┐
│                       API Layer (FastAPI)                        │
│   JWT Auth  │  Role-Based Access Control  │  Pydantic v2        │
│   Fernet PII Encryption  │  Uvicorn ASGI server                 │
└──────┬────────────────┬───────────────┬────────────────┬────────┘
       │                │               │                │
┌──────▼──────┐  ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
│  SQLite 3   │  │ MLP (D1) +  │ │   Kernel   │ │  C(t) +     │
│  (WAL mode) │  │ XGBoost no- │ │    SHAP    │ │  OR-Tools   │
│  Fernet PII │  │ show (D3)   │ │ (15 bg)    │ │  Scheduler  │
└─────────────┘  └─────────────┘ └────────────┘ └─────────────┘
```

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18, Vite, TailwindCSS, Recharts | Interactive clinical dashboard |
| **API** | FastAPI, Uvicorn, Pydantic v2 | RESTful endpoints, auth, validation |
| **Database** | SQLite 3 (WAL) + SQLAlchemy ORM | Persistent storage with concurrent reads |
| **Disease model** | scikit-learn MLP selected from 6 classifiers on D1 (4-fold CV) | Symptom-based prediction of 41 diseases with uncertainty checks |
| **No-show model** | XGBoost / RF / LR on Kaggle D3 (GroupKFold, PR-AUC) | Attendance risk at booking |
| **XAI** | Kernel SHAP (15 background samples) | Local and global explanations |
| **Triage** | Rule-based, 8 departments, D2 severity weights | Department, priority, red flags (independent of the classifier) |
| **Scheduler** | Priority-aware C(t) cost + local rescheduling (OR-Tools for batch booking) | Slot allocation; evaluated by a 20-seed simulation |
| **Security** | Fernet encryption at rest, PBKDF2 passwords, HMAC-signed tokens, RBAC | DPDP Act 2023 PII protection |

---

---

## 🔬 Research pipeline (reproduces Chapters 3–4 of the report)

Every result shown in the app is **computed** by `backend/research/` — nothing is hard-coded.

```bash
cd backend
pip install -r requirements.txt        # scikit-learn, xgboost, shap, pandas, matplotlib, cryptography ...
python -m research.run_all             # ~2-3 min: all experiments -> results/*.json, results/figures/*.png, results/RESULTS.md
python test_research.py                # 28 checks: data prep, 6 models, real Kernel SHAP, triage, feedback loop, simulation
python test_system.py                  # integration checks (DB/WAL, Fernet, prediction, triage, scheduler, simulation)
python server.py                       # http://localhost:8000  (login: drpriya / doctor123)
```

| Module | File | What it does |
|---|---|---|
| Data prep (D1/D2) | `research/d1_data.py` | removes the all-zero duplicate `fluid_overload` column, de-duplicates **before** splitting (4,920 → 304 patterns, 131 features), excludes `Testing.csv` (all rows already in training), D2 consistency check |
| Disease models | `research/disease_experiment.py` | DT, LR, RF, SVM, XGBoost, MLP (+ Bernoulli NB baseline); grid search + 4-fold stratified CV (macro-F1, log-loss); test accuracy/macro-F1/log-loss/top-3/ECE; 30 repeated splits; 25 %/50 % symptom-removal robustness; Kernel SHAP (15 background) |
| No-show (D3) | `research/noshow_experiment.py` | booking-time features incl. leakage-free appointment history; patient-wise split; 3-fold GroupKFold on PR-AUC; ROC-AUC, PR-AUC, Brier, top-20 % lift; Low/Medium/High thresholds. **Needs `data/d3/KaggleV2-May-2016.csv`** |
| Scheduling | `research/scheduling_simulation.py` | real simulation: 8 departments / 16 doctors, 7-day warm-up + 28 days, 20 seeds with common random numbers, 5 demand levels; FCFS vs fixed 30-min vs proposed C(t) with local rescheduling; physician-absence experiment; constraint verification |
| Triage | `app/ml/triage_rules.py` | 8 departments, top-4 with justifications, red flags, priority from D2 severity weights — independent of the classifier |
| Diagnosis service | `app/ml/nn_diagnosis_service.py` | deployed D1 MLP, top-3 + all 41 probabilities, uncertainty checks (count < 3, margin < 0.20, entropy > 0.50), local Kernel SHAP, clinical reasoning report, clinician-feedback retraining with acceptance gate |
| Reasoning | `app/ml/clinical_reasoning.py` | evidence for/against each differential (data-driven typical/hallmark symptoms from D1), conclusion, tests, management approach, safety-net |
| Security | `app/secure_store.py` | Fernet encryption at rest, PBKDF2 password hashing, HMAC-signed expiring tokens, role-based access (patient / physician / admin) |

App pages: **AI Diagnosis** (form → diagnosis, SHAP, triage, reasoning, feedback), **Results** (all computed tables and figures),
**Simulation** (real simulation results by demand level).

See `docs/REPORT_CORRECTIONS.md` for the numbers that changed and inconsistencies to fix in the report/paper.

---

## Quick Start

### Prerequisites

| Tool | Minimum Version |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm / pnpm | 9+ |

---

### Backend

```bash
cd smart-healthcare-dss/backend

# 1. Create & activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Optional) add the no-show dataset: data/d3/KaggleV2-May-2016.csv
# 4. Run all experiments and train the models (D1 disease, D3 no-show, scheduling simulation)
python -m research.run_all

# 5. Seed the database with demo users, doctors and patients
python seed_db.py

# 6. Launch the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd smart-healthcare-dss/frontend

# 1. Install Node dependencies
npm install

# 2. Start the Vite dev server
npm run dev
```

---

### Access

| Resource | URL |
|---|---|
| **Frontend** | http://localhost:5173 |
| **API Interactive Docs** | http://localhost:8000/docs |
| **API Redoc** | http://localhost:8000/redoc |
| **API Health Check** | http://localhost:8000/api/health |

---

### Default Login Credentials

| Role | Username | Password | Access Level |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Full system access, user management |
| **Physician** | `drpriya` | `doctor123` | Patient records, predictions, appointments |
| **Nurse / Demo** | `nurse1` | `nurse123` | Read-only patient view |

> [!CAUTION]
> Change all default passwords before any production or staging deployment.

---

## Features

### 🏥 Clinical Dashboard
- Real-time patient risk overview with colour-coded risk badges (High / Medium / Low)
- Key clinical KPIs: total patients, high-risk count, today's appointments, average risk score
- Interactive Recharts visualisations: risk distribution pie chart, age-vs-risk scatter, feature correlation heatmap

### 🤖 AI Risk Prediction (XGBoost + SHAP)
- One-click heart-disease risk assessment from 10 clinical parameters
- Risk probability expressed as a percentage with confidence band
- **SHAP waterfall chart** – shows each feature's positive / negative contribution to the prediction
- Automated clinical recommendation text generated from risk tier

### 🔍 Explainable AI (XAI) Panel
- Global feature importance bar chart (across all training data)
- Per-patient local SHAP explanation with force plot
- Feature value comparison against population percentiles
- Plain-language explanation narrative for non-technical clinical staff

### 📅 Smart Appointment Scheduling (OR-Tools CP-SAT)
- Constraint-aware slot optimisation: doctor availability windows, existing bookings, specialisation matching
- Automatic conflict detection and best-slot suggestion
- Appointment status lifecycle: Scheduled → Confirmed → Completed / Cancelled
- Calendar view with day / week / month grid

### 👤 Patient Management
- Searchable, filterable patient list with pagination
- Encrypted PII storage (name, phone, email, address) – DPDP Act compliant
- Full clinical history timeline per patient
- Risk trend chart across multiple visits

### 🔐 Authentication & Access Control
- JWT Bearer token authentication (access + refresh tokens)
- Role-Based Access Control: `admin`, `physician`, `patient`
- Secure bcrypt password hashing
- Token expiry and automatic refresh

### 📊 Analytics & Reporting
- Population-level risk statistics by age group, gender, specialisation
- Doctor workload and appointment throughput charts
- Exportable CSV reports for administrative review

### 🛡️ DPDP Act 2023 Compliance
- Fernet-encrypted PII columns (see [DPDP Compliance](#dpdp-act-2023-compliance) below)
- Audit log for every data access event
- Data minimisation: only clinically necessary fields stored
- Consent tracking per patient record

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Obtain JWT access + refresh tokens |
| `POST` | `/api/auth/refresh` | Refresh an expired access token |
| `POST` | `/api/auth/logout` | Invalidate the current token |
| `GET` | `/api/auth/me` | Get the current authenticated user's profile |

### Patients

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/patients` | List all patients (paginated, filterable) |
| `POST` | `/api/patients` | Create a new patient record |
| `GET` | `/api/patients/{id}` | Retrieve a single patient |
| `PUT` | `/api/patients/{id}` | Update patient clinical data |
| `DELETE` | `/api/patients/{id}` | Soft-delete a patient record |
| `GET` | `/api/patients/{id}/history` | Fetch the patient's prediction history |

### Predictions (AI / XAI)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/predict` | Run heart-disease risk prediction + SHAP explanation |
| `GET` | `/api/predict/history` | Retrieve past predictions for the authenticated user |
| `GET` | `/api/predict/{pred_id}` | Get a single prediction with full SHAP values |
| `GET` | `/api/predict/global-importance` | Global feature importance from trained model |

### Doctors

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/doctors` | List all active doctors |
| `POST` | `/api/doctors` | Add a new doctor (admin only) |
| `GET` | `/api/doctors/{id}` | Retrieve doctor profile |
| `PUT` | `/api/doctors/{id}` | Update doctor availability / details |
| `GET` | `/api/doctors/{id}/schedule` | View a doctor's appointment calendar |

### Appointments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/appointments` | List appointments (filtered by role) |
| `POST` | `/api/appointments` | Book a new appointment (OR-Tools slot selection) |
| `GET` | `/api/appointments/{id}` | Retrieve appointment details |
| `PUT` | `/api/appointments/{id}` | Update status or reschedule |
| `DELETE` | `/api/appointments/{id}` | Cancel an appointment |
| `GET` | `/api/appointments/suggest` | Get OR-Tools–optimised slot suggestions |

### Analytics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/analytics/risk-distribution` | Risk level breakdown (counts + percentages) |
| `GET` | `/api/analytics/age-risk` | Age-band vs average risk score |
| `GET` | `/api/analytics/doctor-workload` | Appointment throughput per doctor |
| `GET` | `/api/analytics/feature-stats` | Population-level clinical feature statistics |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check – returns `{"status": "ok"}` |
| `GET` | `/api/version` | API version and model metadata |

---

## DPDP Act 2023 Compliance

The **Digital Personal Data Protection Act 2023 (India)** mandates that any "personal data" must be processed lawfully, stored securely, and protected against unauthorised access.

### What is Encrypted

The following fields are classified as **personally identifiable information (PII)** and are encrypted at rest using **Fernet symmetric encryption** (AES-128-CBC with HMAC-SHA256 authentication):

| Table | Column | Description |
|---|---|---|
| `patients` | `name` | Patient full name |
| `patients` | `phone` | Mobile / landline number |
| `patients` | `email` | Email address |
| `patients` | `address` | Residential address |

Non-PII clinical fields (age, BP, cholesterol, risk score, etc.) are stored in plain form to allow efficient querying, aggregation, and ML feature extraction.

### How Fernet Works in This System

```
Plain PII  ──► Fernet.encrypt()  ──►  Base-64 token (stored in DB)
                     ▲
              AES-128-CBC key
            (loaded from fernet.key)
```

1. **Key Management** – `seed_db.py` calls `get_fernet_key()` which loads `backend/fernet.key` if it exists, or generates a new 32-byte key and writes it on first run.
2. **Encryption** – Every PII value is encrypted to a URL-safe base-64 token before `INSERT`/`UPDATE`.
3. **Decryption** – The API layer decrypts values on authorised `GET` requests only; the raw token is never sent to the frontend.
4. **Key Rotation** – Replace `fernet.key` with a new key and run the provided `rotate_keys.py` utility to re-encrypt all stored tokens in a single transaction.

> [!IMPORTANT]
> `fernet.key` **must never be committed to version control**. It is listed in `.gitignore` by default. Back it up to a secrets manager (e.g., Google Secret Manager, AWS Secrets Manager, HashiCorp Vault) for production deployments.

> [!NOTE]
> Under DPDP §8(5), data fiduciaries must implement "reasonable security safeguards". Fernet encryption of PII, bcrypt-hashed passwords, JWT token expiry, role-based access, and an audit log together satisfy this requirement for a research/clinical-pilot deployment.

---

## Project Structure

```
smart-healthcare-dss/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry-point
│   │   ├── config.py            # Settings (Pydantic BaseSettings)
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request / response schemas
│   │   ├── database.py          # Engine, session factory
│   │   ├── auth.py              # JWT + bcrypt helpers
│   │   ├── ml/
│   │   │   ├── predict.py       # XGBoost inference + SHAP explanations
│   │   │   ├── train.py         # Model training pipeline
│   │   │   └── model.pkl        # Trained XGBoost model (generated)
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── patients.py
│   │   │   ├── doctors.py
│   │   │   ├── appointments.py
│   │   │   ├── predict.py
│   │   │   └── analytics.py
│   │   └── scheduler/
│   │       └── or_tools_scheduler.py   # CP-SAT appointment optimiser
│   ├── data/
│   │   └── heart_disease_synthetic.csv  # Generated by generate_dataset.py
│   ├── generate_dataset.py      # legacy synthetic heart-risk data (patient registration demo only)
│   ├── seed_db.py               # Database seeding script
│   ├── research/                # data prep, 6-model experiment, no-show, scheduling simulation, run_all.py
│   ├── results/                 # computed results JSON, figures, RESULTS.md
│   ├── requirements.txt
│   ├── fernet.key               # ⚠ SECRET – never commit
│   └── healthcare_dss.db        # SQLite database (generated)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── PatientList.jsx
│   │   │   ├── PatientDetail.jsx
│   │   │   ├── PredictionForm.jsx
│   │   │   ├── XAIPanel.jsx
│   │   │   ├── AppointmentCalendar.jsx
│   │   │   └── Analytics.jsx
│   │   ├── pages/
│   │   ├── api/              # Axios client + endpoint hooks
│   │   ├── context/          # Auth context (JWT)
│   │   └── App.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
└── README.md
```

---

## Development Notes

- **Hot reload** – Both Uvicorn (`--reload`) and Vite HMR are active in dev mode.
- **CORS** – FastAPI is configured to allow `http://localhost:5173` during development.
- **Model retraining** – Re-run `python -m research.run_all` to recompute every experiment, model and figure.
- **Database reset** – Delete `healthcare_dss.db` and re-run `seed_db.py` to start fresh.
- **OR-Tools scheduler** – The CP-SAT solver runs with a 5-second time limit per request; tune `MAX_SOLVE_SECONDS` in `or_tools_scheduler.py` for production.

---

## License

This project is developed for academic research purposes under the supervision of the Department of Computer Science. All synthetic patient data is artificially generated and contains no real personal information.
