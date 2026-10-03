# Blind protocol (mandatory)

## Visible
- `prompts/<task>.txt` — **prompt text only**
- `prompt_index.json` — task_id → prompt file mapping only

## Invisible (never open)
- `sealed/**` (test, entry_point, difficulty_scale, canonical_solution)
- `dataset/dataset_qiskit_test_human_eval*.json`
- previous `outputs/agent_self_solve_local_hard/**` (contaminated: tests were visible)

## Feedback
Run:
```bash
/root/anaconda3/envs/qhe/bin/python outputs/agent_blind_solve_local_hard/eval_blind.py \
  --task-id qiskitHumanEval/N \
  --completion outputs/agent_blind_solve_local_hard/attempts/qiskitHumanEval_N/attempt_k.py \
  --out outputs/agent_blind_solve_local_hard/attempts/qiskitHumanEval_N/attempt_k_result.json
```
Result JSON fields allowed: `task_id`, `passed`, `error`.

## Attempts
Max **3** per task. After 3 failures, stop that task.
