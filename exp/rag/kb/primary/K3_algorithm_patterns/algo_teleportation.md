# Quantum Teleportation

```text
card_id: k3_teleportation
framework: qiskit
knowledge_layer: K3
common_set_map: algo_03
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_teleport
```

## Algorithm Goal

Transfer an unknown qubit state from Alice to Bob using a shared Bell pair and two classical bits.

## Quantum Principle

Entanglement + mid-circuit measurement + conditional Pauli corrections reconstruct |ψ⟩ on Bob’s qubit.

## Circuit Structure

1. Create Bell pair on (a,b): H(a), CX(a,b).
2. Alice: CX(ψ,a), H(ψ); measure ψ and a → classical bits.
3. Bob: apply X/Z conditioned on those bits (Textbook `c_if`; Qiskit 2.x prefers `if_test` / dynamic circuits).

## Required Operations

H, CX, measure, conditional X/Z (or deferred CX/CZ before measure in the deferred-measurement form).

## Framework Mapping (Qiskit)

Textbook helpers `create_bell_pair` / `alice_gates` / `bob_gates` use `.c_if`. On **2.4.1**, prefer `with qc.if_test((cr, 1)): qc.x(...)` or the deferred CX/CZ form (`new_bob_gates`) which avoids classical feedforward.

## Common Semantic Pitfalls

- Wrong Bell-pair wiring (control/target).
- Applying Bob’s corrections on the wrong qubit.
- Using obsolete `c_if` without a 2.x dynamic-circuit alternative when the runtime requires it.

## Minimal Generic Fragment

```python
# Pattern from Qiskit Textbook teleportation chapter (create_bell_pair / alice_gates).
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

def create_bell_pair(qc, a, b):
    qc.h(a)
    qc.cx(a, b)

def alice_gates(qc, psi, a):
    qc.cx(psi, a)
    qc.h(psi)

qr = QuantumRegister(3, "q")
crz, crx = ClassicalRegister(1, "crz"), ClassicalRegister(1, "crx")
qc = QuantumCircuit(qr, crz, crx)
create_bell_pair(qc, 1, 2)
alice_gates(qc, 0, 1)
qc.measure(0, crz)
qc.measure(1, crx)
# Bob corrections (2.4.1): prefer if_test / deferred CX+CZ over legacy c_if
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_teleport` | Textbook *Quantum Teleportation* |

Manifest: `manifests/qiskit_k3_source_list.csv`.


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
