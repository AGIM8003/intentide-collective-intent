#!/usr/bin/env python3
"""
INTENTIDE Benchmark Harness — Intent Stability Performance & Correctness

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: Proof-of-concept benchmark only. Not production validation.
Stdlib only. Reuses intentide_gate.py and intentide_poc.py logic.
"""

from __future__ import annotations

import json
import random
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from intentide_gate import (
    AgentIntent,
    SEED,
    defense_sybil_flooding,
    run_gate_pipeline,
    test_byzantine,
    test_deadlock,
    test_message_ordering_invariance,
    test_rapid_churn,
    test_scale,
)
from intentide_poc import build_stable_agents, build_stress_agents, run_scenario

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
DISCLAIMER = "PoC benchmark only — not production, not peer reviewed"
RESULTS_FILE = "intentide_benchmark_results.json"
CAPACITY = 3


@dataclass
class ScenarioResult:
    name: str
    size: str
    expected_pass: bool
    actual_pass: bool
    execution_time_ms: float
    memory_bytes_peak: int
    details: dict[str, Any]


def _measure(
    name: str, size: str, expected_pass: bool, fn: Callable[[], tuple[bool, dict[str, Any]]]
) -> ScenarioResult:
    tracemalloc.start()
    t0 = time.perf_counter()
    actual_pass, details = fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return ScenarioResult(
        name=name, size=size, expected_pass=expected_pass, actual_pass=actual_pass,
        execution_time_ms=round(elapsed_ms, 3), memory_bytes_peak=peak, details=details,
    )


def s01_stable_settlement() -> tuple[bool, dict[str, Any]]:
    result = run_scenario("stable", build_stable_agents(), CAPACITY)
    granted = sum(1 for a in result.allocations if a.outcome == "GRANTED")
    return granted == CAPACITY, {"granted": granted, "settlement_id": result.settlement_id}


def s02_stress_resolution() -> tuple[bool, dict[str, Any]]:
    result = run_scenario("stress", build_stress_agents(), CAPACITY)
    ok = all(a.outcome in ("GRANTED", "WAITLISTED") for a in result.allocations)
    return ok, {"stress_bps": result.stress_bps, "rounds": len(result.stability_rounds)}


def s03_byzantine_isolation() -> tuple[bool, dict[str, Any]]:
    t = test_byzantine()
    return t.passed, {"isolated": t.details.get("isolated_agents", [])}


def s04_ordering_invariance() -> tuple[bool, dict[str, Any]]:
    t = test_message_ordering_invariance()
    return t.passed, {"unique_outcomes": t.details.get("unique_outcomes")}


def s05_rapid_churn() -> tuple[bool, dict[str, Any]]:
    t = test_rapid_churn()
    return t.passed, {"settlement_id": t.details.get("settlement_id")}


def s06_deadlock_detection() -> tuple[bool, dict[str, Any]]:
    t = test_deadlock()
    return t.passed, {"status": t.details.get("status")}


def s07_sybil_defense() -> tuple[bool, dict[str, Any]]:
    d = defense_sybil_flooding()
    return d.blocked, {"throttled": d.details.get("throttled_identities")}


def s08_scale_100() -> tuple[bool, dict[str, Any]]:
    t = test_scale()
    return t.passed, {"granted": t.details.get("granted"), "agents": t.details.get("agents")}


def s09_scale_50() -> tuple[bool, dict[str, Any]]:
    rng = random.Random(SEED)
    agents = [
        AgentIntent(f"s50-{i:03d}", rng.choice(["compute", "storage"]), 1, i, round(0.5 + rng.random() * 0.5, 4))
        for i in range(50)
    ]
    result = run_gate_pipeline(agents, capacity=10)
    granted = sum(1 for a in result["allocations"] if a.outcome == "GRANTED")
    return granted == 10, {"agents": 50, "granted": granted, "stress_bps": result["stress_bps"]}


def s10_fairness_sample() -> tuple[bool, dict[str, Any]]:
    rng = random.Random(SEED + 3)
    tier_totals: dict[str, dict[str, int]] = {
        "high": {"granted": 0, "total": 0},
        "mid": {"granted": 0, "total": 0},
        "low": {"granted": 0, "total": 0},
    }
    for trial in range(100):
        n = rng.randint(8, 12)
        agents = []
        for i in range(n):
            roll = rng.random()
            if roll < 0.33:
                tier, w = "low", round(0.55 + rng.random() * 0.1, 4)
            elif roll < 0.66:
                tier, w = "mid", round(0.70 + rng.random() * 0.1, 4)
            else:
                tier, w = "high", round(0.85 + rng.random() * 0.14, 4)
            agents.append(AgentIntent(f"f{trial}-{i}", "fair", 1, i, stability_weight=w))
            tier_totals[tier]["total"] += 1
        result = run_gate_pipeline(agents, capacity=5)
        granted = {a.agent_id for a in result["allocations"] if a.outcome == "GRANTED"}
        for agent in agents:
            tier = (
                "high" if agent.stability_weight >= 0.85
                else "mid" if agent.stability_weight >= 0.70
                else "low"
            )
            if agent.agent_id in granted:
                tier_totals[tier]["granted"] += 1
    means = {
        t: d["granted"] / max(d["total"], 1) for t, d in tier_totals.items() if d["total"]
    }
    ok = means.get("high", 0) >= means.get("mid", 0) >= means.get("low", 0)
    return ok, {"tier_means": {k: round(v, 4) for k, v in means.items()}, "trials": 100}


SCENARIOS = [
    ("stable_settlement_5_agents", "small", True, s01_stable_settlement),
    ("stress_resolution_6_agents", "small", True, s02_stress_resolution),
    ("byzantine_intent_isolation", "small", True, s03_byzantine_isolation),
    ("message_ordering_invariance", "medium", True, s04_ordering_invariance),
    ("rapid_churn_deterministic", "medium", True, s05_rapid_churn),
    ("deadlock_detection_no_hang", "medium", True, s06_deadlock_detection),
    ("sybil_flooding_blocked", "medium", True, s07_sybil_defense),
    ("scale_100_agents_20_slots", "large", True, s08_scale_100),
    ("scale_50_agents_10_slots", "large", True, s09_scale_50),
    ("fairness_100_trial_sample", "large", True, s10_fairness_sample),
]


def compute_rates(results: list[ScenarioResult]) -> dict[str, float]:
    total = len(results)
    correct = sum(1 for r in results if r.expected_pass == r.actual_pass)
    fp = sum(1 for r in results if not r.expected_pass and r.actual_pass)
    fn = sum(1 for r in results if r.expected_pass and not r.actual_pass)
    neg = sum(1 for r in results if not r.expected_pass)
    pos = sum(1 for r in results if r.expected_pass)
    return {
        "correctness_rate": round(correct / total, 4) if total else 0.0,
        "false_positive_rate": round(fp / neg, 4) if neg else 0.0,
        "false_negative_rate": round(fn / pos, 4) if pos else 0.0,
        "correct": correct, "false_positives": fp, "false_negatives": fn, "total": total,
    }


def scalability_projection(results: list[ScenarioResult]) -> dict[str, Any]:
    large = [r for r in results if r.size == "large"]
    base_ms = sum(r.execution_time_ms for r in large) / max(len(large), 1)
    base_agents = 100
    return {
        "baseline_ms": round(base_ms, 3),
        "baseline_reference": "mean of large scenarios",
        "assumption": "linear O(n) extrapolation over agent count",
        "projections": {
            "10x": round(base_ms * 10, 3),
            "100x": round(base_ms * 100, 3),
            "1000x": round(base_ms * 1000, 3),
        },
        "projected_agents": {"10x": base_agents * 10, "100x": base_agents * 100, "1000x": base_agents * 1000},
    }


def run_benchmark() -> dict[str, Any]:
    results = [_measure(name, size, exp, fn) for name, size, exp, fn in SCENARIOS]
    rates = compute_rates(results)
    scale = scalability_projection(results)
    by_size = {}
    for sz in ("small", "medium", "large"):
        subset = [r for r in results if r.size == sz]
        if subset:
            by_size[sz] = {
                "count": len(subset),
                "mean_time_ms": round(sum(r.execution_time_ms for r in subset) / len(subset), 3),
                "mean_memory_kb": round(sum(r.memory_bytes_peak for r in subset) / len(subset) / 1024, 2),
            }
    return {
        "framework": "INTENTIDE",
        "harness": "intentide_benchmark",
        "author": AUTHOR,
        "orcid": ORCID,
        "disclaimer": DISCLAIMER,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "seed": SEED,
        "scenarios": [
            {
                "name": r.name, "size": r.size, "expected_pass": r.expected_pass,
                "actual_pass": r.actual_pass, "correct": r.expected_pass == r.actual_pass,
                "execution_time_ms": r.execution_time_ms, "memory_bytes_peak": r.memory_bytes_peak,
                "memory_kb_peak": round(r.memory_bytes_peak / 1024, 2), "details": r.details,
            }
            for r in results
        ],
        "metrics": rates,
        "by_size": by_size,
        "scalability_projection": scale,
        "memory_profile": {
            "largest_scenario": max(results, key=lambda r: r.memory_bytes_peak).name,
            "peak_memory_bytes": max(r.memory_bytes_peak for r in results),
            "peak_memory_kb": round(max(r.memory_bytes_peak for r in results) / 1024, 2),
        },
    }


def print_summary(report: dict[str, Any]) -> None:
    m, s = report["metrics"], report["scalability_projection"]
    print("\n" + "=" * 72)
    print("INTENTIDE BENCHMARK SUMMARY")
    print("=" * 72)
    print(f"{'SCENARIO':<42} {'SIZE':<8} {'PASS':<6} {'TIME(ms)':>10} {'MEM(KB)':>10}")
    print("-" * 72)
    for sc in report["scenarios"]:
        mark = "OK" if sc["correct"] else "MISS"
        print(f"{sc['name']:<42} {sc['size']:<8} {mark:<6} {sc['execution_time_ms']:>10.1f} {sc['memory_kb_peak']:>10.1f}")
    print("-" * 72)
    print(f"Correctness rate    : {m['correctness_rate']:.1%} ({m['correct']}/{m['total']})")
    print(f"False positive rate : {m['false_positive_rate']:.1%}")
    print(f"False negative rate : {m['false_negative_rate']:.1%}")
    print(f"\nScalability (baseline {s['baseline_ms']:.1f} ms):")
    for factor in ("10x", "100x", "1000x"):
        proj = s["projections"][factor]
        agents = s["projected_agents"][factor]
        print(f"  {factor:>5} (~{agents} agents): {proj:,.1f} ms ({proj / 1000:.2f} s)")
    print("=" * 72)


def main() -> int:
    print("INTENTIDE Benchmark Harness")
    print(f"Author: {AUTHOR} (ORCID {ORCID})")
    print(DISCLAIMER)
    report = run_benchmark()
    print_summary(report)
    out_path = Path(__file__).resolve().parent / RESULTS_FILE
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to: {out_path}")
    return 0 if report["metrics"]["correctness_rate"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
