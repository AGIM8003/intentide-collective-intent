#!/usr/bin/env python3
"""INTENTIDE Mutation Testing. Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765. PoC only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"

AGENTS = [
    {"agent_id": "a", "stability_weight": 0.9, "quantity": 1, "arrival_order": 3},
    {"agent_id": "b", "stability_weight": 0.8, "quantity": 1, "arrival_order": 1},
    {"agent_id": "c", "stability_weight": 0.7, "quantity": 1, "arrival_order": 2},
    {"agent_id": "d", "stability_weight": 0.6, "quantity": 1, "arrival_order": 4},
]


def settle(agents: list[dict[str, Any]], capacity: int, key: Callable | None = None) -> list[str]:
    key = key or (lambda a: (-a["stability_weight"], a["agent_id"]))
    ranked = sorted(agents, key=key)
    granted = []
    used = 0
    for a in ranked:
        if used + a["quantity"] <= capacity:
            granted.append(a["agent_id"])
            used += a["quantity"]
    return granted


def no_double(agents, capacity, settle_fn) -> bool:
    g = settle_fn(agents, capacity)
    return len(g) == len(set(g)) and len(g) <= capacity


def oracle(settle_fn: Callable) -> list[tuple[str, bool]]:
    g = settle_fn(AGENTS, 2)
    tests = []
    tests.append(("grants_2", len(g) == 2))
    tests.append(("top_weights", set(g) == {"a", "b"}))
    tests.append(("not_fcfs", set(g) != {"b", "c"}))  # arrival 1,2 would be b,c
    tests.append(("no_double", no_double(AGENTS, 2, settle_fn)))
    tests.append(("capacity_respected", len(settle_fn(AGENTS, 1)) == 1))
    tests.append(("all_wait_if_zero", settle_fn(AGENTS, 0) == []))
    return tests


def main() -> int:
    rows = []

    def run(name, fn):
        try:
            results = oracle(fn)
            failed = [n for n, ok in results if not ok]
            rows.append({"name": name, "detected": bool(failed), "caught_by": failed[0] if failed else None})
        except Exception as exc:
            rows.append({"name": name, "detected": True, "caught_by": f"exc:{exc}"})

    run("baseline_should_pass", lambda ag, cap: settle(ag, cap))
    # mutations — baseline may pass; we only score mutations
    rows = []
    run("fcfs_instead_of_weight", lambda ag, cap: settle(ag, cap, key=lambda a: (a["arrival_order"], a["agent_id"])))
    run("ignore_capacity", lambda ag, cap: [a["agent_id"] for a in ag])
    run("empty_always", lambda ag, cap: [])
    run("duplicate_grant", lambda ag, cap: ["a", "a"])
    run("reverse_weights", lambda ag, cap: settle(ag, cap, key=lambda a: (a["stability_weight"], a["agent_id"])))
    run("skip_quantity", lambda ag, cap: [a["agent_id"] for a in sorted(ag, key=lambda x: -x["stability_weight"])][: max(cap, 3)])
    run("crash_on_empty", lambda ag, cap: settle(ag, cap) if ag else 1 / 0)
    run("over_allocate", lambda ag, cap: settle(ag, cap + 10))
    run("drop_first_agent", lambda ag, cap: settle(ag[1:], cap))
    run("hardcode_wrong", lambda ag, cap: ["c", "d"])

    # remove baseline if any
    detected = sum(1 for r in rows if r["detected"])
    score = detected / len(rows)
    report = {
        "framework": "INTENTIDE",
        "author": AUTHOR,
        "orcid": ORCID,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mutations_total": len(rows),
        "mutations_detected": detected,
        "mutation_score": round(score, 3),
        "pass_threshold": 0.9,
        "mutations": rows,
        "suite_pass": score >= 0.9,
    }
    out = Path(__file__).resolve().parent / "intentide_mutation_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"INTENTIDE mutation score: {score:.0%} ({detected}/{len(rows)})")
    for r in rows:
        print(f"  [{'CAUGHT' if r['detected'] else 'SURVIVED'}] {r['name']}")
    return 0 if report["suite_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
