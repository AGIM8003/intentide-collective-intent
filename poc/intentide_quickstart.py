#!/usr/bin/env python3
"""INTENTIDE Quickstart — fair scarce-capacity settlement in ~25 lines."""
from intentide import INTENTIDEEngine

engine = INTENTIDEEngine(capacity=3)
engine.add_agent("pharma_carrier", resource_class="PHARMA_2_8C", quantity=1, arrival_order=5, stability_weight=1.3)
engine.add_agent("seafood_early", resource_class="SEAFOOD", quantity=1, arrival_order=1, stability_weight=0.9)
engine.add_agent("produce_burst", resource_class="PRODUCE", quantity=1, arrival_order=2, stability_weight=0.85)
engine.add_agent("hazmat_late", resource_class="CHEM", quantity=1, arrival_order=8, stability_weight=1.1)
engine.add_agent("retail_retry", resource_class="PRODUCE", quantity=1, arrival_order=20, stability_weight=0.8)

result = engine.settle("port_cold_storage_demo")
print(f"Stress: {result.stress_bps} bps ({result.stress_state})")
print(f"Settlement: {result.settlement_id}")
for alloc in result.allocations:
    print(f"  {alloc.agent_id}: {alloc.outcome} slot={alloc.slot}")
