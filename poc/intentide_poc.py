#!/usr/bin/env python3
"""
INTENTIDE Proof-of-Concept — Collective Intent Stability for Scarce Capacity.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765
DISCLAIMER: PoC only — not production, not peer reviewed.
Library API: `from intentide import INTENTIDEEngine`
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intentide import (
    AgentIntent,
    AllocationResult,
    CoalitionFlip,
    ScenarioResult,
    allocate_fair,
    compute_stress_index,
    detect_unstable_coalitions,
    run_scenario,
    settlement_id,
    stability_protocol,
    stress_state,
)
from intentide.core import AUTHOR, ORCID, CAPACITY_SLOTS, MAX_STABILITY_ROUNDS, clamp, logistic

def print_allocation_table(scenario: ScenarioResult) -> None:
    print(f"\n=== {scenario.name} ===")
    print(f"Capacity: {scenario.capacity} slots | SSI: {scenario.stress_bps} bps ({scenario.stress_state})")
    print(f"Settlement ID: {scenario.settlement_id}")
    print(f"{'Agent':<12} {'Outcome':<12} {'Slot':<6} {'Stability':<10} {'Rank':<6} {'FCFS':<6}")
    print("-" * 58)
    arrival_map = {a.agent_id: a.arrival_order for a in scenario.agents}
    for alloc in scenario.allocations:
        slot = str(alloc.slot) if alloc.slot is not None else "-"
        print(
            f"{alloc.agent_id:<12} {alloc.outcome:<12} {slot:<6} "
            f"{alloc.stability_weight:<10.4f} {alloc.deterministic_rank:<6} {arrival_map[alloc.agent_id]:<6}"
        )
    if scenario.unstable_coalitions:
        print("\nUnstable coalition detected (outcome flips when agent removed):")
        for flip in scenario.unstable_coalitions[:3]:
            print(
                f"  remove {flip.removed_agent}: {flip.baseline_outcome} -> {flip.flipped_outcome}"
            )
    else:
        print("\nCoalition stable: no single-agent removal flips outcomes.")


def build_stable_agents() -> list[AgentIntent]:
    return [
        AgentIntent("agent-alpha", "cold-storage", 1, arrival_order=5, stability_weight=0.95),
        AgentIntent("agent-beta", "cold-storage", 1, arrival_order=1, stability_weight=0.88),
        AgentIntent("agent-gamma", "cold-storage", 1, arrival_order=3, stability_weight=0.91),
        AgentIntent("agent-delta", "cold-storage", 1, arrival_order=2, stability_weight=0.87),
        AgentIntent("agent-epsilon", "cold-storage", 1, arrival_order=4, stability_weight=0.90),
    ]


def build_stress_agents() -> list[AgentIntent]:
    return [
        AgentIntent("stress-a", "port-berth", 2, arrival_order=1, stability_weight=0.70),
        AgentIntent("stress-b", "port-berth", 2, arrival_order=2, stability_weight=0.72),
        AgentIntent("stress-c", "port-berth", 2, arrival_order=3, stability_weight=0.68),
        AgentIntent("stress-d", "port-berth", 1, arrival_order=4, stability_weight=0.75),
        AgentIntent("stress-e", "port-berth", 1, arrival_order=5, stability_weight=0.69),
        AgentIntent("stress-f", "port-berth", 1, arrival_order=6, stability_weight=0.71),
    ]


def scenario_to_dict(scenario: ScenarioResult) -> dict[str, Any]:
    return {
        "name": scenario.name,
        "capacity": scenario.capacity,
        "stress_bps": scenario.stress_bps,
        "stress_state": scenario.stress_state,
        "settlement_id": scenario.settlement_id,
        "stability_rounds": scenario.stability_rounds,
        "unstable_coalitions": [asdict(f) for f in scenario.unstable_coalitions],
        "agents": [asdict(a) for a in scenario.agents],
        "allocations": [asdict(a) for a in scenario.allocations],
    }


def main() -> None:
    print("INTENTIDE PoC - Collective Intent Stability for Scarce Capacity")
    print(f"Author: {AUTHOR} | ORCID: {ORCID}")

    stable = run_scenario("Stable Settlement (5 agents, 3 slots)", build_stable_agents(), CAPACITY_SLOTS)
    stress = run_scenario(
        "Stress Resolution (6 agents, 3 slots, oversubscribed)",
        build_stress_agents(),
        CAPACITY_SLOTS,
    )

    print_allocation_table(stable)
    print_allocation_table(stress)

    evidence = {
        "poc": "INTENTIDE",
        "author": AUTHOR,
        "orcid": ORCID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Proof-of-concept only. Not production. Not peer reviewed.",
        "demonstrations": {
            "stable_settlement": scenario_to_dict(stable),
            "stress_resolution": scenario_to_dict(stress),
        },
        "success_criteria": {
            "stable_settlement": stable.settlement_id.startswith("settle-"),
            "stress_resolved": all(a.outcome in ("GRANTED", "WAITLISTED") for a in stress.allocations),
            "deterministic_outcomes": len(stress.allocations) == len(stress.agents),
        },
    }

    out_path = Path(__file__).resolve().parent / "intentide_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\nEvidence written: {out_path}")
    print("INTENTIDE PoC complete.")


if __name__ == "__main__":
    main()

