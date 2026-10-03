# HHL linear-systems algorithm (sketch)

```text
card_id: k3_hhl
framework: qiskit
knowledge_layer: K3
common_set_map: extended_algorithm
benchmark_derived: false
version: 2.4.1
public_release_status: primary_candidate
source_ids: qiskit_tb_app_hhl
```

## Algorithm Goal

Solve A|x⟩=|b⟩ in amplitude encoding (Harrow–Hassidim–Lloyd), for suitable A.

## Quantum Principle

Phase estimation on e^{iAt} extracts eigenvalues; controlled rotations invert them; uncompute.

## Circuit Structure

State prep |b⟩; QPE of Hamiltonian simulation; eigenvalue inversion rotations; inverse QPE; read |x⟩ amplitudes.

## Required Operations

Hamiltonian simulation / controlled unitaries, QPE, controlled Ry rotations, uncompute.

## Framework Mapping (Qiskit)

Textbook applications *HHL tutorial* — treat as advanced pattern; prefer library/research stacks carefully under 2.4.1.

## Common Semantic Pitfalls

Ill-conditioned A; ignoring normalization of |x⟩; treating HHL as a black-box classical solver.

## Minimal Generic Fragment

```python
# Conceptual HHL pipeline (Textbook HHL tutorial) — not a full solver.
# prepare_|b> -> QPE(e^{iAt}) -> controlled_rotation(1/lambda) -> inverse_QPE
```

## Sources

| `qiskit_tb_app_hhl` | Textbook applications *HHL tutorial* |


## Non-goals

- No benchmark `task_id`, graded entrypoint names, or hidden-test contracts.
- No copy-paste submitable solutions for a specific evaluated function signature.
