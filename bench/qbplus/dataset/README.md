# QuanBench+ — Qiskit subset

Migrated for Oracle closed-loop experiments under `four_benchmarks/`.

| Field | Value |
|------|------:|
| Tasks | **42** |
| Framework | Qiskit |
| Categories | QUANTUM_ALGO / STATE_PREPARATION / DECOMPOSITION |
| Native accept | KL divergence vs `canonical_output` |
| Conda env (suggested) | `quanbench` |

## Layout

```text
prompts/qiskit.jsonl          # official QuanBench+ Qiskit prompts (+ canonical_solution)
prompts/per_task/XX.txt       # one prompt file per task
canonical_results/            # expected probability vectors
sealed/problems_full.json     # unified sealed records (do not feed to model)
eval/                         # snapshot of quanbench-plus qiskit grading code
SOURCE.json                   # provenance
```

## Grading note

- **Authoritative**: execute generated Qiskit function → measurement probs → `get_kl_div` vs sealed `canonical_output`.
- Sealed `test` strings (when present) are copied from QuanBench117 for the same `task_id` and are optional / secondary.
- Prefer running via the original package at repo root `quanbench-plus/` when integrating runners; `eval/` is a frozen snapshot.

## Why this suite (vs QHE local_hard)

QuanBench+ Qiskit tasks are predominantly **circuit construction** with distributional (KL) oracles,
so failure mass is expected to shift toward **L2 structural / L3.3 distributional** rather than
broad SDK surface-API mistakes that dominate QHE local_hard UNRESOLVED/L2.1 tails.
