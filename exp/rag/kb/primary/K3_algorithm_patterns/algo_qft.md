# Quantum Fourier Transform

```text
card_id: k3_qft
framework: qiskit
knowledge_layer: K3
common_set_map: algo_07 (QFT / IQFT)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_qft;qiskit_lib_qft_241;qiskit_docs_qft_dyn
```

## Algorithm Goal

Implement the QFT unitary on n qubits (IQFT = inverse).

## Quantum Principle

QFT maps computational basis states to phase-gradient superpositions used in period finding and PEA.

## Circuit Structure

For the textbook recursive construction (MSB-first recursion): H on qubit `n-1`; controlled-phase `cp(π/2^(n-q), q, n-1)` for `q < n-1`; recurse on `n-1`; optional terminal SWAPs for bit-reversed ordering. IQFT is the inverse of that circuit.

## Required Operations

H, controlled-phase (`cp`), optional SWAP; inverse gate order / `.inverse()` for IQFT.

## Framework Mapping (Qiskit)

- Pattern source: Textbook recursive `qft_rotations` + `swap_registers`.
- Qiskit **2.4.1** library API: `from qiskit.circuit.library import QFT` / `QFTGate` with `do_swaps` to match endian convention.
- Confirm whether the desired convention includes final SWAPs (library `do_swaps=True/False`).

## Common Semantic Pitfalls

- Wrong rotation angles (π/2^k).
- Extra/missing SWAPs failing unitary checks.
- Reversed qubit iteration order vs the intended MSB/LSB convention.

## Minimal Generic Fragment

```python
# Pattern from Qiskit Textbook QFT chapter (recursive H/cp + optional swaps),
# written for Qiskit 2.4.1 circuit APIs. Prefer circuit.library.QFT for production.
from numpy import pi
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT


def qft_rotations(circuit: QuantumCircuit, n: int) -> None:
    if n == 0:
        return
    n -= 1
    circuit.h(n)
    for qubit in range(n):
        circuit.cp(pi / 2 ** (n - qubit), qubit, n)
    qft_rotations(circuit, n)


def qft_with_swaps(circuit: QuantumCircuit, n: int) -> QuantumCircuit:
    qft_rotations(circuit, n)
    for qubit in range(n // 2):
        circuit.swap(qubit, n - qubit - 1)
    return circuit


# Library equivalent (2.4.1):
# qc = QuantumCircuit(4); qc.compose(QFT(4, do_swaps=True), inplace=True)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_qft` | Qiskit Textbook (OSS) *Quantum Fourier Transform* — recursive definition |
| `qiskit_lib_qft_241` | Qiskit 2.4.1 `circuit.library` `QFT` / `QFTGate` |
| `qiskit_docs_qft_dyn` | IBM Quantum docs tutorial (QFT + dynamic circuits) |

Provenance excerpts: `qiskit/sources/k3_official_excerpts/excerpt_textbook_qft_defs.py`, `excerpt_qiskit_241_circuit_library_pointers.md`.  
Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
