# Report & paper corrections (code vs. report)

The project now computes every result itself (`python -m research.run_all`). This page lists, section by section,
what the report/paper says, what the code now produces, and what to change. Numbers come from
`backend/results/RESULTS.md` (fixed seeds, so they reproduce exactly).

**Status legend:** ✅ matches · ✏️ update the number/text · ⚠️ internal inconsistency in the report/paper · 🆕 not yet run (needs D3)

---

## 1. What was wrong in the original code (important for your viva)

| Report claim | What the original code actually did | Now |
|---|---|---|
| MLP trained on D1, compared with 5 other classifiers | D1 was not in the project; the "131-symptom MLP" was a hand-written score table (only 10 of 41 diseases had profiles) | Real pipeline on D1 with 6 classifiers + CV |
| Kernel SHAP explanations | Dashboard SHAP / feature-importance values were fixed numbers in `server.py` | Real Kernel SHAP (verified additive in `test_research.py`) |
| XGBoost no-show on Kaggle D3 | Trained on 800 rows of random synthetic data | Real D3 pipeline (needs the CSV) |
| 28-day, 20-seed simulation | `simulation_service.py` returned the paper's numbers from formulas (e.g. `1.65 * scale`, "4 violations" for fixed slots) | Real discrete simulation with constraint checks |
| Fernet encryption, RBAC | Names/phones were only Base64-encoded; hard-coded backdoor passwords; unsigned tokens; no endpoint checked access | Fernet at rest, PBKDF2 passwords, HMAC-signed expiring tokens, role policy on every API route |

---

## 2. Data preparation (Section 3.6 / Table 4.1)

| Item | Report | Computed | Action |
|---|---|---|---|
| Raw D1 | 4,920 rows, 132 columns, 41 diseases | same | ✅ |
| Erroneous column | "removed duplicate column" → 131 features | D1 has `fluid_overload` (**all zeros**) and `fluid_overload.1` (real data). Report's 303 patterns result from deleting the *informative* copy. Code drops the all-zero copy → 131 features | ✏️ say which column was removed and why |
| Unique patterns | 303 | **304** | ✏️ 303 → 304 |
| Duplicates removed | 4,617 | **4,616** | ✏️ |
| Train / test | 242 / 61 | **243 / 61** | ✏️ |
| Testing.csv | 42 rows, 41 in training | this copy has 41 rows, all 41 in training | ✏️ minor |
| D2 consistency | 297 of 304 patterns match D1 | **304 of 304** after fixing 3 misspelt D1 column names (`dischromic _patches`, `foul_smell_of urine`, `spotting_ urination`) | ✏️ explain the name normalisation |

## 3. Disease prediction (Table 4.2 / paper Table I)

| Model | Report accuracy | Computed accuracy | Computed macro-F1 | CV macro-F1 | CV log-loss | ECE |
|---|---|---|---|---|---|---|
| Decision Tree | 68.85% | **67.21%** | 57.48% | 0.668 | 9.937 | 0.219 |
| Logistic Regression | 100% | 100% ✅ | 100% | 1.000 | 0.414 | 0.229 |
| Random Forest | 100% | 100% ✅ | 100% | 1.000 | 0.304 | 0.207 |
| SVM | 100% | 100% ✅ | 100% | 1.000 | 2.053 | 0.832 |
| XGBoost | 88.52% | 88.52% ✅ | 85.37% | 0.817 | 0.733 | 0.192 |
| **MLP (selected)** | 100%, ECE 0.0216, log-loss 0.0232 | 100%, **ECE 0.0216, log-loss 0.0234** ✅ | 100% | 1.000 | **0.038** | 0.022 |

- ✅ Selection: LR, RF, SVM and MLP tie on CV macro-F1; MLP has the lowest CV log-loss → selected (as the report says).
- ✏️ Robustness (20 repeats): MLP **98.2%** at 25% symptoms removed (report 96.9%), **88.1%** at 50% (report 82.8%).
- ✏️ 30 repeated splits: MLP 100.00 ± 0.00%, RF 99.95 ± 0.29%, XGBoost 87.10 ± 3.24%, DT 62.68 ± 3.66% — add as mean ± sd.
- ✏️ Global SHAP top symptoms: itching, loss of appetite, dark urine, joint pain, yellowing of eyes, muscle pain, abdominal pain, mild fever. The paper's list contains "low temperature", which is not a D1 feature.
- ⚠️ Paper §V-A: "highest accuracy … MLP 84.02% vs RF 76.05% and SVM 59.92%" contradicts the 100% in Table I. These look like **robustness** numbers (computed at 50% removal: MLP 88.1%, RF 86.3%, SVM 60.7%). Relabel the sentence as robustness or remove it.
- ⚠️ Paper: ECE "SVM (83.28%), Random Forest (20.40%)" — ECE is a fraction, write 0.833 / 0.207 (computed), not percent.
- ⚠️ Paper mentions Naive Bayes 68.9%, which is not one of the six models. Bernoulli NB (correct for binary symptoms) scores 100%; 68.9% was probably Gaussian NB. Either drop it or state the variant.
- ⚠️ Paper §III-C says "six algorithms" but lists five (Logistic Regression missing).
- ⚠️ Paper abstract: "the proposed MLP classifier has an ROC-AUC of 73.27%" — that number belongs to the no-show model.

## 4. No-show prediction (Table 4.3) 🆕

Not yet run here: place `KaggleV2-May-2016.csv` in `backend/data/d3/` and run `python -m research.run_all`, then copy the
table from `results/RESULTS.md`. Fix these inconsistencies at the same time:

- ⚠️ Paper Table I no-show rows: the "Accuracy/ROC-AUC" column shows 29.51 / 35.14 / 35.62 — these are PR-AUC values; the columns appear swapped.
- ⚠️ Text says "XGBoost had an accuracy of 0.733" (should be ROC-AUC) and "RF test ROC-AUC 0.729" while Table I shows 73.27 for RF.
- ⚠️ Text says XGBoost was selected on PR-AUC, but reports RF PR-AUC 0.356 > XGBoost 0.295. The pipeline now selects by CV PR-AUC and reports whichever wins.

## 5. Scheduling (Table 4.4) — replace with simulated values

Setting (add to Section 4.x): 8 departments, 16 doctors, 360-min clinic day, 14 patients/doctor/day, Sunday closed,
15/30/45-min visits, priority mix 15/25/60% (urgent/high/routine), same-day booking allowed, normal demand = nominal
capacity, 7-day warm-up + 28 measured days, 20 seeds with common random numbers, weights w = (1.0, 1.5, 0.3, 0.4),
priority weights urgent 10 / high 2 / routine 0.3.

| Metric (normal demand, mean ± sd) | Report FCFS → Proposed | FCFS | Fixed 30-min | Proposed |
|---|---|---|---|---|
| Mean wait from request (days) | 1.66 → 1.65 | 1.00 ± 0.24 | 6.34 ± 0.45 | 2.71 ± 0.18 |
| Wait beyond preferred date (days) | — | 0.40 ± 0.13 | 4.62 ± 0.43 | 0.87 ± 0.18 |
| Urgent wait (days) | 1.65 → 0.62 | **1.02 ± 0.25** | 6.34 ± 0.47 | **0.09 ± 0.04** |
| High-priority wait (days) | 2.78 → 2.34 | 1.00 ± 0.24 | 6.33 ± 0.46 | 1.66 ± 0.28 |
| Urgent seen within 1 day | 50.36% → 85.92% | **73.8%** | 2.7% | **97.5%** |
| Preference satisfaction | 51.02% → 70.66% | **30.4%** | 14.2% | **68.8%** |
| Schedule completion | 100% → 100% | 100% | 100% | 100% |
| Doctor utilisation | — | 95.9% | 100% | 96.3% |
| Constraint violations | 0 → 0 | 0 | 0 | 0 |

- ✏️ Urgent wait reduction: 62.7% → **91.5%**.
- ✏️ Physician absence (7 days, ~28.6 affected bookings): fixed **6.30 days** vs proposed **0.09 days** (report 6.99 vs 1.28).
- ✏️ Demand sensitivity (urgent wait, days) — FCFS / fixed / proposed: 0.6× 0.00/0.04/0.00 · 0.85× 0.08/2.43/0.00 · 1.0× 1.02/6.34/0.09 · 1.2× 4.82/11.71/0.41 · 1.5× 11.14/19.80/1.23.
- ⚠️ Change the claim "average waiting time unchanged". The simulation shows a **trade-off**: the proposed policy books routine (and some high-priority) patients on their preferred later dates and gives same-day capacity to urgent patients, so mean wait from request rises (1.00 → 2.71 days) and high-priority wait rises (1.00 → 1.66 days), while urgent wait falls by 91.5% and preference satisfaction more than doubles. Present this honestly; examiners will appreciate it.

## 6. Security (Section 3.6 "Data Security")

- ✏️ Describe what is implemented: Fernet (AES-128-CBC + HMAC-SHA256) for patient fields at rest; PBKDF2-HMAC-SHA256 (200,000 iterations, per-user salt) for passwords; HMAC-SHA256-signed tokens with 8-hour expiry; role policy (patient: diagnosis only; physician: records, feedback, retraining; admin: deletion, model rollback).
- ⚠️ Remove "bcrypt" from the architecture table unless you switch to it.
- Do not publish `backend/fernet_key.bin` or `backend/.env` in a public repository.

## 7. New features you can add to the report

- **Clinical reasoning report** (Section 3.6 addition): for every prediction the system weighs evidence for/against each differential using data-driven typical symptoms from D1, flags when the model's top choice explains few findings, and recommends investigations, management approach, referral and safety-net advice. Example worth citing: for fever 39.4 °C + headache + joint pain + rash + vomiting the D1 MLP ranks brain haemorrhage first (26%), but the reasoning layer identifies Dengue as the best evidence fit (explains 100% of findings) — a concrete illustration of the generalisation limits discussed in Chapter 5.
- **Clinician feedback loop** (Future Scope → implemented): confirmed diagnoses retrain the MLP; a new version is kept only if D1 test accuracy and held-out confirmed-case accuracy do not drop; versions can be rolled back.
