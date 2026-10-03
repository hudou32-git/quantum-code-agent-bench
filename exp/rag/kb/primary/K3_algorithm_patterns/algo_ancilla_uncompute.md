# Ancilla hygiene / uncomputation

```text
card_id: k3_ancilla_uncompute
framework: qiskit
knowledge_layer: K3
common_set_map: cross-cutting support (not a numbered freeze topic)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_oracles;qiskit_tb_phase_kickback
```

## Algorithm Goal

Return workspace qubits to a clean state after use.

## Quantum Principle

Garbage entanglement between data and ancilla corrupts later interference even if marginal data looks plausible. Textbook oracle / phase-kickback chapters treat ancillas as reversible workspace.

## Circuit Structure

Compute → use ancilla → **uncompute** with the inverse of the compute block.

## Required Operations

Unitary compute/uncompute pair; avoid premature reset/measure when coherence is required.

## Framework Mapping (Qiskit)

`compose(compute)`, controls, then `compose(compute.inverse())` (when unitary). Matches reversible-oracle discipline in Textbook oracles / kickback material.

## Common Semantic Pitfalls

- Leaving entangled garbage.
- Resetting instead of unitary uncompute.
- Wrong ancilla count vs the intended scratch space.

## Minimal Generic Fragment

```python
# Bennett-style uncompute (oracle/ancilla hygiene pattern).
# qc.compose(compute)
# ... use ancilla ...
# qc.compose(compute.inverse())
from qiskit import QuantumCircuit

compute = QuantumCircuit(2)
compute.cx(0, 1)  # placeholder scratch write

qc = QuantumCircuit(2)
qc.compose(compute, inplace=True)
# ... interfere / controlled ops using qubit 1 ...
qc.compose(compute.inverse(), inplace=True)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_oracles` | Textbook oracle / reversible classical computation |
| `qiskit_tb_phase_kickback` | Ancilla |−⟩ / kickback discipline |

Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
