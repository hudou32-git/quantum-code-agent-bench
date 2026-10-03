# Phase oracle / relative phase marking

```text
card_id: k3_phase_oracle
framework: qiskit
knowledge_layer: K3
common_set_map: supports algo_06 (Grover) / general oracle patterns
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_oracles;qiskit_tb_phase_kickback;qiskit_tb_grover;qiskit_docs_grovers;qiskit_lib_phase_oracle_241;qiskit_lib_grover_op_241
```

## Algorithm Goal

Apply a relative minus phase to target basis state(s): |t⟩ → −|t⟩.

## Quantum Principle

Interference experiments detect relative phase; global phase alone is unobservable. Phase kickback through an ancilla in |−⟩ is the usual mechanism for bit oracles.

## Circuit Structure

Multi-controlled Z on a matched bit pattern (X wrappers on open controls), or phase kickback through an ancilla in |−⟩.

## Required Operations

X, multi-controlled Z / CZ / `MCMTGate(ZGate(), ...)`, H on ancilla for kickback.

## Framework Mapping (Qiskit)

- Textbook Grover: CZ / multi-controlled phase with X wrappers.
- Docs Learning-aligned tutorial: `MCMTGate(ZGate(), n-1, 1)` after endian flip of the marked string.
- 2.4.1 library: `qiskit.circuit.library.phase_oracle` helpers and `grover_operator(oracle)`.

## Common Semantic Pitfalls

- Flipping support (X) instead of phase.
- Only global phase.
- Correct probabilities but wrong interference (classic semantic residual).

## Minimal Generic Fragment

```python
# Phase-mark one bitstring (docs Grover tutorial pattern), Qiskit 2.4.1 APIs.
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCMTGate, ZGate


def phase_mark(bitstring: str) -> QuantumCircuit:
    n = len(bitstring)
    qc = QuantumCircuit(n)
    rev = bitstring[::-1]
    zeros = [i for i, b in enumerate(rev) if b == "0"]
    if zeros:
        qc.x(zeros)
    qc.compose(MCMTGate(ZGate(), n - 1, 1), inplace=True)
    if zeros:
        qc.x(zeros)
    return qc
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_oracles` | Textbook oracles chapter |
| `qiskit_tb_phase_kickback` | Textbook phase kickback |
| `qiskit_tb_grover` | Textbook Grover marking examples |
| `qiskit_docs_grovers` | Docs / Learning-aligned multi-controlled Z oracle |
| `qiskit_lib_phase_oracle_241` | Qiskit 2.4.1 `phase_oracle` module |
| `qiskit_lib_grover_op_241` | Qiskit 2.4.1 `grover_operator` |

Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
