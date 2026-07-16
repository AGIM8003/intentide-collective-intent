#!/usr/bin/env python3
"""
INTENTIDE Stress-Scale Test — 500 agents, 50 resource units, ~10:1 oversubscription.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intentide_poc import (
    AgentIntent,
    allocate_fair,
    compute_stress_index,
    detect_unstable_coalitions,
    settlement_id,
    stability_protocol,
    stress_state,
)

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
OUT = Path(__file__).with_name("intentide_stress_results.json")

BASE = {"agents": 500, "capacity": 50}


def build_agents(n: int) -> list[AgentIntent]:
    classes = ["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON"]
    agents = []
    for i in range(n):
        agents.append(
            AgentIntent(
                agent_id=f"A_{i:04d}",
                resource_class=classes[i % len(classes)],
                quantity=1,  # keep ~10:1 oversubscription at base (500/50)
                arrival_order=i if i < n // 2 else i + n,  # retries in second half
                stability_weight=round(0.8 + (i % 20) * 0.01, 4),
            )
        )
    return agents


def run_once(n_agents: int, capacity: int, coalition_sample: int = 40) -> dict[str, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()
    agents = build_agents(n_agents)
    t_build = time.perf_counter() - t0

    t1 = time.perf_counter()
    stress_bps, features = compute_stress_index(agents, capacity)
    t_stress = time.perf_counter() - t1

    t2 = time.perf_counter()
    stabilized, rounds = stability_protocol(agents, stress_bps, capacity)
    t_stability = time.perf_counter() - t2

    t3 = time.perf_counter()
    allocations = allocate_fair(stabilized, capacity)
    settle = settlement_id(stabilized, allocations)
    t_alloc = time.perf_counter() - t3

    # Coalition detection is O(n²); sample subset at large scale
    t4 = time.perf_counter()
    sample = stabilized[: min(coalition_sample, len(stabilized))]
    flips = detect_unstable_coalitions(sample, capacity)
    t_coalition = time.perf_counter() - t4

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = time.perf_counter() - t0
    final_stress, _ = compute_stress_index(stabilized, capacity)
    demand = sum(a.quantity for a in agents)

    return {
        "scale": {
            "agents": n_agents,
            "capacity": capacity,
            "oversubscription_ratio": round(demand / max(capacity, 1), 3),
            "coalition_sample": len(sample),
        },
        "timing_s": {
            "build": round(t_build, 6),
            "stress_index": round(t_stress, 6),
            "stability_protocol": round(t_stability, 6),
            "allocation_settlement": round(t_alloc, 6),
            "coalition_sample": round(t_coalition, 6),
            "total": round(total, 6),
            "per_agent_stability_ms": round(1000 * t_stability / max(n_agents, 1), 6),
        },
        "memory": {
            "current_bytes": current,
            "peak_bytes": peak,
            "peak_mb": round(peak / (1024 * 1024), 4),
        },
        "results": {
            "initial_stress_bps": stress_bps,
            "final_stress_bps": final_stress,
            "stress_state": stress_state(final_stress),
            "stability_rounds": len(rounds),
            "granted": sum(1 for a in allocations if a.outcome == "GRANTED"),
            "settlement_id": settle,
            "unstable_coalitions_in_sample": len(flips),
            "features": features,
        },
    }


def main() -> int:
    curve = []
    for m in [1, 2, 5, 10]:
        n = BASE["agents"] * m
        cap = BASE["capacity"] * m
        print(f"INTENTIDE stress {m}x agents={n} capacity={cap}")
        row = run_once(n, cap, coalition_sample=30 if m >= 5 else 40)
        row["multiplier"] = m
        curve.append(row)
        print(f"  total={row['timing_s']['total']}s peak_mb={row['memory']['peak_mb']}")

    base_t = curve[0]["timing_s"]
    ops = [
        "build",
        "stress_index",
        "stability_protocol",
        "allocation_settlement",
        "coalition_sample",
    ]
    bottleneck = max(ops, key=lambda k: base_t[k])
    growth = {
        op: [
            {
                "multiplier": r["multiplier"],
                "seconds": r["timing_s"][op],
                "vs_1x": round(r["timing_s"][op] / max(base_t[op], 1e-9), 3),
            }
            for r in curve
        ]
        for op in ops
    }

    out = {
        "framework": "INTENTIDE",
        "script": "intentide_stress.py",
        "author": AUTHOR,
        "orcid": ORCID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_target": BASE,
        "note": (
            "Full O(n²) coalition detection is sampled at stress scale; "
            "documented as a known scaling gap."
        ),
        "scalability_curve": curve,
        "bottleneck_operation": bottleneck,
        "bottleneck_rationale": (
            f"Dominant measured op at 1× is '{bottleneck}'. Full coalition "
            "detection would dominate beyond sample size — see Honest Gap Register."
        ),
        "growth_by_operation": growth,
        "pass": (
            all(r["results"]["granted"] == r["scale"]["capacity"] for r in curve)
            and abs(curve[0]["scale"]["oversubscription_ratio"] - 10) < 3
            and len(curve) == 4
        ),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"bottleneck={bottleneck} pass={out['pass']} oversub={curve[0]['scale']['oversubscription_ratio']}")
    print(f"Wrote {OUT.name}")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
