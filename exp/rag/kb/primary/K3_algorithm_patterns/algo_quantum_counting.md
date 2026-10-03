# Quantum counting

```text
card_id: k3_quantum_counting
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_counting
```

## Algorithm Goal

Estimate the number of Grover solutions M via phase estimation on the Grover iterate.

## Quantum Principle

Eigenphases of the Grover operator encode arcsin(√(M/N)); QPE recovers that angle.

## Circuit Structure

Counting register controls powers of a Grover iteration gate; IQFT on counting register; convert measured phase → M.

## Required Operations

Controlled Grover iterate, IQFT, measure; classical decoding.

## Framework Mapping (Qiskit)

Textbook *Quantum Counting*: build Grover gate, `.control()`, append with doubling repetitions, then IQFT.

## Common Semantic Pitfalls

- Controlling the wrong qubits on the Grover block.
- Off-by-one in iteration schedule 1,2,4,...
- Mis-converting phase to M.

## Minimal Generic Fragment

```python
# Shape from Textbook Quantum Counting.
from qiskit import QuantumCircuit
# grit = grover_iteration_circuit.to_gate(); cgrit = grit.control()
t, n = 4, 4
qc = QuantumCircuit(n + t, t)
qc.h(range(n + t))
iters = 1
for q in range(t):
    for _ in range(iters):
        pass  # qc.append(cgrit, [q] + list(range(t, n+t)))
    iters *= 2
# qc.append(iqft_gate, range(t)); qc.measure(range(t), range(t))
```

## Sources

| `qiskit_tb_counting` | Textbook *Quantum Counting* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
