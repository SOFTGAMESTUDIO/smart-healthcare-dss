"""Shared paths, metrics and helpers for the research pipeline."""
from __future__ import annotations

import json
import os
from datetime import datetime

import numpy as np

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
RESULTS_DIR = os.path.join(BACKEND_DIR, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")
MODELS_DIR = os.path.join(BACKEND_DIR, "artifacts", "research")
for d in (RESULTS_DIR, FIG_DIR, MODELS_DIR):
    os.makedirs(d, exist_ok=True)

SEED = 42


def expected_calibration_error(proba: np.ndarray, y_true: np.ndarray, n_bins: int = 15) -> float:
    """ECE = sum_m |B_m|/N * |acc(B_m) - conf(B_m)| using top-1 confidence."""
    conf = proba.max(axis=1)
    pred = proba.argmax(axis=1)
    correct = (pred == y_true).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def reliability_bins(proba: np.ndarray, y_true: np.ndarray, n_bins: int = 10):
    conf = proba.max(axis=1)
    correct = (proba.argmax(axis=1) == y_true).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "confidence": float(conf[m].mean()),
                        "accuracy": float(correct[m].mean()), "count": int(m.sum())})
    return out


def top_k_accuracy(proba: np.ndarray, y_true: np.ndarray, k: int = 3) -> float:
    topk = np.argsort(-proba, axis=1)[:, :k]
    return float(np.mean([y_true[i] in topk[i] for i in range(len(y_true))]))


def save_json(name: str, obj) -> str:
    path = os.path.join(RESULTS_DIR, name)
    obj = dict(obj)
    obj.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=_np_default)
    return path


def load_json(name: str):
    path = os.path.join(RESULTS_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _np_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))
