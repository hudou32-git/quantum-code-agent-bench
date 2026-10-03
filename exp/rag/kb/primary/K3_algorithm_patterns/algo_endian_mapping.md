# Endianness and bit mapping

```text
card_id: k3_endian
framework: qiskit
knowledge_layer: K3
common_set_map: cross-cutting support (not a numbered freeze topic)
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_bv;qiskit_tb_qft;qiskit_docs_grovers
```

## Algorithm Goal

Map textbook MSB-left bitstrings onto Qiskit’s little-endian qubit indices.

## Quantum Principle

Index bit 0 ↔ qubit 0 in Qiskit Statevector / counts conventions.

## Circuit Structure

Translate string indices; implement reversals with SWAP(i, n-1-i) when a bit-reversal is truly required (e.g. Textbook QFT `swap_registers`).

## Required Operations

SWAP / CX networks for reversals; careful oracle wiring.

## Framework Mapping (Qiskit)

Official materials reverse classical strings before wiring:

- Textbook BV: `s = s[::-1]  # reverse s to fit qiskit's qubit ordering`
- Docs Grover tutorial: `rev_target = target[::-1]` before open-control X masks

When reading counts keys or Statevector integers, treat qubit 0 as LSB.

## Common Semantic Pitfalls

- Reversing only printed classical strings.
- Off-by-one in SWAP pairs.
- Mixing big-endian oracle wiring with little-endian prep.

## Minimal Generic Fragment

```python
# Endian helpers as used in official BV / Grover materials.
s_textbook = "011"          # MSB-left classical label
s_qubits = s_textbook[::-1] # index 0 -> qubit 0

# QFT-style bit-reversal swaps (Textbook QFT swap_registers):
# for i in range(n // 2):
#     qc.swap(i, n - 1 - i)
```

## Sources

| source_id | role |
|-----------|------|
| `qiskit_tb_bv` | Explicit `s[::-1]` endian note |
| `qiskit_tb_qft` | `swap_registers` bit-reversal |
| `qiskit_docs_grovers` | `target[::-1]` in Grover oracle builder |

Manifest: `manifests/qiskit_k3_source_list.csv`.

## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
