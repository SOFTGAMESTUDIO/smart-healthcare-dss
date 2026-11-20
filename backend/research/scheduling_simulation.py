"""
Appointment scheduling simulation (report Sections 3.6 and 4.x) - a REAL simulation.

Setting
  * 8 departments, 16 doctors, 6-hour clinic days (360 min), Sunday closed
  * daily booking limit of 14 patients per doctor
  * consultation length 15 / 30 / 45 min (longer for urgent patients)
  * priorities: Urgent 15%, High 25%, Routine 60%
  * patients have a preferred day window and a preferred time of day
  * requests arrive on working days (Poisson) and are booked into slots from the
    same day onward (same-day appointments are possible for every policy)
  * 35 simulated days = 7-day warm-up + 28 measured days
  * 20 seeds with common random numbers (each policy sees the SAME patients)
  * 5 demand levels: 0.6, 0.85, 1.0, 1.2, 1.5 x normal demand

Policies
  1. FCFS           - requests in arrival order, earliest feasible slot
  2. Fixed 30-min   - requests in arrival order, rigid 30-min slots (45-min visits take 2)
  3. Proposed       - requests in priority order; each candidate slot t is scored with
                      C(t) = w1*Wait(t)*w_priority + w2*PrefPenalty(t) + w3*UtilPenalty(t) + w4*Imbalance(t)
                      plus local rescheduling: if an urgent patient cannot be seen within 1 day,
                      a routine appointment in the next day is postponed to make room
                      (each patient is postponed at most once)

Physician-absence experiment
  A doctor is unavailable for 7 days (announced on day 14). Affected bookings are
  rescheduled: Fixed policy -> same doctor after return; Proposed -> any eligible
  doctor via C(t), urgent first. Metric: average delay in days.

Every schedule is verified afterwards (capacity, daily limit, department
eligibility, absence) and violations are counted.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List

import numpy as np

from research.common import save_json

DEPTS = {"Pulmonology": 2, "Gastroenterology": 2, "General Medicine": 3, "Cardiology": 2,
         "Dermatology": 2, "Neurology": 2, "Orthopedics": 2, "ENT": 1}
DAY_MIN = 360
DAILY_LIMIT = 14
WARMUP, MEASURE = 7, 28
SIM_DAYS = WARMUP + MEASURE
HORIZON = 60          # booking horizon (days after arrival)
PRIORITY_P = {"Urgent": 0.15, "High": 0.25, "Routine": 0.60}
DURATION_P = {"Urgent": ([15, 30, 45], [0.2, 0.5, 0.3]),
              "High": ([15, 30, 45], [0.3, 0.5, 0.2]),
              "Routine": ([15, 30, 45], [0.45, 0.45, 0.10])}
W_PRIORITY = {"Urgent": 10.0, "High": 2.0, "Routine": 0.3}
WEIGHTS = {"wait": 1.0, "pref": 1.5, "util": 0.3, "imbalance": 0.4}
BASE_LOAD = 1.0        # normal demand = nominal clinic capacity (queues form, as in a busy OPD)
DEMANDS = [0.6, 0.85, 1.0, 1.2, 1.5]


def working(day: int) -> bool:
    return day % 7 != 6


def doctors():
    out = []
    for dept, n in DEPTS.items():
        for i in range(n):
            out.append({"id": len(out), "dept": dept, "name": f"{dept[:4]}-{i+1}"})
    return out


def generate_requests(seed: int, demand: float) -> List[dict]:
    rng = np.random.default_rng(seed)
    docs = doctors()
    mean_dur = {p: float(np.dot(*DURATION_P[p])) for p in PRIORITY_P}
    avg_dur = sum(PRIORITY_P[p] * mean_dur[p] for p in PRIORITY_P)
    reqs = []
    for day in range(SIM_DAYS):
        if not working(day):
            continue
        for dept, n in DEPTS.items():
            lam = BASE_LOAD * demand * n * DAY_MIN / avg_dur
            for _ in range(rng.poisson(lam)):
                pr = rng.choice(list(PRIORITY_P), p=list(PRIORITY_P.values()))
                durs, probs = DURATION_P[pr]
                if pr == "Urgent":
                    pref_delay = 0
                elif pr == "High":
                    pref_delay = int(rng.choice([0, 1, 2], p=[0.5, 0.3, 0.2]))
                else:
                    pref_delay = int(rng.choice([1, 2, 3, 5, 7], p=[0.3, 0.25, 0.2, 0.15, 0.1]))
                reqs.append({"id": len(reqs), "arrival": day, "dept": dept, "priority": pr,
                             "duration": int(rng.choice(durs, p=probs)),
                             "pref_start": day + pref_delay, "pref_len": 3,
                             "pref_tod": str(rng.choice(["morning", "afternoon", "any"], p=[0.4, 0.3, 0.3])),
                             "order": float(rng.random())})
    return reqs


class Schedule:
    def __init__(self, fixed_slots: bool = False):
        self.docs = doctors()
        self.by_dept: Dict[str, List[int]] = {}
        for d in self.docs:
            self.by_dept.setdefault(d["dept"], []).append(d["id"])
        self.fixed = fixed_slots
        self.used: Dict[tuple, int] = {}       # (doc, day) -> minutes
        self.count: Dict[tuple, int] = {}      # (doc, day) -> patients
        self.appts: Dict[tuple, list] = {}     # (doc, day) -> [request ids]
        self.assign: Dict[int, tuple] = {}     # request id -> (doc, day, start)
        self.absent: set = set()               # (doc, day)

    def cost_minutes(self, dur):
        return 30 * math.ceil(dur / 30) if self.fixed else dur

    def feasible(self, doc, day, dur):
        if not working(day) or (doc, day) in self.absent:
            return False
        return (self.used.get((doc, day), 0) + self.cost_minutes(dur) <= DAY_MIN
                and self.count.get((doc, day), 0) < DAILY_LIMIT)

    def book(self, r, doc, day):
        k = (doc, day)
        start = self.used.get(k, 0)
        self.used[k] = start + self.cost_minutes(r["duration"])
        self.count[k] = self.count.get(k, 0) + 1
        self.appts.setdefault(k, []).append(r["id"])
        self.assign[r["id"]] = (doc, day, start)

    def unbook(self, r):
        doc, day, _ = self.assign.pop(r["id"])
        k = (doc, day)
        self.used[k] -= self.cost_minutes(r["duration"])
        self.count[k] -= 1
        self.appts[k].remove(r["id"])


def tod_of(start):
    return "morning" if start < DAY_MIN / 2 else "afternoon"


def pref_ok(r, day, start):
    in_window = r["pref_start"] <= day < r["pref_start"] + r["pref_len"]
    return in_window and (r["pref_tod"] == "any" or r["pref_tod"] == tod_of(start))


def earliest(s: Schedule, r, first_day, docs=None, until=None):
    docs = docs if docs is not None else s.by_dept[r["dept"]]
    last = until if until is not None else r["arrival"] + HORIZON
    for day in range(first_day, last + 1):
        for doc in docs:
            if s.feasible(doc, day, r["duration"]):
                return doc, day
    return None


def c_of_t(s: Schedule, r, doc, day):
    wait = day - r["arrival"]
    start = s.used.get((doc, day), 0)
    pref = 0.0
    if not (r["pref_start"] <= day < r["pref_start"] + r["pref_len"]):
        pref = min(abs(day - r["pref_start"]), abs(day - (r["pref_start"] + r["pref_len"] - 1)))
    if r["pref_tod"] != "any" and r["pref_tod"] != tod_of(start):
        pref += 0.5
    util_after = (start + r["duration"]) / DAY_MIN
    util_pen = 1.0 - util_after
    loads = [s.used.get((d, day), 0) for d in s.by_dept[r["dept"]]]
    imbalance = (start - (sum(loads) / len(loads))) / DAY_MIN
    return (WEIGHTS["wait"] * wait * W_PRIORITY[r["priority"]] + WEIGHTS["pref"] * pref
            + WEIGHTS["util"] * util_pen + WEIGHTS["imbalance"] * max(0.0, imbalance))


def best_slot(s: Schedule, r, first_day, docs=None):
    docs = docs if docs is not None else s.by_dept[r["dept"]]
    best, best_c = None, math.inf
    for day in range(first_day, r["arrival"] + HORIZON + 1):
        if WEIGHTS["wait"] * (day - r["arrival"]) * W_PRIORITY[r["priority"]] >= best_c:
            break  # every later day costs at least this much -> prune
        for doc in docs:
            if s.feasible(doc, day, r["duration"]):
                c = c_of_t(s, r, doc, day)
                if c < best_c:
                    best, best_c = (doc, day), c
    return best


def next_working(day):
    d = day + 1
    while not working(d):
        d += 1
    return d


def simulate(policy: str, reqs: List[dict]):
    s = Schedule(fixed_slots=(policy == "fixed"))
    by_id = {r["id"]: r for r in reqs}
    postponed = set()
    unscheduled = []
    for day in range(SIM_DAYS):
        today = [r for r in reqs if r["arrival"] == day]
        if not today:
            continue
        first = day
        if policy == "proposed":
            today.sort(key=lambda r: (-W_PRIORITY[r["priority"]], r["order"]))
        else:
            today.sort(key=lambda r: r["order"])
        for r in today:
            if policy == "proposed":
                slot = best_slot(s, r, first)
                if r["priority"] == "Urgent" and (slot is None or slot[1] > first):
                    slot = _make_room(s, r, first, by_id, postponed) or slot
            else:
                slot = earliest(s, r, first)
            if slot is None:
                unscheduled.append(r["id"])
            else:
                s.book(r, *slot)
    return s, unscheduled, postponed


def _make_room(s, r, day, by_id, postponed):
    """Postpone one routine appointment on `day` so the urgent patient fits."""
    for doc in s.by_dept[r["dept"]]:
        if (doc, day) in s.absent or not working(day):
            continue
        cands = [by_id[i] for i in s.appts.get((doc, day), [])
                 if by_id[i]["priority"] == "Routine" and i not in postponed]
        cands.sort(key=lambda x: -x["duration"])
        for victim in cands:
            free = DAY_MIN - s.used.get((doc, day), 0) + s.cost_minutes(victim["duration"])
            if free < s.cost_minutes(r["duration"]):
                continue
            s.unbook(victim)
            new = best_slot(s, victim, day + 1)
            if new is None:
                s.book(victim, doc, day)
                continue
            s.book(victim, *new)
            postponed.add(victim["id"])
            if s.feasible(doc, day, r["duration"]):
                return doc, day
    return None


def verify(s: Schedule, reqs) -> int:
    v = 0
    by_id = {r["id"]: r for r in reqs}
    dept_of = {d["id"]: d["dept"] for d in s.docs}
    for (doc, day), ids in s.appts.items():
        if not ids:
            continue
        mins = sum(s.cost_minutes(by_id[i]["duration"]) for i in ids)
        v += mins > DAY_MIN
        v += len(ids) > DAILY_LIMIT
        v += (doc, day) in s.absent
        v += not working(day)
        v += sum(dept_of[doc] != by_id[i]["dept"] for i in ids)
    return int(v)


def metrics(s: Schedule, reqs, unscheduled):
    m = [r for r in reqs if WARMUP <= r["arrival"] < SIM_DAYS]
    ids = {r["id"] for r in m}
    waits = {r["id"]: s.assign[r["id"]][1] - r["arrival"] for r in m if r["id"] in s.assign}
    urg = [waits[r["id"]] for r in m if r["priority"] == "Urgent" and r["id"] in waits]
    high = [waits[r["id"]] for r in m if r["priority"] == "High" and r["id"] in waits]
    excess = [max(0, s.assign[r["id"]][1] - r["pref_start"]) for r in m if r["id"] in s.assign]
    pref = [pref_ok(r, s.assign[r["id"]][1], s.assign[r["id"]][2]) for r in m if r["id"] in s.assign]
    cap = sum(DAY_MIN for d in s.docs for day in range(WARMUP + 1, SIM_DAYS + 1) if working(day))
    used = sum(v for (doc, day), v in s.used.items() if WARMUP + 1 <= day <= SIM_DAYS)
    return {
        "patients": len(m),
        "mean_wait_days": float(np.mean(list(waits.values()))) if waits else None,
        "mean_excess_wait_days": float(np.mean(excess)) if excess else None,
        "urgent_wait_days": float(np.mean(urg)) if urg else None,
        "high_wait_days": float(np.mean(high)) if high else None,
        "urgent_within_1_day_pct": float(100 * np.mean([w <= 1 for w in urg])) if urg else None,
        "preference_satisfaction_pct": float(100 * np.mean(pref)) if pref else None,
        "scheduled_pct": float(100 * len(waits) / len(m)) if m else None,
        "doctor_utilization_pct": float(100 * used / cap),
        "unscheduled": int(len([i for i in unscheduled if i in ids])),
    }


def absence_experiment(seed: int, policy: str, absent_doc: int = 4, start: int = 15, length: int = 7):
    """Doctor `absent_doc` (General Medicine) is away for `length` days from `start`.

    Both policies start from the SAME pre-absence schedule (built by the proposed
    booking rule); only the rescheduling rule differs, which isolates its effect.
    """
    reqs = generate_requests(seed, 1.0)
    upto = [r for r in reqs if r["arrival"] < start - 1]  # bookings made before the announcement
    s, _, _ = simulate("proposed", upto)
    by_id = {r["id"]: r for r in upto}
    days = set(range(start, start + length))
    affected = [by_id[i] for (doc, day), ids in list(s.appts.items()) if doc == absent_doc and day in days for i in ids]
    orig = {r["id"]: s.assign[r["id"]][1] for r in affected}
    for r in affected:
        s.unbook(r)
    for d in days:
        s.absent.add((absent_doc, d))
    delays = []
    if policy == "fixed":
        ret = start + length
        for r in sorted(affected, key=lambda r: orig[r["id"]]):
            slot = earliest(s, r, ret, docs=[absent_doc], until=ret + HORIZON)
            if slot:
                s.book(r, *slot)
                delays.append(slot[1] - orig[r["id"]])
    else:
        for r in sorted(affected, key=lambda r: (-W_PRIORITY[r["priority"]], orig[r["id"]])):
            rr = dict(r, arrival=start - 1)  # reschedule decision made on announcement day
            slot = best_slot(s, rr, start)
            if slot:
                s.book(r, *slot)
                delays.append(max(0, slot[1] - orig[r["id"]]))
    return {"affected": len(affected), "rescheduled": len(delays),
            "mean_delay_days": float(np.mean(delays)) if delays else 0.0,
            "violations": verify(s, upto)}


def run(seeds: int = 20, demands=DEMANDS, verbose: bool = True):
    t0 = time.time()
    policies = ["fcfs", "fixed", "proposed"]
    per = {str(d): {p: [] for p in policies} for d in demands}
    violations = {p: 0 for p in policies}
    for demand in demands:
        for seed in range(seeds):
            reqs = generate_requests(1000 + seed, demand)   # common random numbers across policies
            for p in policies:
                s, uns, _ = simulate(p, reqs)
                per[str(demand)][p].append(metrics(s, reqs, uns))
                violations[p] += verify(s, reqs)
        if verbose:
            print(f"[schedule] demand {demand} done ({time.time()-t0:.0f}s)", flush=True)

    def agg(lst, key):
        vals = [x[key] for x in lst if x[key] is not None]
        return {"mean": float(np.mean(vals)), "std": float(np.std(vals))} if vals else None

    keys = ["mean_wait_days", "mean_excess_wait_days", "urgent_wait_days", "high_wait_days", "urgent_within_1_day_pct",
            "preference_satisfaction_pct", "scheduled_pct", "doctor_utilization_pct", "patients"]
    summary = {d: {p: {k: agg(per[d][p], k) for k in keys} for p in policies} for d in per}
    absence = {p: [absence_experiment(1000 + s_, p) for s_ in range(seeds)] for p in ("fixed", "proposed")}
    absence_sum = {p: {"mean_delay_days": float(np.mean([a["mean_delay_days"] for a in v])),
                       "affected_mean": float(np.mean([a["affected"] for a in v])),
                       "rescheduled_pct": float(100 * sum(a["rescheduled"] for a in v) / max(1, sum(a["affected"] for a in v))),
                       "violations": int(sum(a["violations"] for a in v))} for p, v in absence.items()}
    base = summary.get("1.0") or summary[str(demands[0])]
    f, pr = base["fcfs"]["urgent_wait_days"]["mean"], base["proposed"]["urgent_wait_days"]["mean"]
    out = {
        "config": {"departments": DEPTS, "doctors": sum(DEPTS.values()), "day_minutes": DAY_MIN,
                   "daily_limit": DAILY_LIMIT, "warmup_days": WARMUP, "measured_days": MEASURE,
                   "seeds": seeds, "demand_levels": demands, "priority_mix": PRIORITY_P,
                   "weights": WEIGHTS, "priority_weights": W_PRIORITY, "baseline_load": BASE_LOAD,
                   "common_random_numbers": True},
        "summary": summary, "constraint_violations": violations, "physician_absence": absence_sum,
        "headline": {"urgent_wait_reduction_pct_vs_fcfs": float(100 * (f - pr) / f) if f else None,
                     "urgent_within_1_day_fcfs": base["fcfs"]["urgent_within_1_day_pct"]["mean"],
                     "urgent_within_1_day_proposed": base["proposed"]["urgent_within_1_day_pct"]["mean"]},
        "runtime_seconds": round(time.time() - t0, 1),
    }
    save_json("scheduling_results.json", out)
    if verbose:
        print(f"[schedule] done in {out['runtime_seconds']} s")
    return out


if __name__ == "__main__":
    run()
