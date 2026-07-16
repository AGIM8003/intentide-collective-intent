"""INTENTIDE public types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import AgentIntent, AllocationResult, CoalitionFlip, ScenarioResult


@dataclass
class SettlementResult:
    capacity: int
    stress_bps: int
    stress_state: str
    allocations: list[AllocationResult]
    settlement_id: str
    stability_rounds: list[dict[str, Any]]
    unstable_coalitions: list[CoalitionFlip]
    agents: list[AgentIntent] = field(default_factory=list)
