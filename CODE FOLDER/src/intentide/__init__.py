"""INTENTIDE — Collective Intent Stability (research library)."""
from .core import (
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
from .engine import INTENTIDEEngine
from .types import SettlementResult

__all__ = [
    "INTENTIDEEngine",
    "SettlementResult",
    "AgentIntent",
    "AllocationResult",
    "CoalitionFlip",
    "ScenarioResult",
    "compute_stress_index",
    "stability_protocol",
    "allocate_fair",
    "detect_unstable_coalitions",
    "settlement_id",
    "run_scenario",
    "stress_state",
]
__version__ = "1.3.0"
