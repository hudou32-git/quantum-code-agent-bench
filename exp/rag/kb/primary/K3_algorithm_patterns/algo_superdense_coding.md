# Superdense coding

```text
card_id: k3_superdense_coding
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_superdense;qiskit_tb_entangled
```

## Algorithm Goal

Send two classical bits by transmitting one qubit of a shared Bell pair.

## Quantum Principle

Local Pauli on Alice’s half selects which Bell state Bob will decode with CX+H.

## Circuit Structure

Shared Bell pair; Alice encodes message with I/X/Z/XZ; Bob CX+H and measures both qubits.

## Required Operations

H, CX, X/Z encode, measure.

## Framework Mapping (Qiskit)

Textbook *Superdense Coding*: `create_bell_pair`, message encode, `decode_message` (CX then H).

## Common Semantic Pitfalls

Encoding on the wrong qubit; decoding without the matching Bell partner.

## Minimal Generic Fragment

```python
# From Textbook Superdense Coding helpers.
from qiskit import QuantumCircuit

def create_bell_pair():
    qc = QuantumCircuit(2)
    qc.h(1)
    qc.cx(1, 0)
    return qc

def decode_message(qc):
    qc.cx(1, 0)
    qc.h(1)
    return qc
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_superdense` | Textbook *Superdense Coding* |
| `qiskit_tb_entangled` | Bell pair motif |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
