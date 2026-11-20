"""
Leakage-aware preparation of the symptom datasets (D1, D2).

Steps (report Section 3.6, "Dataset Acquisition and Preprocessing"):
  1. Load D1 Training.csv (4,920 rows, 132 symptom columns + prognosis).
  2. Remove erroneous columns. D1 contains two copies of `fluid_overload`:
       - `fluid_overload`   : ALL ZEROS (erroneous, carries no information)
       - `fluid_overload.1` : the real data (positive for Alcoholic hepatitis)
     We drop the all-zero copy and keep the informative one -> 131 features.
     (Dropping the informative copy instead, as the original report did,
      also gives 131 features but merges two patterns -> 303 instead of 304.)
  3. Remove duplicate rows BEFORE splitting -> unique symptom patterns.
     Removing duplicates after the split would let identical patterns appear
     in both train and test (leakage).
  4. D1 Testing.csv is NOT used for evaluation: all its rows already appear in
     Training.csv.
  5. D2 is used only for a consistency check (its patterns overlap D1) and as
     a source of symptom severity weights, descriptions and precautions.
"""
from __future__ import annotations

import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from research.common import DATA_DIR

D1_DIR = os.path.join(DATA_DIR, "d1")
D2_DIR = os.path.join(DATA_DIR, "d2")


def _norm(s: str) -> str:
    return str(s).strip().replace(" ", "_").replace("__", "_").lower()


def load_d1_raw() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(D1_DIR, "Training.csv"))
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df["prognosis"] = df["prognosis"].str.strip()
    return df


def clean_d1() -> Tuple[pd.DataFrame, Dict]:
    raw = load_d1_raw()
    stats = {"raw_rows": int(len(raw)), "raw_symptom_columns": int(raw.shape[1] - 1),
             "diseases": int(raw["prognosis"].nunique())}
    sym_cols = [c for c in raw.columns if c != "prognosis"]
    all_zero = [c for c in sym_cols if raw[c].sum() == 0]
    df = raw.drop(columns=all_zero)
    df = df.rename(columns={c: c[:-2] for c in df.columns if c.endswith(".1")})
    df.columns = [c if c == "prognosis" else _norm(c) for c in df.columns]
    stats["removed_columns"] = all_zero
    stats["removed_columns_reason"] = "all-zero duplicate of an informative column"
    stats["missing_values"] = int(df.isna().sum().sum())
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    stats["duplicate_rows_removed"] = int(before - len(df))
    stats["unique_patterns"] = int(len(df))
    stats["symptom_features"] = int(df.shape[1] - 1)
    feats = [c for c in df.columns if c != "prognosis"]
    X = df[feats]
    groups = {}
    for c in feats:
        groups.setdefault(tuple(X[c].values), []).append(c)
    stats["identical_feature_groups"] = [g for g in groups.values() if len(g) > 1]
    stats["patterns_per_disease"] = df["prognosis"].value_counts().describe()[["min", "mean", "max"]].round(2).to_dict()

    # Testing.csv overlap
    te = pd.read_csv(os.path.join(D1_DIR, "Testing.csv"))
    te = te.loc[:, ~te.columns.str.startswith("Unnamed")]
    te["prognosis"] = te["prognosis"].str.strip()
    te = te.drop(columns=[c for c in all_zero if c in te.columns])
    te = te.rename(columns={c: c[:-2] for c in te.columns if c.endswith(".1")})
    te.columns = [c if c == "prognosis" else _norm(c) for c in te.columns]
    key_tr = set(map(tuple, df[feats + ["prognosis"]].astype(str).values))
    in_train = sum(tuple(r) in key_tr for r in te[feats + ["prognosis"]].astype(str).values)
    stats["testing_csv_rows"] = int(len(te))
    stats["testing_csv_rows_in_training"] = int(in_train)
    return df, stats


def d2_consistency(d1: pd.DataFrame) -> Dict:
    raw = pd.read_csv(os.path.join(D2_DIR, "dataset.csv"), header=None).dropna(how="all")
    feats = [c for c in d1.columns if c != "prognosis"]
    fset = set(feats)
    rows, unknown = [], set()
    for _, r in raw.iterrows():
        disease = str(r.iloc[0]).strip()
        syms = {_norm(s) for s in r.iloc[1:].dropna()}
        unknown |= {s for s in syms if s not in fset}
        rows.append((disease, frozenset(s for s in syms if s in fset)))
    uniq = set(rows)
    d1_patterns = {(r["prognosis"], frozenset(c for c in feats if r[c] == 1)) for _, r in d1.iterrows()}
    matched = len(uniq & d1_patterns)
    return {"d2_rows": int(len(rows)), "d2_unique_patterns": int(len(uniq)),
            "d2_patterns_matching_d1": int(matched),
            "d2_unknown_symptom_names": sorted(unknown)[:10],
            "use": "consistency check only (not independent validation)"}


def load_severity() -> Dict[str, int]:
    df = pd.read_csv(os.path.join(D2_DIR, "Symptom_severity.csv"))
    return {_norm(a): int(b) for a, b in df.values}


def load_descriptions() -> Dict[str, Dict]:
    desc = pd.read_csv(os.path.join(D2_DIR, "symptom_Description.csv"), header=None)
    prec = pd.read_csv(os.path.join(D2_DIR, "symptom_precaution.csv"), header=None)
    out = {}
    for d, t in desc.values:
        out.setdefault(str(d).strip(), {})["description"] = str(t).strip()
    for r in prec.values:
        out.setdefault(str(r[0]).strip(), {})["precautions"] = [str(x).strip() for x in r[1:] if isinstance(x, str)]
    return out


def matrices(df: pd.DataFrame):
    feats = [c for c in df.columns if c != "prognosis"]
    classes = sorted(df["prognosis"].unique())
    cidx = {c: i for i, c in enumerate(classes)}
    X = df[feats].values.astype(np.float64)
    y = df["prognosis"].map(cidx).values
    return X, y, feats, classes


if __name__ == "__main__":
    import json
    d, s = clean_d1()
    s["d2"] = d2_consistency(d)
    print(json.dumps(s, indent=1, default=str)[:3000])
