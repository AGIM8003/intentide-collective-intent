#!/usr/bin/env python3
"""INTENTIDE public API integration tests."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from intentide import INTENTIDEEngine

OUT = Path(__file__).with_name("intentide_integration_results.json")


def run() -> dict:
    results = []

    e = INTENTIDEEngine(capacity=3)
    r = e.settle()
    results.append({"name": "empty_input", "pass": r.settlement_id == "settle-empty"})

    e = INTENTIDEEngine(capacity=1)
    e.add_agent("solo", quantity=1, arrival_order=1)
    r = e.settle()
    results.append({"name": "single_agent", "pass": r.allocations[0].outcome == "GRANTED"})

    e = INTENTIDEEngine(capacity=2)
    e.add_agent("a", arrival_order=1, stability_weight=1.2)
    e.add_agent("b", arrival_order=2, stability_weight=1.0)
    e.add_agent("c", arrival_order=3, stability_weight=0.9)
    r = e.settle()
    granted = sum(1 for a in r.allocations if a.outcome == "GRANTED")
    results.append({"name": "typical_oversubscribe", "pass": granted == 2 and r.settlement_id.startswith("settle-")})

    e = INTENTIDEEngine(capacity=10)
    for i in range(120):
        e.add_agent(f"A{i}", arrival_order=i, quantity=1)
    r = e.settle()
    results.append({"name": "large_scale_120", "pass": sum(1 for a in r.allocations if a.outcome == "GRANTED") == 10})

    ok_err = True
    e = INTENTIDEEngine(capacity=1)
    e.add_agent("x")
    try:
        e.add_agent("x")
        ok_err = False
    except ValueError:
        pass
    try:
        INTENTIDEEngine(capacity=-1)
        ok_err = False
    except ValueError:
        pass
    results.append({"name": "error_handling", "pass": ok_err})

    e = INTENTIDEEngine(capacity=10)
    e.add_agent("a1", arrival_order=1)
    e.add_agent("a2", arrival_order=2)
    r = e.settle()
    results.append({
        "name": "excess_capacity",
        "pass": all(a.outcome == "GRANTED" for a in r.allocations),
    })

    return {
        "framework": "INTENTIDE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "pass": all(x["pass"] for x in results),
    }


def main() -> int:
    evidence = run()
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"INTENTIDE integration pass={evidence['pass']}")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
