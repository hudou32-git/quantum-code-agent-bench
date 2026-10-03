# Simon's algorithm

```text
card_id: k3_simon
framework: qiskit
knowledge_layer: K3
common_set_map: supporting (related to algo_04 family; not numbered freeze id)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_simon
```

## Algorithm Goal

Find hidden period bitstring b such that f(x)=f(y) iff x⊕y∈{0,b}.

## Quantum Principle

Oracle + Hadamards produce linear equations y·b=0; repeat and solve classically.

## Circuit Structure

H on input; oracle to second register; H on input; measure input; classical linear algebra over GF(2).

## Required Operations

H, oracle CX network for secret b, measure.

## Framework Mapping (Qiskit)

Textbook *Simon's Algorithm*; also summarized in the DJ/Simon/Grover bundle card.

## Common Semantic Pitfalls

Insufficient linearly independent y samples; endianness of b.

## Minimal Generic Fragment

```python
from qiskit import QuantumCircuit
n = 2
qc = QuantumCircuit(2 * n, n)
qc.h(range(n))
# qc.compose(simon_oracle, inplace=True)
qc.h(range(n))
qc.measure(range(n), range(n))
```

## Sources

| `qiskit_tb_simon` | Textbook *Simon's Algorithm* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
