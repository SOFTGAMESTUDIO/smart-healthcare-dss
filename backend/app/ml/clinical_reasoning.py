"""
clinical_reasoning.py - Turns neural-network output into a clinician-style assessment.

Pipeline (mirrors how a doctor reasons):
  1. Summarise the presentation (key symptoms, abnormal vitals, duration).
  2. Consider ALL 41 diseases using the network's probabilities.
  3. For every serious candidate, weigh the evidence:
       - supporting findings (present typical / hallmark symptoms)
       - missing hallmark findings (expected but not reported)
       - findings the disease does NOT explain
       - consistency of vitals, age and duration with the disease profile
  4. Keep "can't-miss" urgent diseases in the differential even at low probability.
  5. Reach a conclusion whose strength matches the evidence
     (probable / likely-but-not-excluded / undifferentiated).
  6. Recommend an approach: immediate actions, investigations that confirm or
     rule out each candidate (ranked by how much they help), management
     approach, referral, safety-net advice and follow-up.

The management text is general guidance on approach, not prescriptions.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Set

from app.ml.disease_kb import DISEASES_41
from app.ml.symptom_dataset import DISEASE_PROFILES, CLINICAL_DEFAULTS

# ---------------------------------------------------------------- knowledge
# disease: (investigations, management approach, follow-up / return advice)
CLINICAL_PLANS: Dict[str, tuple] = {
    "Fungal infection": (["KOH mount / skin scraping microscopy", "Fungal culture if extensive or recurrent", "Blood sugar (recurrent infections)"],
                         ["Topical antifungal for 2-4 weeks, continue 1-2 weeks after clearing", "Oral antifungal only for extensive/nail/scalp disease (doctor decision)", "Keep skin dry; treat household contacts"],
                         "Review if not improving in 2-4 weeks or spreading."),
    "Allergy": (["Clinical diagnosis; absolute eosinophil count", "Allergy skin-prick or specific IgE testing if recurrent"],
                ["Trigger avoidance", "Non-sedating antihistamine; nasal steroid for persistent rhinitis", "Emergency plan if any history of anaphylaxis"],
                "Return immediately if lip/tongue swelling, wheeze or breathing difficulty."),
    "GERD": (["Clinical diagnosis; trial of acid suppression", "ECG if chest pain (rule out cardiac cause)", "Upper GI endoscopy if alarm features (weight loss, dysphagia, bleeding, age > 55)"],
             ["Lifestyle: smaller meals, no meals 3 h before bed, raise bed head, weight loss", "Proton-pump inhibitor course as prescribed", "Avoid trigger foods, alcohol and smoking"],
             "Review in 4-8 weeks; urgent if vomiting blood, black stools or trouble swallowing."),
    "Chronic cholestasis": (["Liver function tests (ALP, GGT, bilirubin)", "Abdominal ultrasound", "AMA antibody, MRCP if ducts dilated"],
                            ["Treat the underlying cause (specialist)", "Symptom relief for itching", "Fat-soluble vitamin assessment"],
                            "Hepatology follow-up; urgent if fever with jaundice (cholangitis)."),
    "Drug Reaction": (["Detailed medication history (last 8 weeks)", "CBC with eosinophils, LFT, kidney function", "Urgent review if mucosal involvement (SJS/TEN)"],
                      ["Stop the suspected drug under medical guidance", "Antihistamines / topical steroids for mild rash", "Record as drug allergy"],
                      "Emergency if blistering, mouth/eye sores, fever or facial swelling."),
    "Peptic ulcer diseae": (["H. pylori test (urea breath / stool antigen)", "CBC for anaemia", "Upper GI endoscopy if age > 55 or alarm features"],
                            ["Stop NSAIDs, alcohol and smoking", "Acid suppression therapy", "H. pylori eradication if positive"],
                            "Emergency if black stools, vomiting blood or sudden severe pain."),
    "AIDS": (["HIV-1/2 antibody/antigen test with counselling and consent", "CD4 count and viral load", "Screen for TB, hepatitis B/C, opportunistic infections"],
             ["Antiretroviral therapy via ART centre / specialist", "Prophylaxis against opportunistic infections as indicated", "Partner notification and safe-sex counselling"],
             "Regular ART-centre follow-up; urgent for new fever, cough or neurological symptoms."),
    "Diabetes": (["Fasting plasma glucose and HbA1c", "Urine ketones if unwell", "Kidney function, lipid profile, eye and foot exam"],
                 ["Diet, exercise and weight management", "Glucose-lowering therapy per guidelines", "Education on hypoglycaemia and sick-day rules"],
                 "Review in 2-4 weeks with results; urgent if vomiting, drowsiness or very high sugars."),
    "Gastroenteritis": (["Usually clinical; assess dehydration", "Stool test if bloody diarrhoea or > 7 days", "Electrolytes and kidney function if severe dehydration"],
                        ["Oral rehydration solution (ORS) after each loose stool", "Zinc for children", "Antibiotics only for specific indications (doctor decision)"],
                        "Return if unable to keep fluids down, blood in stool, no urine for 8 h, or drowsy."),
    "Bronchial Asthma": (["Peak expiratory flow / spirometry with reversibility", "SpO2 monitoring", "Chest X-ray if fever or first severe episode"],
                         ["Reliever inhaler for symptoms; controller (inhaled steroid) if persistent", "Check inhaler technique", "Trigger avoidance and written asthma action plan"],
                         "Emergency if unable to speak in sentences, SpO2 < 92% or reliever not helping."),
    "Hypertension": (["Repeat BP on 2-3 occasions or ambulatory monitoring", "ECG, kidney function, urine protein, lipids, glucose", "Fundoscopy if BP very high"],
                     ["Lifestyle: salt < 5 g/day, exercise, weight loss, limit alcohol", "Antihypertensive therapy per guidelines", "Treat cardiovascular risk factors"],
                     "Emergency if BP >= 180/120 with chest pain, breathlessness, confusion or weakness."),
    "Migraine": (["Clinical diagnosis", "Neuro-imaging only if red flags (sudden worst headache, neuro deficit, age > 50 new headache)"],
                 ["Rest in dark quiet room; simple analgesia early", "Triptan for moderate-severe attacks if no contraindication", "Headache diary; preventive therapy if frequent"],
                 "Emergency for thunderclap headache, fever with stiff neck, weakness or confusion."),
    "Cervical spondylosis": (["Clinical exam incl. neurological examination", "Cervical spine X-ray", "MRI if limb weakness/numbness"],
                             ["Physiotherapy, posture correction, neck exercises", "Analgesics for flares", "Surgical opinion only if progressive neurological deficit"],
                             "Urgent if new weakness, numbness, gait or bladder problems."),
    "Paralysis (brain hemorrhage)": (["EMERGENCY non-contrast CT brain", "Blood glucose, coagulation profile, CBC", "BP monitoring"],
                                     ["Call emergency services - time critical", "Stroke/neurosurgical centre management", "Nothing by mouth until swallow assessed"],
                                     "Emergency now."),
    "Jaundice": (["Liver function tests (bilirubin fractions, enzymes)", "Hepatitis A/B/C/E serology", "Abdominal ultrasound, CBC (haemolysis)"],
                 ["Treat the cause once identified", "Hydration and rest; avoid alcohol and unnecessary medicines", "Monitor for liver failure signs"],
                 "Urgent if confusion, bleeding, persistent vomiting or worsening jaundice."),
    "Malaria": (["Peripheral blood smear (thick and thin) or malaria rapid antigen test - same day", "CBC, platelet count", "Kidney function, glucose and bilirubin if severe"],
                ["Antimalarial treatment per national guidelines once confirmed", "Antipyretic (paracetamol) and fluids", "Severe malaria needs hospital admission"],
                "Emergency if confusion, seizures, jaundice, dark urine, breathlessness or bleeding."),
    "Chicken pox": (["Clinical diagnosis", "PCR of vesicle fluid only if atypical or immunocompromised"],
                    ["Isolate until all lesions crust; calamine and antihistamine for itch", "Paracetamol for fever (avoid aspirin in children)", "Antiviral considered for adults, pregnant or immunocompromised (doctor decision)"],
                    "Return if breathing difficulty, confusion, or infected/very painful spots."),
    "Dengue": (["NS1 antigen (days 1-5) or dengue IgM (after day 5)", "CBC with platelet count and haematocrit - repeat daily", "LFT if unwell"],
               ["Paracetamol only - AVOID ibuprofen/aspirin/NSAIDs", "Oral fluids; monitor urine output", "Watch closely on days 3-7 (critical phase)"],
               "Emergency if abdominal pain, persistent vomiting, bleeding, drowsiness or cold hands (warning signs)."),
    "Typhoid": (["Blood culture (best in first week)", "CBC; Typhidot/Widal has limited accuracy", "LFT"],
                ["Antibiotic course per local sensitivity guidelines", "Fluids, soft diet, antipyretic", "Complete the full course"],
                "Urgent if severe abdominal pain, bleeding or confusion (complications)."),
    "hepatitis A": (["IgM anti-HAV", "Liver function tests, INR"],
                    ["Supportive: rest, hydration, nutrition", "Avoid alcohol and hepatotoxic drugs", "Hand hygiene; vaccinate contacts"],
                    "Urgent if confusion, bleeding, or vomiting preventing fluids."),
    "Hepatitis B": (["HBsAg, anti-HBc IgM, HBeAg, HBV DNA", "Liver function tests, INR", "Ultrasound liver"],
                    ["Specialist assessment for antiviral therapy", "Avoid alcohol", "Vaccinate household and sexual contacts"],
                    "Regular hepatology follow-up; urgent if confusion or bleeding."),
    "Hepatitis C": (["Anti-HCV antibody, then HCV RNA", "Liver function tests, fibrosis assessment"],
                    ["Direct-acting antiviral therapy (curative) via specialist", "Avoid alcohol", "No sharing of needles/razors"],
                    "Hepatology follow-up."),
    "Hepatitis D": (["Anti-HDV with HBsAg", "Liver function tests, INR"],
                    ["Specialist hepatology management", "Avoid alcohol", "Hepatitis B vaccination prevents HDV in contacts"],
                    "Urgent if confusion or bleeding."),
    "Hepatitis E": (["IgM anti-HEV", "LFT, INR, glucose", "Pregnancy test in women (high-risk group)"],
                    ["Supportive care; admit if INR raised or pregnant", "Safe drinking water", "Avoid hepatotoxic drugs"],
                    "Emergency if confusion, bleeding or drowsiness (liver failure)."),
    "Alcoholic hepatitis": (["LFT (AST:ALT > 2), bilirubin, INR, albumin", "CBC, kidney function", "Ultrasound abdomen; ascitic tap if fluid"],
                            ["Complete alcohol cessation with withdrawal management", "Nutritional support (high protein, thiamine)", "Hospital care if severe (specialist decides on steroids)"],
                            "Emergency if vomiting blood, confusion or fever."),
    "Tuberculosis": (["Sputum CBNAAT/GeneXpert and smear microscopy (2 samples)", "Chest X-ray", "HIV test, blood sugar"],
                     ["Standard anti-TB treatment under national programme (DOTS)", "Cough hygiene, ventilated room", "Nutritional support; screen household contacts"],
                     "Monthly review during treatment; urgent if coughing blood."),
    "Common Cold": (["None usually needed", "Test for flu/COVID if locally indicated"],
                    ["Rest, fluids, steam inhalation, saline nasal drops", "Paracetamol for fever/aches", "Antibiotics are NOT helpful"],
                    "Return if fever > 3 days, breathlessness, ear pain or worsening after initial improvement."),
    "Pneumonia": (["Chest X-ray", "SpO2, CBC, CRP; blood culture and sputum culture if admitted", "CURB-65 severity score"],
                  ["Antibiotics per guidelines (doctor decides oral vs IV)", "Oxygen if SpO2 < 94%", "Admit if CURB-65 >= 2, low SpO2 or unable to take orally"],
                  "Review in 48 h; emergency if breathing worsens, confusion or lips turn blue."),
    "Dimorphic hemmorhoids(piles)": (["Clinical / proctoscopic examination", "Colonoscopy if age > 45, anaemia or change in bowel habit"],
                                     ["High-fibre diet, fluids, stool softener", "Sitz baths, topical preparations", "Banding or surgery for persistent/large piles"],
                                     "Review if bleeding persists; urgent if heavy bleeding or dizziness."),
    "Heart attack": (["12-lead ECG within 10 minutes", "Troponin (repeat at 3-6 h)", "Continuous cardiac monitoring"],
                     ["Call emergency services; keep patient at rest", "Aspirin if not allergic and advised by emergency services", "Urgent cardiology: reperfusion (PCI/thrombolysis)"],
                     "Emergency now."),
    "Varicose veins": (["Venous Doppler ultrasound"],
                       ["Leg elevation, compression stockings, exercise", "Weight management", "Vascular surgery opinion for ulcers or severe symptoms"],
                       "Urgent if a vein bleeds, or calf becomes hot, red and swollen (clot)."),
    "Hypothyroidism": (["TSH and free T4", "Anti-TPO antibodies", "Lipids, CBC"],
                       ["Levothyroxine replacement, dose adjusted to TSH", "Take on empty stomach, separate from calcium/iron", "Recheck TSH 6-8 weeks after dose change"],
                       "Review with results; regular TSH monitoring."),
    "Hyperthyroidism": (["TSH, free T4, free T3", "TSH-receptor antibodies; thyroid scan if needed", "ECG if palpitations"],
                        ["Beta-blocker for symptoms if suitable", "Antithyroid medication via endocrinologist", "Definitive options: radioiodine or surgery"],
                        "Urgent if very fast heartbeat, fever with confusion (thyroid storm)."),
    "Hypoglycemia": (["Capillary blood glucose NOW", "Review diabetes medicines, alcohol, meals", "Further work-up if no diabetes"],
                     ["15-20 g fast-acting sugar, recheck in 15 min (rule of 15)", "Follow with a complex-carbohydrate snack", "Glucagon/IV glucose if unconscious (emergency)"],
                     "Emergency if unconscious or not improving after treatment."),
    "Osteoarthristis": (["Clinical diagnosis; weight-bearing X-ray of affected joint", "ESR/CRP if inflammation suspected"],
                        ["Exercise therapy and physiotherapy (first line)", "Weight loss; walking aids", "Analgesics/topical NSAIDs; joint replacement for end-stage"],
                        "Review if function declines; urgent if hot swollen joint with fever."),
    "Arthritis": (["ESR, CRP, rheumatoid factor, anti-CCP", "Uric acid; X-ray of affected joints", "CBC, kidney/liver function before treatment"],
                  ["Early rheumatology referral (disease-modifying therapy)", "Physiotherapy and joint protection", "Short-term anti-inflammatory relief"],
                  "Urgent if single hot swollen joint with fever (septic arthritis)."),
    "(vertigo) Paroymsal  Positional Vertigo": (["Dix-Hallpike test", "Neurological exam (HINTS) to exclude central cause"],
                                                ["Canalith repositioning (Epley manoeuvre)", "Brief anti-vertigo medicine only for severe nausea", "Fall precautions"],
                                                "Emergency if new weakness, double vision, slurred speech or severe headache."),
    "Acne": (["Clinical diagnosis", "Hormonal tests if signs of PCOS"],
             ["Topical retinoid / benzoyl peroxide", "Oral antibiotic or isotretinoin for moderate-severe (dermatologist)", "Gentle skin care; do not squeeze"],
             "Review in 8-12 weeks."),
    "Urinary tract infection": (["Urine dipstick and microscopy", "Urine culture (before antibiotics if possible)", "Pregnancy test in women of reproductive age"],
                                ["Antibiotic course per local guidelines", "Plenty of fluids", "Imaging if recurrent, male or not improving"],
                                "Urgent if fever, flank pain, vomiting (kidney infection) or pregnant."),
    "Psoriasis": (["Clinical diagnosis; skin biopsy if uncertain", "Screen joints (psoriatic arthritis), lipids, glucose"],
                  ["Emollients and topical steroids / vitamin D analogues", "Phototherapy or systemic therapy for extensive disease", "Stop smoking, limit alcohol"],
                  "Review in 4-8 weeks; urgent if widespread red skin with fever."),
    "Impetigo": (["Clinical diagnosis; swab culture if not responding"],
                 ["Clean crusts; topical antibiotic for localised disease", "Oral antibiotic if widespread", "Keep child off school until 48 h of treatment / crusted"],
                 "Review if spreading or fever."),
}

LEVELS = [(0.50, "Likely"), (0.15, "Possible"), (0.03, "Less likely"), (0.0, "Unlikely")]


def _level(p: float) -> str:
    for thr, name in LEVELS:
        if p >= thr:
            return name
    return "Unlikely"


def _z(value, mean_sd):
    m, sd = mean_sd
    return (value - m) / max(sd, 1e-6)


def _fmt(s: str) -> str:
    return s.replace("_", " ")


def assess(symptoms: List[str], clin: Dict[str, float], provided: Set[str],
           probs: Dict[str, float], metadata: Dict[str, dict], red_flags: List[str],
           typical: Optional[Dict[str, List[str]]] = None,
           hallmarks: Optional[Dict[str, List[str]]] = None) -> dict:
    """Build the full reasoning report. `probs` must contain all 41 diseases.

    typical / hallmarks: per-disease symptom lists derived from the training data
    (symptoms seen in the disease's D1 patterns / seen in >= 80% of them).
    Vitals, age and duration plausibility use the clinical-knowledge profiles.
    """
    sym = set(symptoms)
    ranked = sorted(probs.items(), key=lambda kv: -kv[1])
    p1_d, p1 = ranked[0]
    p2_d, p2 = ranked[1]

    # ---------------- 1. presentation summary
    abnormal = []
    if "temperature" in provided:
        t = clin["temperature"]
        if t >= 38.0: abnormal.append(f"fever {t:.1f} °C")
        elif t < 35.5: abnormal.append(f"low temperature {t:.1f} °C")
    if "heart_rate" in provided:
        if clin["heart_rate"] > 100: abnormal.append(f"tachycardia {clin['heart_rate']:.0f} bpm")
        elif clin["heart_rate"] < 55: abnormal.append(f"bradycardia {clin['heart_rate']:.0f} bpm")
    if "systolic_bp" in provided:
        if clin["systolic_bp"] >= 140: abnormal.append(f"raised BP {clin['systolic_bp']:.0f} mmHg")
        elif clin["systolic_bp"] < 90: abnormal.append(f"low BP {clin['systolic_bp']:.0f} mmHg")
    if "spo2" in provided and clin["spo2"] < 95:
        abnormal.append(f"low SpO2 {clin['spo2']:.0f}%")
    who = []
    if "age" in provided: who.append(f"{clin['age']:.0f}-year-old")
    if "gender_female" in provided or "gender" in provided:
        who.append("female" if clin["gender_female"] >= 0.75 else "male" if clin["gender_female"] <= 0.25 else "")
    who = " ".join(w for w in who if w) or "Patient"
    dur = ""
    if "duration_days" in provided:
        d = clin["duration_days"]
        dur = " for " + ("less than a day" if d < 1 else f"{d:.0f} day(s)" if d < 30 else f"about {d/30:.0f} month(s)")
    summary = (f"{who} presenting with {', '.join(_fmt(s) for s in symptoms)}{dur}"
               + (f"; examination: {', '.join(abnormal)}" if abnormal else "")
               + ("." if not provided - {"age", "gender_female", "gender"} else
                  "" if abnormal else "; recorded vitals within normal range."))
    if not summary.endswith("."):
        summary += "."

    # ---------------- 2/3. weigh evidence for serious candidates
    considered = [d for d, p in ranked if p >= 0.03][:6] or [ranked[0][0], ranked[1][0]]
    if len(considered) < 2:
        considered.append(ranked[1][0])
    extra = 0
    for d, p in ranked:  # can't-miss diagnoses stay on the list (max 3 extra)
        if extra < 3 and metadata[d]["urgency"] == "Urgent" and p >= 0.02 and d not in considered:
            considered.append(d)
            extra += 1
    differential = []
    for d in considered:
        prof = DISEASE_PROFILES[d]
        typ = typical[d] if typical else prof["symptoms"]
        hal = hallmarks[d] if hallmarks else prof["symptoms"][:4]
        supporting = [s for s in symptoms if s in typ]
        missing = [s for s in hal if s not in sym]
        unexplained = [s for s in symptoms if s not in typ]
        notes_for, notes_against = [], []
        for key, label, unit in (("temperature", "temperature", "°C"), ("heart_rate", "heart rate", "bpm"),
                                 ("systolic_bp", "systolic BP", "mmHg"), ("spo2", "SpO2", "%")):
            if key not in provided:
                continue
            z = _z(clin[key], prof[{"temperature": "temp", "heart_rate": "hr", "systolic_bp": "sbp", "spo2": "spo2"}[key]])
            if abs(z) <= 1.5:
                if abs(clin[key] - CLINICAL_DEFAULTS[key]) > {"temperature": 0.8, "heart_rate": 15, "systolic_bp": 20, "spo2": 3}[key]:
                    notes_for.append(f"{label} {clin[key]:g} {unit} fits")
            elif abs(z) >= 2.5:
                notes_against.append(f"{label} {clin[key]:g} {unit} is atypical")
        if "age" in provided:
            za = _z(clin["age"], prof["age"])
            if abs(za) >= 2.5:
                notes_against.append(f"unusual age ({clin['age']:.0f})")
        if "duration_days" in provided:
            lo, hi = prof["days"]
            dd = clin["duration_days"]
            if dd < lo * 0.5 - 0.5 or dd > hi * 2 + 1:
                notes_against.append(f"duration {dd:.0f} d is atypical (usually {lo}-{hi} d)")
            elif lo <= dd <= hi:
                notes_for.append("duration fits")
        coverage = len(supporting) / max(1, len(symptoms))
        p = probs[d]
        level = _level(p)
        if (metadata[d]["urgency"] == "Urgent" and level in ("Less likely", "Unlikely")
                and len(supporting) >= 2):
            level = "Must rule out"
        differential.append({
            "disease": d, "probability": round(p, 4), "percentage": round(p * 100, 1), "assessment": level,
            "department": metadata[d]["department"], "urgency": metadata[d]["urgency"],
            "supporting_findings": [_fmt(s) for s in supporting] + notes_for,
            "against_or_missing": ([f"no {_fmt(s)}" for s in missing[:3]] + notes_against),
            "unexplained_findings": [_fmt(s) for s in unexplained],
            "explains_pct": round(coverage * 100),
            "confirm_with": CLINICAL_PLANS[d][0][:2],
        })

    top = differential[0]
    n_meaningful = sum(1 for _, p in ranked if p >= 0.03)

    # ---------------- 5. conclusion
    margin = p1 - p2
    if p1 >= 0.70 and margin >= 0.30:
        strength = "Probable"
        conclusion = (f"Working diagnosis: {p1_d} ({p1*100:.0f}%). The findings fit its typical pattern"
                      + (f" ({', '.join(top['supporting_findings'][:4])})" if top["supporting_findings"] else "")
                      + ". Confirm with " + " and ".join(CLINICAL_PLANS[p1_d][0][:1]) + ".")
    elif p1 >= 0.40:
        strength = "Likely, not yet excluded"
        conclusion = (f"Most likely {p1_d} ({p1*100:.0f}%), but {p2_d} ({p2*100:.0f}%) cannot be excluded on "
                      f"symptoms alone. Tests should be chosen to separate these two.")
    else:
        strength = "Undifferentiated"
        names = ", ".join(f"{d} ({p*100:.0f}%)" for d, p in ranked[:3])
        conclusion = (f"No single diagnosis is supported yet - the presentation is non-specific. "
                      f"Leading possibilities: {names}. The most useful next step is to ask the "
                      f"discriminating questions and order first-line tests below, then re-assess.")
    # Evidence check: does another candidate explain the findings much better than the model's top pick?
    better = [x for x in differential[1:] if x["probability"] >= 0.05 and x["explains_pct"] >= 80
              and x["explains_pct"] >= top["explains_pct"] + 30 and not any("atypical" in a for a in x["against_or_missing"])]
    if better and len(symptoms) >= 3:
        b = max(better, key=lambda x: (x["explains_pct"], x["probability"]))
        strength = "Evidence favours an alternative"
        conclusion = (f"The model ranks {p1_d} first ({p1*100:.0f}%), but it explains only {top['explains_pct']}% of the findings, "
                      f"whereas {b['disease']} ({b['percentage']}%) explains {b['explains_pct']}% "
                      f"({', '.join(b['supporting_findings'][:5])}). Clinically, {b['disease']} is the better-supported working "
                      f"hypothesis - confirm with {b['confirm_with'][0]}" + (f" while excluding {p1_d}" if metadata[p1_d]['urgency'] == 'Urgent' else "") + ".")
        b["assessment"] = "Best evidence fit"
    elif top["explains_pct"] < 60 and len(symptoms) >= 4:
        conclusion += (f" Note: {p1_d} explains only {top['explains_pct']}% of the reported findings "
                       f"({', '.join(top['unexplained_findings'][:4])} unexplained) - consider a second condition "
                       f"or re-check the history.")
    must_rule_out = [x["disease"] for x in differential if x["assessment"] == "Must rule out"]
    if must_rule_out:
        conclusion += " Serious conditions to actively rule out: " + ", ".join(must_rule_out) + "."

    # ---------------- 6. approach
    immediate = list(red_flags)
    if metadata[p1_d]["urgency"] == "Urgent" and p1 >= 0.3:
        immediate.append(f"{p1_d} is time-sensitive - arrange same-day assessment.")
    if not immediate:
        immediate.append("No emergency features identified from the information given.")

    tests: Dict[str, dict] = {}
    for x in differential:
        w = x["probability"] + (0.05 if x["assessment"] == "Must rule out" else 0)
        if x["assessment"] == "Best evidence fit":
            w = max(w, 0.6)
        for i, t in enumerate(CLINICAL_PLANS[x["disease"]][0]):
            e = tests.setdefault(t, {"test": t, "helps_with": [], "score": 0.0})
            e["helps_with"].append(x["disease"])
            e["score"] += w * (1.0 if i == 0 else 0.6 if i == 1 else 0.3)
    investigations = sorted(tests.values(), key=lambda e: -e["score"])[:7]
    for e in investigations:
        e["priority"] = "First-line" if e["score"] >= 0.25 else "If needed"
        if (not red_flags and e["test"].upper().startswith("EMERGENCY")
                and max(probs[h] for h in e["helps_with"]) < 0.5):
            e["priority"] = "Only if red flags develop"
        e["score"] = round(e["score"], 3)
    rank = {"First-line": 0, "If needed": 1, "Only if red flags develop": 2}
    investigations.sort(key=lambda e: (rank[e["priority"]], -e["score"]))

    if strength == "Probable":
        management = CLINICAL_PLANS[p1_d][1]
    else:
        management = ["Supportive care while awaiting results (fluids, rest, paracetamol for fever/pain)",
                      f"Start specific treatment only after confirmation - leading candidate: {p1_d}"]
        if any(x["disease"] == "Dengue" and x["probability"] >= 0.05 for x in differential):
            management.append("Dengue is in the differential: avoid ibuprofen/aspirin/NSAIDs until excluded")
    safety_net = []
    for x in differential[:3]:
        adv = CLINICAL_PLANS[x["disease"]][2]
        if adv not in safety_net:
            safety_net.append(adv)

    referral = top["department"]
    if must_rule_out:
        referral += " (urgent review for " + ", ".join(must_rule_out[:2]) + ")"

    steps = [
        f"Presentation: {summary}",
        f"All 41 diseases were scored by the neural network; {n_meaningful} have a probability of 3% or more.",
        f"Leading candidate {p1_d} ({p1*100:.0f}%): supported by "
        + (", ".join(top["supporting_findings"][:5]) or "the overall pattern")
        + (f"; against/missing: {', '.join(top['against_or_missing'][:3])}" if top["against_or_missing"] else "") + ".",
    ]
    if len(differential) > 1:
        sec = differential[1]
        steps.append(f"Main alternative {sec['disease']} ({sec['percentage']}%): supported by "
                     + (", ".join(sec["supporting_findings"][:4]) or "few specific findings")
                     + (f"; against/missing: {', '.join(sec['against_or_missing'][:3])}" if sec["against_or_missing"] else "") + ".")
    if red_flags:
        steps.append("Safety rules triggered: " + "; ".join(red_flags))
    steps.append(f"Conclusion strength: {strength}.")

    return {
        "engine": "offline-clinical-reasoning",
        "case_summary": summary,
        "reasoning_steps": steps,
        "differential": differential,
        "conclusion": conclusion,
        "conclusion_strength": strength,
        "recommended_approach": {
            "immediate": immediate,
            "investigations": investigations,
            "management": management,
            "referral": referral,
            "safety_net": safety_net,
        },
    }
