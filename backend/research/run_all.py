"""
Run every experiment in the report and write results, figures and report-ready tables.

    cd backend
    python -m research.run_all            # all experiments (~2-4 minutes; + no-show if D3 present)
    python -m research.run_all --figures  # only regenerate figures/tables from saved results

Outputs
    results/disease_results.json, noshow_results.json, scheduling_results.json
    results/figures/*.png
    results/RESULTS.md   (tables you can paste into the report)
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("PYTHONWARNINGS", "ignore")
import warnings  # noqa: E402

warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from research.common import FIG_DIR, RESULTS_DIR, load_json  # noqa: E402

BLUE, GREY, ORANGE, GREEN = "#2563eb", "#94a3b8", "#f59e0b", "#10b981"


def _style(ax, title):
    ax.set_title(title, fontsize=11, loc="left", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def figures():
    d = load_json("disease_results.json")
    s = load_json("scheduling_results.json")
    n = load_json("noshow_results.json")
    made = []
    if d:
        names = list(d["models"])
        acc = [100 * d["models"][k]["test"]["accuracy"] for k in names]
        f1 = [100 * d["models"][k]["test"]["macro_f1"] for k in names]
        fig, ax = plt.subplots(figsize=(9, 4))
        x = np.arange(len(names))
        ax.bar(x - 0.2, acc, 0.4, label="Accuracy", color=BLUE)
        ax.bar(x + 0.2, f1, 0.4, label="Macro-F1", color=GREY)
        ax.set_xticks(x, [k.replace(" (baseline)", "\n(baseline)") for k in names], fontsize=8)
        ax.set_ylabel("%"); ax.set_ylim(0, 105); ax.legend(frameon=False)
        _style(ax, "Disease prediction models - held-out test set (D1)")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "disease_models.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)

        fig, ax = plt.subplots(figsize=(9, 4))
        data = [np.array(d["models"][k]["repeated_splits_raw_accuracy"]) * 100 for k in names]
        ax.boxplot(data, tick_labels=[k.split(" (")[0] for k in names])
        ax.set_ylabel("Accuracy (%)"); ax.tick_params(axis="x", labelsize=8)
        _style(ax, "Variability over 30 repeated stratified 80:20 splits")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "repeated_splits.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)

        fig, ax = plt.subplots(figsize=(7, 4))
        for k, c in zip(names, plt.cm.tab10.colors):
            r = d["models"][k]["robustness"]
            ax.plot([0, 25, 50], [100 * d["models"][k]["test"]["accuracy"], 100 * r["drop_25pct"]["accuracy"],
                                  100 * r["drop_50pct"]["accuracy"]], marker="o", label=k, color=c)
        ax.set_xlabel("% of positive symptoms removed"); ax.set_ylabel("Accuracy (%)"); ax.legend(fontsize=7, frameon=False)
        _style(ax, "Robustness to missing symptoms")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "robustness.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)

        g = d["shap"]["global_top20"][:15][::-1]
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.barh([x["feature"].replace("_", " ") for x in g], [x["mean_abs_shap"] for x in g], color=BLUE)
        ax.set_xlabel("mean |SHAP| (probability of predicted class)")
        _style(ax, f"Global Kernel SHAP importance - {d['deployed_model']}")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "shap_global.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)

        cb = d["deployed_calibration"]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([0, 1], [0, 1], "--", color=GREY)
        ax.plot([b["confidence"] for b in cb], [b["accuracy"] for b in cb], "o-", color=BLUE)
        ax.set_xlabel("Confidence"); ax.set_ylabel("Accuracy")
        _style(ax, f"Reliability diagram (ECE {d['models']['MLP']['test']['ece']:.3f})")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "calibration.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)
    if s:
        base = s["summary"]["1.0"]
        labels = {"fcfs": "FCFS", "fixed": "Fixed 30-min", "proposed": "Proposed"}
        metrics = [("urgent_wait_days", "Urgent wait (days)"), ("mean_wait_days", "Mean wait (days)"),
                   ("urgent_within_1_day_pct", "Urgent within 1 day (%)"), ("preference_satisfaction_pct", "Preference satisfied (%)")]
        fig, axes = plt.subplots(1, 4, figsize=(13, 3.5))
        for ax, (k, t) in zip(axes, metrics):
            vals = [base[p][k]["mean"] for p in labels]
            errs = [base[p][k]["std"] for p in labels]
            ax.bar(list(labels.values()), vals, yerr=errs, color=[GREY, ORANGE, BLUE], capsize=3)
            ax.tick_params(axis="x", labelsize=8); _style(ax, t)
        fig.suptitle("Scheduling policies at normal demand (20 seeds, mean ± sd)", fontsize=11)
        fig.tight_layout(); p = os.path.join(FIG_DIR, "scheduling_baseline.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)

        fig, ax = plt.subplots(figsize=(7, 4))
        lv = sorted(s["summary"], key=float)
        for pk, c in zip(labels, [GREY, ORANGE, BLUE]):
            ax.plot([float(v) for v in lv], [s["summary"][v][pk]["urgent_wait_days"]["mean"] for v in lv], "o-", color=c, label=labels[pk])
        ax.set_xlabel("Demand (x normal)"); ax.set_ylabel("Urgent wait (days)"); ax.legend(frameon=False)
        _style(ax, "Urgent-patient waiting time across demand levels")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "scheduling_demand.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)
    if n and n.get("status") == "ok":
        names = list(n["models"])
        fig, ax = plt.subplots(figsize=(7, 4))
        x = np.arange(len(names))
        ax.bar(x - 0.2, [100 * n["models"][k]["test"]["roc_auc"] for k in names], 0.4, label="ROC-AUC", color=BLUE)
        ax.bar(x + 0.2, [100 * n["models"][k]["test"]["pr_auc"] for k in names], 0.4, label="PR-AUC", color=GREY)
        ax.set_xticks(x, names); ax.set_ylabel("%"); ax.legend(frameon=False)
        _style(ax, "No-show prediction (D3, patient-wise test split)")
        fig.tight_layout(); p = os.path.join(FIG_DIR, "noshow_models.png"); fig.savefig(p, dpi=150); plt.close(fig); made.append(p)
    return made


def tables():
    d, s, n = load_json("disease_results.json"), load_json("scheduling_results.json"), load_json("noshow_results.json")
    L = ["# Results (generated by `python -m research.run_all`)", ""]
    if d:
        ds = d["data"]
        L += ["## Data preparation (D1/D2)", "",
              f"- D1 raw: {ds['raw_rows']} rows, {ds['raw_symptom_columns']} symptom columns, {ds['diseases']} diseases",
              f"- Removed column(s): {', '.join(ds['removed_columns'])} ({ds['removed_columns_reason']})",
              f"- Duplicate rows removed: {ds['duplicate_rows_removed']} -> **{ds['unique_patterns']} unique patterns, {ds['symptom_features']} features**",
              f"- Missing values: {ds['missing_values']}",
              f"- Testing.csv: {ds['testing_csv_rows_in_training']} of {ds['testing_csv_rows']} rows already in Training.csv -> not used",
              f"- D2: {ds['d2']['d2_unique_patterns']} unique patterns, {ds['d2']['d2_patterns_matching_d1']} match D1 -> consistency check only",
              f"- Split: {d['split']['train']} train / {d['split']['test']} test (stratified 80:20, after de-duplication)", "",
              "## Disease prediction (Table 4.2)", "",
              "| Model | CV macro-F1 | CV log-loss | Test accuracy | Test macro-F1 | Test log-loss | Top-3 | ECE | 30-split accuracy (mean ± sd) | 25% removed | 50% removed |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for k, m in d["models"].items():
            t, r, rb = m["test"], m["repeated_splits"]["accuracy"], m["robustness"]
            L.append(f"| {k} | {m['cv_macro_f1']:.3f} | {m['cv_log_loss']:.3f} | {100*t['accuracy']:.2f}% | {100*t['macro_f1']:.2f}% | "
                     f"{t['log_loss']:.4f} | {100*t['top3_accuracy']:.1f}% | {t['ece']:.4f} | {100*r['mean']:.2f} ± {100*r['std']:.2f}% | "
                     f"{100*rb['drop_25pct']['accuracy']:.1f}% | {100*rb['drop_50pct']['accuracy']:.1f}% |")
        L += ["", f"Selection: {d['selection']['rule']}. Tied: {', '.join(d['selection']['tied_candidates'])}. "
                  f"**Selected: {d['selection']['selected']}**. Deployed: {d['deployed_model']}.", "",
              f"Kernel SHAP (background {d['shap']['background_size']}): top symptoms by mean |SHAP| - "
              + ", ".join(f"{g['feature']} ({g['mean_abs_shap']:.4f})" for g in d["shap"]["global_top20"][:8]), "",
              f"> {d['caveat']}", ""]
    L += ["## No-show prediction (Table 4.3)", ""]
    if n and n.get("status") == "ok":
        dd = n["data"]
        L += [f"- {dd['valid_records']} valid records ({dd['invalid_removed']} invalid removed), no-show rate {100*dd['no_show_rate']:.1f}%, "
              f"{dd['train_records']} train / {dd['test_records']} test (patient-wise)", "",
              "| Model | CV PR-AUC | Test ROC-AUC | Test PR-AUC | Brier | Top-20% lift |", "|---|---|---|---|---|---|"]
        for k, m in n["models"].items():
            t = m["test"]
            L.append(f"| {k} | {m['cv_pr_auc']:.3f} | {100*t['roc_auc']:.2f}% | {100*t['pr_auc']:.2f}% | {t['brier']:.3f} | {t['lift_top20']:.2f}x |")
        L += ["", f"Selected: **{n['selected']}** ({n['selection_rule']}).", ""]
    else:
        L += ["Not run yet - place `KaggleV2-May-2016.csv` in `backend/data/d3/` and rerun.", ""]
    if s:
        b = s["summary"]["1.0"]
        lab = {"fcfs": "FCFS", "fixed": "Fixed 30-min", "proposed": "Proposed"}
        rows = [("Mean wait from request (days)", "mean_wait_days", 2), ("Wait beyond preferred date (days)", "mean_excess_wait_days", 2),
                ("Urgent wait (days)", "urgent_wait_days", 2), ("High-priority wait (days)", "high_wait_days", 2),
                ("Urgent seen within 1 day (%)", "urgent_within_1_day_pct", 1), ("Preference satisfaction (%)", "preference_satisfaction_pct", 1),
                ("Schedule completion (%)", "scheduled_pct", 1), ("Doctor utilisation (%)", "doctor_utilization_pct", 1)]
        L += ["## Appointment scheduling (Table 4.4) - normal demand, 20 seeds, mean ± sd", "",
              "| Metric | FCFS | Fixed 30-min | Proposed |", "|---|---|---|---|"]
        for t, k, dp in rows:
            L.append(f"| {t} | " + " | ".join(f"{b[p][k]['mean']:.{dp}f} ± {b[p][k]['std']:.{dp}f}" for p in lab) + " |")
        L.append("| Constraint violations (all runs) | " + " | ".join(str(s["constraint_violations"][p]) for p in lab) + " |")
        h, a = s["headline"], s["physician_absence"]
        L += ["", f"- Urgent waiting time reduced by **{h['urgent_wait_reduction_pct_vs_fcfs']:.1f}%** vs FCFS; urgent seen within 1 day "
                  f"{h['urgent_within_1_day_fcfs']:.1f}% -> {h['urgent_within_1_day_proposed']:.1f}%.",
              f"- Physician absence (7 days, {a['fixed']['affected_mean']:.1f} affected appointments on average): mean rescheduling delay "
              f"**{a['fixed']['mean_delay_days']:.2f} days (fixed)** vs **{a['proposed']['mean_delay_days']:.2f} days (proposed)**.", "",
              "### Urgent wait across demand levels (days)", "", "| Demand | FCFS | Fixed 30-min | Proposed |", "|---|---|---|---|"]
        for v in sorted(s["summary"], key=float):
            L.append(f"| {v}x | " + " | ".join(f"{s['summary'][v][p]['urgent_wait_days']['mean']:.2f}" for p in lab) + " |")
    path = os.path.join(RESULTS_DIR, "RESULTS.md")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return path


def main():
    if "--figures" not in sys.argv:
        from research import disease_experiment, noshow_experiment, scheduling_simulation
        print("=== 1/3 Disease prediction (D1) ===", flush=True)
        disease_experiment.run()
        print("=== 2/3 No-show prediction (D3) ===", flush=True)
        noshow_experiment.run()
        print("=== 3/3 Scheduling simulation ===", flush=True)
        scheduling_simulation.run()
    figs = figures()
    print(f"Figures: {len(figs)} written to {FIG_DIR}")
    print(f"Tables:  {tables()}")


if __name__ == "__main__":
    main()
