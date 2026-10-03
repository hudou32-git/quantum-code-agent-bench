# Quantum walk search

```text
card_id: k3_quantum_walk_search
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_qwalk
```

## Algorithm Goal

Search marked vertices using a discrete-time quantum walk (coin + shift) instead of plain Grover.

## Quantum Principle

Quantum walk operators interfere amplitudes toward marked nodes on a graph.

## Circuit Structure

Coin space ⊗ position space; alternate coin reflection and conditional shift; mark/phase nodes; iterate; measure position.

## Required Operations

Coin unitaries, controlled shifts / SWAPs, phase marking, measure.

## Framework Mapping (Qiskit)

Textbook *Quantum Walk Search Algorithm* — build walk step as a reusable gate and iterate.

## Common Semantic Pitfalls

Wrong coin dimension vs graph degree; marking position without coin cleanup.

## Minimal Generic Fragment

```python
# High-level walk-search loop (Textbook Quantum Walk Search).
from qiskit import QuantumCircuit
# walk_step = (coin + shift + mark).to_gate()
# qc = QuantumCircuit(coin_qubits + position_qubits)
# for _ in range(num_steps): qc.append(walk_step, all_qubits)
# qc.measure(position_qubits, creg)
```

## Sources

| `qiskit_tb_qwalk` | Textbook *Quantum Walk Search Algorithm* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
