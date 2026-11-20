"""
simulation_service.py - Serves REAL results of the scheduling simulation.

Numbers come from research/scheduling_simulation.py (28 days + 7-day warm-up,
20 seeds with common random numbers, FCFS vs fixed 30-min vs proposed C(t)).
Results for the five reported demand levels are precomputed in
results/scheduling_results.json (python -m research.run_all). Any other demand
level is simulated live with fewer seeds. Nothing here is hard-coded.
"""
import os
import sys
from typing import Any, Dict

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from research.common import load_json  # noqa: E402

_POLICY_KEYS = {"fcfs": ("fcfs", "First-Come-First-Served (FCFS)"),
                "fixed": ("fixed_slot", "Fixed 30-Minute Slots"),
                "proposed": ("proposed", "Proposed Priority-Aware C(t) + local rescheduling")}


def _m(x):
    return None if x is None else round(x["mean"], 2)


class SimulationService:
    def run_simulation(self, demand_multiplier: float = 1.0, seeds_count: int = 20) -> Dict[str, Any]:
        res = load_json("scheduling_results.json")
        key = None
        if res:
            levels = {float(k): k for k in res["summary"]}
            near = min(levels, key=lambda v: abs(v - demand_multiplier))
            if abs(near - demand_multiplier) < 1e-6:
                key = levels[near]
        if key is None:  # simulate live
            from research import scheduling_simulation as S
            live = _live_no_save(S, demand_multiplier)
            res, key, source = live, str(demand_multiplier), "live simulation (5 seeds)"
        else:
            source = "precomputed (results/scheduling_results.json)"
        summ = res["summary"][key]
        comp = {}
        for p, (out_key, label) in _POLICY_KEYS.items():
            s = summ[p]
            comp[out_key] = {
                "policy_name": label,
                "avg_waiting_days": _m(s["mean_wait_days"]),
                "excess_wait_days": _m(s.get("mean_excess_wait_days")),
                "urgent_wait_days": _m(s["urgent_wait_days"]),
                "high_wait_days": _m(s["high_wait_days"]),
                "urgent_seen_within_1_day_pct": _m(s["urgent_within_1_day_pct"]),
                "preference_satisfaction_pct": _m(s["preference_satisfaction_pct"]),
                "schedule_completion_pct": _m(s["scheduled_pct"]),
                "doctor_utilization_pct": _m(s["doctor_utilization_pct"]),
                "constraint_violations": res.get("constraint_violations", {}).get(p, 0),
                "patients_per_seed": _m(s["patients"]),
            }
        f, pr = comp["fcfs"], comp["proposed"]
        red = round(100 * (f["urgent_wait_days"] - pr["urgent_wait_days"]) / f["urgent_wait_days"], 1) if f["urgent_wait_days"] else 0.0
        absn = res.get("physician_absence", {})
        cfg = res["config"]
        return {
            "source": source,
            "parameters": {"duration_days": cfg["measured_days"], "warmup_days": cfg["warmup_days"],
                           "seeds_evaluated": cfg["seeds"], "demand_level": f"{demand_multiplier}x normal demand",
                           "departments_count": len(cfg["departments"]), "doctors": cfg["doctors"],
                           "consultation_durations": [15, 30, 45], "common_random_numbers": True},
            "comparison_summary": comp,
            "key_findings": {
                "urgent_wait_reduction_pct": red,
                "one_day_urgent_fulfillment_gain": round(pr["urgent_seen_within_1_day_pct"] - f["urgent_seen_within_1_day_pct"], 2),
                "preference_gain_pct_points": round(pr["preference_satisfaction_pct"] - f["preference_satisfaction_pct"], 2),
                "trade_off": (f"Average wait from request: FCFS {f['avg_waiting_days']} d vs proposed {pr['avg_waiting_days']} d - "
                              "the proposed policy deliberately books routine patients on their preferred later dates "
                              "and redistributes capacity toward urgent patients."),
            },
            "doctor_absence_experiment": {
                "scenario": "One General Medicine doctor unavailable for 7 days (announced 1 day ahead), baseline demand",
                "affected_appointments": round(absn.get("fixed", {}).get("affected_mean", 0), 1),
                "fixed_reschedule_lag_days": round(absn.get("fixed", {}).get("mean_delay_days", 0), 2),
                "proposed_reschedule_lag_days": round(absn.get("proposed", {}).get("mean_delay_days", 0), 2),
                "rescheduled_pct": round(absn.get("proposed", {}).get("rescheduled_pct", 0), 1),
            },
            "all_demand_levels": {k: {p: {"urgent_wait_days": _m(v[p]["urgent_wait_days"]),
                                          "avg_waiting_days": _m(v[p]["mean_wait_days"]),
                                          "urgent_within_1_day_pct": _m(v[p]["urgent_within_1_day_pct"])}
                                      for p in v} for k, v in res["summary"].items()},
        }


def _live_no_save(S, demand):
    # run without overwriting the precomputed results file
    import research.scheduling_simulation as mod
    orig = mod.save_json
    mod.save_json = lambda *a, **k: None
    try:
        return S.run(seeds=5, demands=[demand], verbose=False)
    finally:
        mod.save_json = orig


simulation_service = SimulationService()
