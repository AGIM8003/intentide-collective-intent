# Reproducibility Guide — INTENTIDE

## Requirements
- Python 3.10+ (tested on 3.14.4)
- No external dependencies (stdlib only)

## Verify the Core Mechanism
```bash
python intentide_poc.py
python intentide_gate.py
python intentide_benchmark.py
python intentide_alt_impl.py
python intentide_mutation_test.py
```

## Expected Output (last lines)
- `intentide_poc.py`: `INTENTIDE PoC complete.`
- `intentide_gate.py`: `GATE VERDICT: PASS`
- `intentide_benchmark.py`: `Correctness rate    : 100.0% (10/10)`
- `intentide_alt_impl.py`: `Agree with iterative ref: True; differs from FCFS: True`
- `intentide_mutation_test.py`: `Mutation score: 90%` or higher

## Verification Time
All scripts complete in under 5 seconds on a standard machine (fairness sample included).

## Evidence Files Generated
| File | Contents |
|------|----------|
| `intentide_evidence.json` | Settlement + stress evidence |
| `intentide_gate_results.json` | Gate + defenses |
| `intentide_benchmark_results.json` | Benchmarks + scalability |
| `intentide_replication_evidence.json` | LP-style vs iterative agreement |
| `intentide_mutation_results.json` | Mutation detections |

## Author
Agim Haxhijaha · ORCID 0009-0002-3234-7765 · Independent Researcher

## REALITY_FORGE additions (v1.2.0)

```bash
python intentide_realworld.py
python intentide_stress.py
```

Expect EXIT 0 and JSON evidence/results beside the scripts. Deploy reference: `intentide_deploy_manifest.json`.

## INVENTION_CRYSTALLIZATION (v1.3.0)

```bash
from intentide import INTENTIDEEngine
python intentide_quickstart.py
python intentide_integration_test.py
```
