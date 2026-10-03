"""Zero-API selftests for the ablation harness (freeze plan §21 items testable offline).

Run: python3 -m exp.eqpa.isoabl.selftest
Exit 0 = all gates pass. No LLM calls; no formal-data writes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from exp.eqpa.isoabl import gateway
from exp.eqpa.isoabl.arms import ARM_NAMES, ARM_TOOLS, FROZEN_BUDGETS, MANIFEST_LINE

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{tag}] {name}" + (f" — {detail}" if detail and not ok else ""), flush=True)


def test_arm_toolsets() -> None:
    check("B has no Shell tool", all(t["function"]["name"] != "Shell" for t in ARM_TOOLS["B"]))
    check("C has no Eval tool", all(t["function"]["name"] != "Eval" for t in ARM_TOOLS["C"]))
    for arm in ARM_NAMES:
        names = {t["function"]["name"] for t in ARM_TOOLS[arm]}
        check(f"{arm} has Write+Submit", {"Write", "Submit"} <= names)
        check(f"{arm} manifest line", MANIFEST_LINE[arm] == MANIFEST_LINE[arm])


def test_gateway_B() -> None:
    calls = []

    def fake_shell(cmd, session=None):
        calls.append(cmd)
        return {"ok": True, "text": " leaked output ", "capability_block": False}

    out = gateway.gateway_shell("cat /workspace/prompt.txt", arm="B", entry_point="f", run_shell_fn=fake_shell, session=None)
    check("B: Shell blocked without execution", out.get("capability_block") is True and not calls)
    check("B: blocked reply names INSPECT=0", "INSPECT=0" in (out.get("text") or ""))


def test_gateway_C() -> None:
    calls = []

    def fake_shell(cmd, session=None):
        calls.append(cmd)
        return {"ok": True, "text": "qiskit 1.2.4", "capability_block": False}

    allowed = [
        "python3 -c \"import qiskit; print(qiskit.__version__)\"",
        "cat /workspace/prompt.txt",
        "ls /tmp",
        "python3 -c \"import qiskit.circuit; print(dir(qiskit.circuit))\"",
        "grep -c def /workspace/prompt.txt",
    ]
    for cmd in allowed:
        out = gateway.gateway_shell(cmd, arm="C", entry_point="my_func", run_shell_fn=fake_shell, session=None)
        check(f"C allows inspect: {cmd[:44]}", out.get("capability_block") is False)

    blocked = [
        ("python3 /workspace/attempt_1.py", "executes attempt file"),
        ("cd /workspace && python attempt_2.py", "executes attempt file"),
        ("python3 -c \"import attempt_1\"", "imports attempt file"),
        ("pytest -q", "test runner"),
        ("python3 -m unittest discover", "test runner"),
        ("python3 -c \"from qiskit import *; import my_func; print(my_func([1,0]))\"", "entry-point probe"),
        ("python3 -c \"import my_func as f; print(f('01'))\"", "entry-point probe"),
    ]
    for cmd, why in blocked:
        out = gateway.gateway_shell(cmd, arm="C", entry_point="my_func", run_shell_fn=fake_shell, session=None)
        check(f"C blocks eval-ish: {cmd[:44]} ({why})", out.get("capability_block") is True)
    check("C: no command reached the sandbox for blocked set", len(calls) == len(allowed))


def test_budget_freeze() -> None:
    check("max_model_calls frozen at 36", FROZEN_BUDGETS["max_model_calls"] == 36)
    check("max_eval_calls frozen at 3", FROZEN_BUDGETS["max_eval_calls"] == 3)
    check("B inspect cap is 0 via manifest not budget", MANIFEST_LINE["B"].startswith("INSPECT=0"))
    check("forced submit on", FROZEN_BUDGETS["forced_submit_at_budget"] is True)


def test_terminal_grading_isolation() -> None:
    """_grade_offline must not touch the episode session/jail (offline evaluator)."""
    import inspect as _inspect

    from exp.eqpa.isoabl.episode import _grade_offline

    params = list(_inspect.signature(_grade_offline).parameters)
    check("terminal grade takes only (case, code)", params == ["case", "code"])
    body = _inspect.getsource(_grade_offline)
    check("terminal grade body references neither session nor jail",
          "session" not in body and "jail" not in body)


def test_resume_key_uniqueness() -> None:
    from exp.eqpa.isoabl.runner import _done_keys, plan_blocks
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"case_id": "t/1", "arm": "A"}) + "\n")
        p = Path(f.name)
    check("done-key parse", ("t/1", "A") in _done_keys(p))
    p.unlink()
    blocks = plan_blocks(["t/3", "t/1", "t/2"], block_size=2, seed=1)
    ids = [t["task_id"] for b in blocks for t in b["tasks"]]
    check("blocks partition cohort", sorted(ids) == ["t/1", "t/2", "t/3"])
    arms_all = [t["arm_order"] for b in blocks for t in b["tasks"]]
    check("every task has all 4 arms", all(sorted(a) == sorted(ARM_NAMES) for a in arms_all))


def test_episode_end_to_end() -> None:
    """Scripted fake-LLM walkthrough: R reset, C/B blocks, budgets, forced submit, terminal grade."""
    import types

    import exp.eqpa.isoabl.episode as ep

    real_run_shell = ep.run_shell
    real_grade = ep._grade_offline
    ep.run_shell = lambda cmd, session: {"ok": True, "blocked": False, "text": "fake-inspect-output"}
    grade_results = {"bad": {"passed": False, "error_message": "KLMismatch: distribution differs"},
                     "good": {"passed": True, "error_message": ""}}
    ep._grade_offline = lambda case, code: grade_results["good" if "return 1" in code else "bad"]

    class FakeRes:
        def __init__(self, tool_calls):
            self.content = ""
            self.usage = {"completion_tokens": 100}
            self.tool_calls = tool_calls
            self.assistant_message = {"role": "assistant", "content": ""}

    def _tc(name, **args):
        return {"name": name, "arguments": args, "id": f"c{abs(hash((name, str(args)))) % 10 ** 8}"}

    BAD = "def entry(p):\n    return 0\n"
    GOOD = "def entry(p):\n    return 1\n"

    class ScriptClient:
        model = "mock-0731"
        def __init__(self, script):
            self.script = list(script)
            self.seen_lengths = []
        def chat_messages(self, messages, tools=None):
            self.seen_lengths.append(len(messages))
            return FakeRes(self.script.pop(0))

    # --- R arm: mismatch -> conversation reset to [system, user(+latest feedback)] ---
    script = [
        [_tc("Write", path="attempt_1.py", contents=BAD), _tc("Eval")],
        [_tc("Write", path="attempt_2.py", contents=GOOD), _tc("Eval")],
        [_tc("Submit")],
    ]
    cli = ScriptClient(script)
    row = ep.run_ablation_episode("qiskitHumanEval/15", "R", cli, tag="e4_isoabl_SELFTEST")
    check("R: reset happened once on mismatch", row["context_reset_count"] == 1)
    check("R: agent submitted at end", row["agent_submitted"] is True)
    check("R: eval_calls == 2 (both evals counted)", row["eval_calls"] == 2)
    check("R: terminal pass from last good candidate", row["terminal_candidate_pass"] is True)
    check("R: terminal result was agent-visible (no rescore flag)",
          row["terminal_rescore_used"] is False)
    check("R: second context == 2 messages (history wiped)",
          len(cli.seen_lengths) >= 2 and cli.seen_lengths[1] == 2)

    # --- C arm: eval-ish Shell blocked; no Eval; Submit; blocks counted ---
    script = [
        [_tc("Shell", command="python3 /workspace/attempt_1.py"),
         _tc("Shell", command="cat /workspace/prompt.txt"),
         _tc("Write", path="attempt_1.py", contents=GOOD),
         _tc("Submit")],
    ]
    cli = ScriptClient(script)
    row = ep.run_ablation_episode("qiskitHumanEval/15", "C", cli, tag="e4_isoabl_SELFTEST")
    check("C: zero eval calls", row["eval_calls"] == 0)
    check("C: eval-ish shell blocked", row["blocked_capability_attempt_count"] == 1)
    check("C: inspect shell allowed", row["inspect_calls"] == 1)
    check("C: terminal pass", row["terminal_candidate_pass"] is True)

    # --- B arm: any Shell blocked ---
    script = [
        [_tc("Shell", command="cat /workspace/prompt.txt"),
         _tc("Write", path="attempt_1.py", contents=GOOD),
         _tc("Eval"),
         _tc("Submit")],
    ]
    cli = ScriptClient(script)
    row = ep.run_ablation_episode("qiskitHumanEval/15", "B", cli, tag="e4_isoabl_SELFTEST")
    check("B: no inspect calls", row["inspect_calls"] == 0)
    check("B: shell attempt counted as blocked", row["blocked_capability_attempt_count"] == 1)
    check("B: eval still available (1 call)", row["eval_calls"] == 1)

    # --- Budget: agent never submits -> loop to max_model_calls, forced submit, offline grade ---
    script = [[_tc("Write", path="attempt_1.py", contents=BAD)]] + [[] for _ in range(40)]
    cli = ScriptClient(script)
    row = ep.run_ablation_episode("qiskitHumanEval/15", "A", cli, tag="e4_isoabl_SELFTEST")
    check("A: model-call budget binds at 36", row["llm_calls"] == FROZEN_BUDGETS["max_model_calls"])
    check("A: forced submit at budget", row["forced_submit"] is True)
    check("A: termination reason recorded", row["termination_reason"] == "budget_model_calls")
    check("A: NoSubmit=0 (candidate existed)", row["NoSubmit"] == 0)

    # --- Write budget: repeated Write calls are capped and counted as blocked ---
    script = [[_tc("Write", path=f"attempt_{(i % 3) + 1}.py", contents=GOOD)] * 12 for i in range(3)]
    script = [list(x) for x in script]
    flat = [c for turn in script for c in turn]
    cli = ScriptClient([flat[:18]] + [[] for _ in range(40)])
    row = ep.run_ablation_episode("qiskitHumanEval/15", "A", cli, tag="e4_isoabl_SELFTEST")
    check("A: write budget caps at 6", row["write_calls"] == FROZEN_BUDGETS["max_write_calls"])
    check("A: extra writes counted blocked",
          row["blocked_capability_attempt_count"] >= 12 - FROZEN_BUDGETS["max_write_calls"])

    ep.run_shell = real_run_shell
    ep._grade_offline = real_grade


def main() -> int:
    test_arm_toolsets()
    test_gateway_B()
    test_gateway_C()
    test_budget_freeze()
    test_terminal_grading_isolation()
    test_resume_key_uniqueness()
    test_episode_end_to_end()
    print(f"\nselftest: {PASS} pass / {FAIL} fail", flush=True)
    return 0 if FAIL == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
