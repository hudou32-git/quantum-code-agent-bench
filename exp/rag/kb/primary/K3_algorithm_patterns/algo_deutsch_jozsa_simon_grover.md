# Deutsch–Jozsa / Simon / Grover (bundle)

```text
card_id: k3_dj_simon_grover
framework: qiskit
knowledge_layer: K3
common_set_map: algo_04 (DJ); algo_06 (Grover); Simon=supporting (not in 12-topic freeze)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_dj;qiskit_tb_simon;qiskit_tb_grover;qiskit_algo_tut_06_grover;qiskit_docs_grovers;qiskit_lib_grover_op_241
```

## Algorithm Goal

Reference the shared interference structure of DJ, Simon, and Grover-type oracles.

## Quantum Principle

Oracles mark structure in phase/bit space; Hadamards and diffusers convert that structure into measurable outcomes.

## Circuit Structure

**DJ:** H on data + |−⟩ ancilla → oracle → H on data → measure (constant vs balanced).  
**Simon:** prepare / query / measure linear equations for the hidden period.  
**Grover:** even superposition → repeat (phase oracle + diffuser) ≈ π/4 √(N/M) times → measure.

## Required Operations

H, oracle unitary, multi-controlled Z / diffuser (`mcx`/`MCMTGate`), measure; optional `grover_operator`.

## Framework Mapping (Qiskit)

- Textbook: hand-built diffuser (`H/X` sandwich + multi-controlled Z via `mct`/`mcx`) and CZ oracles.
- Algorithm Tutorials (`qiskit-algorithms`): `AmplificationProblem` + `Grover` with a Sampler primitive.
- IBM Quantum docs tutorial: `grover_oracle` + `circuit.library.grover_operator` + compose/`power` iterations (2.4.1-friendly).

## Common Semantic Pitfalls

- Classical if/else standing in for a unitary oracle.
- Diffuser on the wrong qubit subset.
- Marked-string endianness (`target[::-1]` in the docs tutorial).
- Missing ancilla uncompute after marking.

## Minimal Generic Fragment

```python
# Grover skeleton aligned with IBM Quantum docs tutorial
# (docs/tutorials/grovers-algorithm.ipynb) + circuit.library for Qiskit 2.4.1.
from qiskit import QuantumCircuit
from qiskit.circuit.library import grover_operator, MCMTGate, ZGate


def phase_oracle_marked(bitstring: str) -> QuantumCircuit:
    """Mark one computational basis string with a relative phase −1."""
    n = len(bitstring)
    qc = QuantumCircuit(n)
    rev = bitstring[::-1]  # Qiskit little-endian wiring
    zeros = [i for i, b in enumerate(rev) if b == "0"]
    if zeros:
        qc.x(zeros)
    qc.compose(MCMTGate(ZGate(), n - 1, 1), inplace=True)
    if zeros:
        qc.x(zeros)
    return qc


oracle = phase_oracle_marked("11")
grover_op = grover_operator(oracle)
qc = QuantumCircuit(oracle.num_qubits)
qc.h(range(qc.num_qubits))
qc.compose(grover_op, inplace=True)  # one Grover iteration; repeat as needed
qc.measure_all()
```

```python
# Textbook-style diffuser pattern (Grover chapter); prefer mcx on 2.4.1.
from qiskit import QuantumCircuit


def diffuser(nqubits: int):
    qc = QuantumCircuit(nqubits)
    qc.h(range(nqubits))
    qc.x(range(nqubits))
    qc.h(nqubits - 1)
    qc.mcx(list(range(nqubits - 1)), nqubits - 1)
    qc.h(nqubits - 1)
    qc.x(range(nqubits))
    qc.h(range(nqubits))
    return qc.to_gate(label="Us")
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_dj` | Textbook *Deutsch-Jozsa Algorithm* |
| `qiskit_tb_simon` | Textbook *Simon's Algorithm* (supporting) |
| `qiskit_tb_grover` | Textbook *Grover's Algorithm* (diffuser / oracles) |
| `qiskit_algo_tut_06_grover` | Qiskit Algorithm Tutorials `06_grover.ipynb` |
| `qiskit_docs_grovers` | IBM Quantum documentation / Learning-aligned Grover tutorial |
| `qiskit_lib_grover_op_241` | Qiskit 2.4.1 `grover_operator` |

Excerpts: `excerpt_docs_grovers_oracle_compose.py`, `excerpt_textbook_grover_diffuser.py`, `excerpt_algorithms_06_grover_amplification.py`.  
Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
