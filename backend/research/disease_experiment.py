"""
Disease prediction experiment (report Sections 3.6 and 4.x).

Protocol
  * Data: cleaned D1 (131 binary symptom features, unique patterns, 41 diseases)
  * Split: stratified 80:20 train/test (random_state=42), done AFTER de-duplication
  * Models: Decision Tree, Logistic Regression, Random Forest, SVM, XGBoost, MLP
           (+ Bernoulli Naive Bayes as an extra baseline)
  * Tuning: grid search with 4-fold stratified CV, primary metric macro-F1;
           cross-validated log-loss is recorded for every candidate
  * Selection: best CV macro-F1; candidates within 0.01 of the best are tied and
           the tie is broken by the lowest CV log-loss (probability quality),
           never by the test set
  * Test metrics: accuracy, macro-F1, log-loss, top-3 accuracy, ECE
  * Variability: 30 repeated stratified 80:20 splits with the tuned parameters
  * Robustness: randomly discard 25% and 50% of positive symptoms in the test set
  * Explainability: Kernel SHAP (15 background samples) local + global, for the MLP
"""
from __future__ import annotations

import time
import warnings

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.model_selection import GridSearchCV, StratifiedKFold, StratifiedShuffleSplit, train_test_split
from sklearn.naive_bayes import BernoulliNB
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from research.common import (MODELS_DIR, SEED, expected_calibration_error, reliability_bins,
                             save_json, top_k_accuracy)
from research.d1_data import clean_d1, d2_consistency, matrices

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def candidates(n_classes: int):
    return {
        "Decision Tree": (DecisionTreeClassifier(random_state=SEED),
                          {"criterion": ["gini", "entropy"], "max_depth": [None, 10, 20], "min_samples_leaf": [1, 2, 4]}),
        "Logistic Regression": (LogisticRegression(max_iter=3000),
                                {"C": [0.1, 1.0, 10.0]}),
        "Random Forest": (RandomForestClassifier(random_state=SEED, n_jobs=1),
                          {"n_estimators": [200, 400], "max_depth": [None, 20], "min_samples_leaf": [1, 2]}),
        "SVM": (SVC(probability=True, random_state=SEED),
                {"C": [0.1, 1.0, 10.0], "kernel": ["linear", "rbf"]}),
        "XGBoost": (XGBClassifier(objective="multi:softprob", num_class=n_classes, eval_metric="mlogloss",
                                  random_state=SEED, n_jobs=1, tree_method="hist"),
                    {"n_estimators": [200], "max_depth": [3, 6], "learning_rate": [0.1, 0.3]}),
        "MLP": (MLPClassifier(max_iter=2000, random_state=SEED),
                {"hidden_layer_sizes": [(64,), (128,), (128, 64)], "alpha": [1e-4, 1e-3, 1e-2]}),
        "Naive Bayes (baseline)": (BernoulliNB(), {"alpha": [0.1, 0.5, 1.0]}),
    }


def evaluate(model, X, y, n_classes):
    p = model.predict_proba(X)
    pred = p.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", labels=np.arange(n_classes), zero_division=0)),
        "log_loss": float(log_loss(y, p, labels=np.arange(n_classes))),
        "top3_accuracy": top_k_accuracy(p, y, 3),
        "ece": expected_calibration_error(p, y),
    }


def drop_symptoms(X, frac, rng):
    Xd = X.copy()
    for i in range(len(Xd)):
        pos = np.where(Xd[i] > 0)[0]
        k = int(round(frac * len(pos)))
        k = min(k, len(pos) - 1)  # keep at least one symptom
        if k > 0:
            Xd[i, rng.choice(pos, k, replace=False)] = 0
    return Xd


def run(n_repeats: int = 30, robustness_repeats: int = 20, shap_nsamples: int = 500, verbose: bool = True):
    t0 = time.time()
    df, data_stats = clean_d1()
    data_stats["d2"] = d2_consistency(df)
    X, y, feats, classes = matrices(df)
    K = len(classes)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    split = {"train": int(len(ytr)), "test": int(len(yte))}
    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=SEED)

    results, fitted = {}, {}
    for name, (est, grid) in candidates(K).items():
        if verbose:
            print(f"[disease] grid search {name} ...", flush=True)
        gs = GridSearchCV(est, grid, cv=cv, scoring={"f1": "f1_macro", "nll": "neg_log_loss"},
                          refit="f1", n_jobs=-1, error_score="raise")
        gs.fit(Xtr, ytr)
        bi = gs.best_index_
        results[name] = {
            "best_params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in gs.best_params_.items()},
            "cv_macro_f1": float(gs.cv_results_["mean_test_f1"][bi]),
            "cv_macro_f1_std": float(gs.cv_results_["std_test_f1"][bi]),
            "cv_log_loss": float(-gs.cv_results_["mean_test_nll"][bi]),
            "test": evaluate(gs.best_estimator_, Xte, yte, K),
        }
        fitted[name] = gs.best_estimator_

    # ---- selection on cross-validation only
    main = [n for n in results if "baseline" not in n]
    best_f1 = max(results[n]["cv_macro_f1"] for n in main)
    tied = [n for n in main if results[n]["cv_macro_f1"] >= best_f1 - 0.01]
    selected = min(tied, key=lambda n: results[n]["cv_log_loss"])
    selection = {"rule": "best CV macro-F1; ties (within 0.01) broken by lowest CV log-loss",
                 "tied_candidates": tied, "selected": selected}

    # ---- 30 repeated stratified splits
    rep = {n: {"accuracy": [], "macro_f1": [], "log_loss": [], "top3_accuracy": []} for n in results}
    sss = StratifiedShuffleSplit(n_splits=n_repeats, test_size=0.2, random_state=SEED + 1)
    for i, (a, b) in enumerate(sss.split(X, y)):
        for n, m in fitted.items():
            mm = clone(m).fit(X[a], y[a])
            ev = evaluate(mm, X[b], y[b], K)
            for k in rep[n]:
                rep[n][k].append(ev[k])
        if verbose and (i + 1) % 10 == 0:
            print(f"[disease] repeated splits {i + 1}/{n_repeats}", flush=True)
    for n in results:
        results[n]["repeated_splits"] = {k: {"mean": float(np.mean(v)), "std": float(np.std(v)),
                                             "min": float(np.min(v)), "max": float(np.max(v))}
                                         for k, v in rep[n].items()}
        results[n]["repeated_splits_raw_accuracy"] = rep[n]["accuracy"]

    # ---- robustness: discard positive symptoms
    rng = np.random.default_rng(SEED)
    rob = {n: {} for n in results}
    for frac in (0.25, 0.5):
        accs = {n: [] for n in results}
        top3 = {n: [] for n in results}
        for _ in range(robustness_repeats):
            Xd = drop_symptoms(Xte, frac, rng)
            for n, m in fitted.items():
                p = m.predict_proba(Xd)
                accs[n].append(float((p.argmax(1) == yte).mean()))
                top3[n].append(top_k_accuracy(p, yte, 3))
        for n in results:
            rob[n][f"drop_{int(frac*100)}pct"] = {"accuracy": float(np.mean(accs[n])), "top3_accuracy": float(np.mean(top3[n]))}
    for n in results:
        results[n]["robustness"] = rob[n]

    # ---- deployed model: the MLP (report's deployed model); selection result reported honestly
    deployed_name = "MLP"
    deployed = fitted[deployed_name]
    p_te = deployed.predict_proba(Xte)
    calib = reliability_bins(p_te, yte)

    # Kernel SHAP, background = 15 representative training observations (one per k-means cluster)
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=15, n_init=10, random_state=SEED).fit(Xtr)
    bg_idx = [int(np.argmin(((Xtr - c) ** 2).sum(1))) for c in km.cluster_centers_]
    background = Xtr[sorted(set(bg_idx))]
    shap_info = kernel_shap_global(deployed, background, Xte, feats, classes, shap_nsamples, verbose)

    joblib.dump({"model": deployed, "features": feats, "classes": classes, "background": background,
                 "name": deployed_name, "params": results[deployed_name]["best_params"],
                 "train_X": Xtr, "train_y": ytr, "test_X": Xte, "test_y": yte},
                os.path.join(MODELS_DIR, "disease_model.joblib"))

    out = {
        "data": data_stats, "split": split, "models": results, "selection": selection,
        "deployed_model": deployed_name, "deployed_calibration": calib, "shap": shap_info,
        "runtime_seconds": round(time.time() - t0, 1),
        "caveat": ("D1 has only ~300 unique symptom patterns (4,616 duplicates). Perfect held-out "
                   "scores reflect a small, highly separable dataset, not real-world diagnostic accuracy."),
    }
    save_json("disease_results.json", out)
    if verbose:
        print(f"[disease] done in {out['runtime_seconds']} s; selected={selected}", flush=True)
    return out


def kernel_shap_global(model, background, Xte, feats, classes, nsamples, verbose):
    import shap
    t = time.time()
    explainer = shap.KernelExplainer(model.predict_proba, background, link="identity")
    pred = model.predict(Xte)
    vals = explainer.shap_values(Xte, nsamples=nsamples, silent=True)
    vals = np.asarray(vals)
    if vals.ndim == 3 and vals.shape[0] == len(classes) and vals.shape[1] == len(Xte):
        vals = np.transpose(vals, (1, 2, 0))  # -> (n, features, classes)
    per_sample = np.array([vals[i, :, pred[i]] for i in range(len(Xte))])  # predicted-class SHAP
    mean_abs = np.abs(per_sample).mean(axis=0)
    order = np.argsort(-mean_abs)
    glob = [{"feature": feats[j], "mean_abs_shap": float(mean_abs[j])} for j in order[:20]]
    example = 0
    loc = sorted(({"feature": feats[j], "shap": float(per_sample[example, j]), "present": bool(Xte[example, j])}
                  for j in range(len(feats))), key=lambda d: -abs(d["shap"]))[:10]
    if verbose:
        print(f"[disease] Kernel SHAP on {len(Xte)} test samples in {time.time()-t:.1f}s", flush=True)
    return {"method": "Kernel SHAP", "background_size": int(len(background)), "nsamples": nsamples,
            "explained_output": "probability of the predicted class", "global_top20": glob,
            "local_example": {"predicted": classes[pred[example]], "top10": loc},
            "matrix_for_plot": per_sample[:, order[:15]].tolist(), "matrix_features": [feats[j] for j in order[:15]],
            "matrix_values_X": Xte[:, order[:15]].tolist()}


import os  # noqa: E402  (used above in joblib path)

if __name__ == "__main__":
    run()
