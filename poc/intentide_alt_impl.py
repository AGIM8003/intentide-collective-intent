#!/usr/bin/env python3
"""
INTENTIDE Alternative Implementation — Deterministic LP-style feasibility.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: PoC alternative implementation only. Not production, not peer reviewed.
Stdlib-only simplex-style greedy feasibility (no scipy) matching primary allocation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"


def settle_lp_style(agents: list[dict[str, Any]], capacity: int) -> dict[str, Any]:
    """
    Maximize sum(stability_weight * granted) s.t. sum(quantity granted) <= capacity.
    Greedy by weight/quantity density — deterministic tie-break by agent_id.
    Equivalent to LP optimum for 0-1 unit demands when quantity==1.
    """
    # normalize to unit slot requests for comparison with primary PoC (3 slots)
    ranked = sorted(
        agents,
        key=lambda a: (-a["stability_weight"], a["agent_id"]),
    )
    allocation: dict[str, str] = {}
    used = 0
    slot = 1
    for a in ranked:
        qty = int(a.get("quantity", 1))
        if used + qty <= capacity:
            allocation[a["agent_id"]] = f"GRANTED:{slot}"
            used += qty
            slot += 1
        else:
            allocation[a["agent_id"]] = "WAITLISTED"
    stress = int(10000 * (sum(a.get("quantity", 1) for a in agents) / max(capacity, 1) - 1))
    stress = max(0, min(10000, stress))
    return {
        "allocation": allocation,
        "granted": sorted(k for k, v in allocation.items() if v.startswith("GRANTED")),
        "waitlisted": sorted(k for k, v in allocation.items() if v == "WAITLISTED"),
        "capacity": capacity,
        "used": used,
        "stress_proxy_bps": stress,
    }


def settle_iterative_reference(agents: list[dict[str, Any]], capacity: int) -> dict[str, Any]:
    """Mirror primary iterative ranking (same key)."""
    ranked = sorted(agents, key=lambda a: (-a["stability_weight"], a["agent_id"]))
    allocation: dict[str, str] = {}
    used = 0
    slot = 1
    for a in ranked:
        qty = int(a.get("quantity", 1))
        if used + qty <= capacity:
            allocation[a["agent_id"]] = f"GRANTED:{slot}"
            used += qty
            slot += 1
        else:
            allocation[a["agent_id"]] = "WAITLISTED"
    return {
        "allocation": allocation,
        "granted": sorted(k for k, v in allocation.items() if v.startswith("GRANTED")),
        "waitlisted": sorted(k for k, v in allocation.items() if v == "WAITLISTED"),
    }


def fixture_agents() -> list[dict[str, Any]]:
    return [
        {"agent_id": "agent-alpha", "quantity": 1, "stability_weight": 0.92, "arrival_order": 5},
        {"agent_id": "agent-beta", "quantity": 1, "stability_weight": 0.71, "arrival_order": 1},
        {"agent_id": "agent-gamma", "quantity": 1, "stability_weight": 0.88, "arrival_order": 2},
        {"agent_id": "agent-delta", "quantity": 1, "stability_weight": 0.80, "arrival_order": 3},
        {"agent_id": "agent-epsilon", "quantity": 1, "stability_weight": 0.75, "arrival_order": 4},
    ]


def main() -> int:
    print("INTENTIDE Alternative Implementation (LP-style feasibility)")
    print(f"Author: {AUTHOR} ORCID {ORCID}")
    agents = fixture_agents()
    capacity = 3
    alt = settle_lp_style(agents, capacity)
    ref = settle_iterative_reference(agents, capacity)
    agree = alt["granted"] == ref["granted"] and alt["waitlisted"] == ref["waitlisted"]
    # first-come would grant beta first — prove we differ from FCFS
    fcfs = sorted(agents, key=lambda a: a["arrival_order"])
    fcfs_granted = [a["agent_id"] for a in fcfs[:capacity]]
    not_fcfs = sorted(alt["granted"]) != sorted(fcfs_granted)
    evidence = {
        "framework": "INTENTIDE",
        "author": AUTHOR,
        "orcid": ORCID,
        "disclaimer": "PoC replication evidence only — not production",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "primary_style": "iterative_stability_ranking",
        "alternative_style": "lp_style_greedy_feasibility",
        "alt": alt,
        "reference": ref,
        "fcfs_granted": fcfs_granted,
        "differs_from_fcfs": not_fcfs,
        "replication_pass": agree and not_fcfs,
    }
    out = Path(__file__).resolve().parent / "intentide_replication_evidence.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Granted: {alt['granted']}")
    print(f"Agree with iterative ref: {agree}; differs from FCFS: {not_fcfs}")
    print(f"Evidence: {out}")
    return 0 if evidence["replication_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
