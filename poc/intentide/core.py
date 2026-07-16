"""INTENTIDE core protocol. Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field
from typing import Any

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
CAPACITY_SLOTS = 3
MAX_STABILITY_ROUNDS = 4


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def stress_state(bps: int) -> str:
    if bps < 3500:
        return "NORMAL"
    if bps < 6000:
        return "JITTER"
    if bps < 8500:
        return "RESERVE"
    return "EMERGENCY_PAUSE"


@dataclass
class AgentIntent:
    agent_id: str
    resource_class: str
    quantity: int
    arrival_order: int
    stability_weight: float = 1.0
    confirmed: bool = False
    revised: bool = False

    def commitment_hash(self) -> str:
        payload = f"{self.agent_id}:{self.resource_class}:{self.quantity}:{self.stability_weight:.4f}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class AllocationResult:
    agent_id: str
    outcome: str
    slot: int | None
    stability_weight: float
    deterministic_rank: int


@dataclass
class CoalitionFlip:
    coalition: list[str]
    removed_agent: str
    baseline_outcome: str
    flipped_outcome: str


@dataclass
class ScenarioResult:
    name: str
    capacity: int
    agents: list[AgentIntent]
    stress_bps: int
    stress_state: str
    stability_rounds: list[dict[str, Any]]
    unstable_coalitions: list[CoalitionFlip]
    allocations: list[AllocationResult]
    settlement_id: str


def compute_stress_index(agents: list[AgentIntent], capacity: int) -> tuple[int, dict[str, float]]:
    """Synchronization Stress Index — deterministic simulation formula (Section 11.2)."""
    total_demand = sum(a.quantity for a in agents)
    d_ratio = total_demand / max(capacity, 1)

    classes = [a.resource_class for a in agents]
    class_counts: dict[str, int] = {}
    for cls in classes:
        class_counts[cls] = class_counts.get(cls, 0) + 1
    n = len(agents)
    semantic_concentration = max(class_counts.values()) / n if n else 0.0

    arrival_orders = sorted(a.arrival_order for a in agents)
    if len(arrival_orders) >= 3:
        window = arrival_orders[-1] - arrival_orders[0]
        narrow = sum(1 for o in arrival_orders if o - arrival_orders[0] <= max(window * 0.25, 1))
        timing_concentration = narrow / len(arrival_orders)
    else:
        timing_concentration = 0.5

    retries = sum(1 for a in agents if a.arrival_order > n)
    retry_amplification = retries / max(n, 1)
    provider_concentration = semantic_concentration
    substitution_spillover = 0.15 if len(class_counts) > 1 else 0.05
    arrival_acceleration = min(d_ratio - 1.0, 2.0) if d_ratio > 1.0 else 0.1
    integrity_anomaly = 0.0
    recovery_confidence = 0.35 if d_ratio <= 1.0 else max(0.0, 0.6 - 0.15 * (d_ratio - 1.0))

    features = {
        "arrival_acceleration": arrival_acceleration,
        "demand_capacity_ratio": d_ratio,
        "semantic_concentration": semantic_concentration,
        "retry_amplification": retry_amplification,
        "substitution_spillover": substitution_spillover,
        "provider_concentration": provider_concentration,
        "timing_concentration": timing_concentration,
        "integrity_anomaly": integrity_anomaly,
        "recovery_confidence": recovery_confidence,
    }

    raw = (
        0.18 * features["arrival_acceleration"]
        + 0.24 * features["demand_capacity_ratio"]
        + 0.12 * features["semantic_concentration"]
        + 0.14 * features["retry_amplification"]
        + 0.08 * features["substitution_spillover"]
        + 0.08 * features["provider_concentration"]
        + 0.08 * features["timing_concentration"]
        + 0.08 * features["integrity_anomaly"]
        - 0.10 * features["recovery_confidence"]
    )
    stress_bps = int(clamp(round(10000 * logistic(raw)), 0, 10000))
    return stress_bps, features


def stability_protocol(
    agents: list[AgentIntent], stress_bps: int, capacity: int
) -> tuple[list[AgentIntent], list[dict[str, Any]]]:
    """Iterative revise-or-confirm until coalition stress stabilizes."""
    working = [AgentIntent(**asdict(a)) for a in agents]
    rounds: list[dict[str, Any]] = []

    for round_idx in range(1, MAX_STABILITY_ROUNDS + 1):
        stress_bps, _ = compute_stress_index(working, capacity)
        actions: list[str] = []

        for agent in working:
            if agent.confirmed:
                continue
            if stress_bps >= 6000 and agent.quantity > 1:
                agent.quantity = max(1, agent.quantity - 1)
                agent.revised = True
                agent.stability_weight = round(agent.stability_weight * 0.92, 4)
                actions.append(f"{agent.agent_id}: revised quantity -> {agent.quantity}")
            else:
                agent.confirmed = True
                agent.stability_weight = round(agent.stability_weight + 0.05, 4)
                actions.append(f"{agent.agent_id}: confirmed")

        rounds.append(
            {
                "round": round_idx,
                "stress_bps": stress_bps,
                "stress_state": stress_state(stress_bps),
                "actions": actions,
            }
        )

        if all(a.confirmed for a in working):
            break

    return working, rounds


def allocate_fair(
    agents: list[AgentIntent], capacity: int
) -> list[AllocationResult]:
    """
    Fair reservation: stability-weighted ordering, not first-come-first-served.
    Deterministic tie-break via commitment hash.
    """
    ranked = sorted(
        agents,
        key=lambda a: (-a.stability_weight, a.commitment_hash(), a.arrival_order),
    )

    results: list[AllocationResult] = []
    slots_remaining = capacity

    for rank, agent in enumerate(ranked, start=1):
        if slots_remaining > 0 and agent.quantity >= 1:
            slot = capacity - slots_remaining + 1
            slots_remaining -= 1
            results.append(
                AllocationResult(
                    agent_id=agent.agent_id,
                    outcome="GRANTED",
                    slot=slot,
                    stability_weight=agent.stability_weight,
                    deterministic_rank=rank,
                )
            )
        else:
            results.append(
                AllocationResult(
                    agent_id=agent.agent_id,
                    outcome="WAITLISTED",
                    slot=None,
                    stability_weight=agent.stability_weight,
                    deterministic_rank=rank,
                )
            )

    return results


def detect_unstable_coalitions(
    agents: list[AgentIntent], capacity: int
) -> list[CoalitionFlip]:
    """Detect coalitions where removing one agent flips another agent's outcome."""
    baseline = {r.agent_id: r.outcome for r in allocate_fair(agents, capacity)}
    flips: list[CoalitionFlip] = []

    for removed in agents:
        subset = [a for a in agents if a.agent_id != removed.agent_id]
        if not subset:
            continue
        subset_outcomes = {r.agent_id: r.outcome for r in allocate_fair(subset, capacity)}
        for agent_id, outcome in baseline.items():
            if agent_id == removed.agent_id:
                continue
            if agent_id in subset_outcomes and subset_outcomes[agent_id] != outcome:
                flips.append(
                    CoalitionFlip(
                        coalition=[a.agent_id for a in agents],
                        removed_agent=removed.agent_id,
                        baseline_outcome=f"{agent_id}:{outcome}",
                        flipped_outcome=f"{agent_id}:{subset_outcomes[agent_id]}",
                    )
                )
                break

    return flips


def settlement_id(agents: list[AgentIntent], allocations: list[AllocationResult]) -> str:
    payload = "|".join(
        f"{a.agent_id}:{a.outcome}:{a.slot}" for a in sorted(allocations, key=lambda x: x.agent_id)
    )
    commitments = "|".join(sorted(a.commitment_hash() for a in agents))
    digest = hashlib.sha256(f"{payload}::{commitments}".encode()).hexdigest()
    return f"settle-{digest[:12]}"


def run_scenario(name: str, agents: list[AgentIntent], capacity: int) -> ScenarioResult:
    initial_stress, _ = compute_stress_index(agents, capacity)
    stabilized, rounds = stability_protocol(agents, initial_stress, capacity)
    final_stress, _ = compute_stress_index(stabilized, capacity)
    allocations = allocate_fair(stabilized, capacity)
    unstable = detect_unstable_coalitions(stabilized, capacity)
    settle = settlement_id(stabilized, allocations)

    return ScenarioResult(
        name=name,
        capacity=capacity,
        agents=stabilized,
        stress_bps=final_stress,
        stress_state=stress_state(final_stress),
        stability_rounds=rounds,
        unstable_coalitions=unstable,
        allocations=allocations,
        settlement_id=settle,
    )



