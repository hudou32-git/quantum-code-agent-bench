# Quantum Phase Estimation (QPE / IQPE)

```text
card_id: k3_phase_estimation
framework: qiskit
knowledge_layer: K3
common_set_map: algo_08
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_qpe;qiskit_docs_qpe;qiskit_lib_qft_241
```

## Algorithm Goal

Estimate eigenphase φ of a unitary U for an eigenstate |u⟩ (QPE), (iterative variants exist; prefer current docs/Textbook QPE patterns under 2.4.1).

## Quantum Principle

Controlled-U^(2^k) writes phase into a counting register; inverse QFT reads φ as a bitstring.

## Circuit Structure

1. Counting register H⊗t; eigenstate prepared on target.
2. For k=0..t-1: controlled-U^(2^k) from counting qubit k onto target.
3. Apply IQFT on counting register; measure counting bits.
IQPE replaces the full IQFT with sequential single-qubit measurements and classical phase corrections.

## Required Operations

H, controlled-phase / controlled-U powers, IQFT (or iterative P corrections), measure.

## Framework Mapping (Qiskit)

Textbook QPE builds `cp` powers then `qft_dagger`. 2.4.1: `circuit.library.QFT(...).inverse()` for IQFT; docs also ship QPE tutorials.

## Common Semantic Pitfalls

- Missing or wrong U^(2^k) repetition schedule.
- Forgetting IQFT swaps / endianness of the phase bitstring.
- Target not an (approximate) eigenstate → smeared peaks.

## Minimal Generic Fragment

```python
# Skeleton from Qiskit Textbook QPE (counting H, controlled-U powers, IQFT).
import math
from qiskit import QuantumCircuit

qpe = QuantumCircuit(4, 3)  # 3 counting + 1 eigenqubit
qpe.x(3)  # |u> example
for qubit in range(3):
    qpe.h(qubit)
reps = 1
for cq in range(3):
    for _ in range(reps):
        qpe.cp(math.pi / 4, cq, 3)  # placeholder CU
    reps *= 2
# then IQFT on counting qubits + measure (Textbook qft_dagger / library QFT.inverse())
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_qpe` | Textbook *Quantum Phase Estimation* |
| `qiskit_docs_qpe` | IBM Quantum docs QPE tutorial |
| `qiskit_lib_qft_241` | 2.4.1 `QFT` for IQFT block |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
