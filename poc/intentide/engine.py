"""INTENTIDEEngine — usable research library API. Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

from .core import (
    AgentIntent,
    allocate_fair,
    compute_stress_index,
    detect_unstable_coalitions,
    run_scenario,
    settlement_id,
    stability_protocol,
    stress_state,
)
from .types import SettlementResult
from .validators import require_agent_id, require_capacity


class INTENTIDEEngine:
    """Collective intent stability for scarce capacity allocation.

    Usage:
        engine = INTENTIDEEngine(capacity=3)
        engine.add_agent("alpha", resource_class="cold", quantity=1, arrival_order=1)
        result = engine.settle()
    """

    def __init__(self, capacity: int = 3) -> None:
        self.capacity = require_capacity(capacity)
        self._agents: list[AgentIntent] = []

    def set_capacity(self, capacity: int) -> None:
        self.capacity = require_capacity(capacity)

    def add_agent(
        self,
        agent_id: str,
        *,
        resource_class: str = "default",
        quantity: int = 1,
        arrival_order: int = 0,
        stability_weight: float = 1.0,
    ) -> None:
        agent_id = require_agent_id(agent_id)
        if any(a.agent_id == agent_id for a in self._agents):
            raise ValueError(f"duplicate agent: {agent_id}")
        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        self._agents.append(
            AgentIntent(
                agent_id=agent_id,
                resource_class=resource_class,
                quantity=quantity,
                arrival_order=arrival_order,
                stability_weight=stability_weight,
            )
        )

    def stress_index(self) -> tuple[int, dict]:
        return compute_stress_index(self._agents, self.capacity)

    def run_stability(self) -> tuple[list[AgentIntent], list[dict]]:
        bps, _ = self.stress_index()
        return stability_protocol(self._agents, bps, self.capacity)

    def allocate(self) -> list:
        return allocate_fair(self._agents, self.capacity)

    def coalition_violations(self) -> list:
        return detect_unstable_coalitions(self._agents, self.capacity)

    def settle(self, name: str = "settlement") -> SettlementResult:
        if not self._agents:
            return SettlementResult(
                capacity=self.capacity,
                stress_bps=0,
                stress_state="NORMAL",
                allocations=[],
                settlement_id="settle-empty",
                stability_rounds=[],
                unstable_coalitions=[],
                agents=[],
            )
        scen = run_scenario(name, self._agents, self.capacity)
        return SettlementResult(
            capacity=scen.capacity,
            stress_bps=scen.stress_bps,
            stress_state=scen.stress_state,
            allocations=scen.allocations,
            settlement_id=scen.settlement_id,
            stability_rounds=scen.stability_rounds,
            unstable_coalitions=scen.unstable_coalitions,
            agents=scen.agents,
        )
