"""deurq_base selftest: execution guards (corrective retry, length fuse,
artifact gate, slot salvage) + composition sanity. Stub client, zero API
calls; the qhe grader runs for real (local spawn, selftest_length_retry
precedent).

Run: python3 -m exp.fcea.selftest_base
"""
from __future__ import annotations

from types import SimpleNamespace

from exp.fcea import config as fcfg
from exp.fcea.control import execution_guard as _execg
from exp.fcea.loop import run_fcea
from exp.fcea.utility import commitment_state as fsm_mod

GOOD_CODE = (
    "```python\n"
    "from qiskit import QuantumCircuit\n"
    "def get_circuit():\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    return qc\n"
    "```"
)
GOOD_RAW = GOOD_CODE[len("```python\n"):-len("```")]
CUT_TEXT = "```python\nfrom qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\n"
_EMPTY = {"content": "", "finish": "stop"}
_PASS = 0


def check(name: str, cond: bool) -> None:
    global _PASS
    if not cond:
        raise AssertionError(f"deurq_base selftest FAILED: {name}")
    _PASS += 1
    print(f"  ok  {name}")


def _res(content: str, finish: str, tool_calls=None):
    return SimpleNamespace(
        content=content, finish_reason=finish, usage={"prompt_tokens": 10,
        "completion_tokens": 20}, tool_calls=list(tool_calls or []),
        assistant_message={"role": "assistant", "content": content},
        reasoning_content="")


class ScriptClient:
    """Pops scripted draws; a draw is (content, finish) or ("tool", calls).
    When the script is exhausted it serves clean GOOD draws so later shots
    complete deterministically (the /15 verdict itself is irrelevant here)."""

    def __init__(self, script):
        self.script = list(script)
        self.n_calls = 0
        self.temperature = 0.6

    def chat_messages(self, messages, tools=None, max_tokens=None):
        self.n_calls += 1
        if self.script:
            item = self.script.pop(0)
        else:
            item = (GOOD_CODE, "stop")
        if isinstance(item, tuple) and item and item[0] == "tool":
            return _res("", "tool_calls", tool_calls=item[1])
        content, finish = item
        return _res(content, finish)


def _write_call(path: str, contents: str):
    return [{"id": "c1", "name": "Write",
             "arguments": {"path": path, "contents": contents}}]


def test_unit() -> None:
    print("A. LengthFuse + defaults")
    check("EXEC_GUARD_DEFAULTS: flags False, cap int",
          _execg.EXEC_GUARD_DEFAULTS["exec_retry_corrective"] is False
          and _execg.EXEC_GUARD_DEFAULTS["exec_artifact_gate"] is False
          and _execg.EXEC_GUARD_DEFAULTS["exec_slot_salvage"] is False
          and _execg.EXEC_GUARD_DEFAULTS["exec_length_fuse_cap"] == 2)
    f = _execg.LengthFuse(2)
    check("cap=2: first two cuts retry, third blows",
          (f.on_cut(), f.on_cut(), f.on_cut()) == ("retry", "retry", "blown"))
    f2 = _execg.LengthFuse(0)
    check("cap=0 blows immediately", f2.on_cut() == "blown" and f2.retries_paid == 0)
    check("directives non-empty and distinct",
          all((_execg.CORRECTIVE_TEXT, _execg.FUSE_TEXT, _execg.GATE_TEXT))
          and len({_execg.CORRECTIVE_TEXT, _execg.FUSE_TEXT, _execg.GATE_TEXT}) == 3)
    check("legacy constants carry no exec/fsm flags",
          not [k for k in fcfg.DEURC_NOCTX_CONSTANTS
               if k.startswith(("exec_", "fsm_"))])
    check("base = noctx + 5 fsm + 4 exec flags",
          all(fcfg.DEURQ_BASE_CONSTANTS[k] is True for k in (
              "fsm_g1_terminate", "fsm_g2_chain", "fsm_g3_evidence_guard",
              "fsm_g4_hysteresis", "fsm_g5_best_q", "exec_retry_corrective",
              "exec_artifact_gate", "exec_slot_salvage"))
          and fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"] == 2
          and fcfg.DEURQ_BASE_CONSTANTS["focus_min_evidence"]
          == fcfg.DEURC_NOCTX_CONSTANTS["focus_min_evidence"]
          and fcfg.DEURQ_BASE_CONSTANTS.get("kl_neutral_attribution") is None)


def _run_base(script, tag_suffix: str):
    client = ScriptClient(script)
    with _variant("deurq_base"):
        fsm_mod.fsm_disable_all()
        fsm_mod.fsm_enable_from_constants(fcfg.DEURQ_BASE_CONSTANTS)
        row = run_fcea("qiskitHumanEval/15", client,
                       tag=f"rq4_fcea_base_selftest_{tag_suffix}", bench="qhe")
    fsm_mod.fsm_disable_all()
    return row, client


class _variant:
    def __init__(self, name):
        self.name = name
        self.prev = fcfg.VARIANT

    def __enter__(self):
        fcfg.set_variant(self.name)

    def __exit__(self, *a):
        fcfg.set_variant(self.prev)


def test_corrective_retry() -> None:
    print("B. corrective retry (cut -> directive -> resample)")
    row, client = _run_base([(CUT_TEXT, "length")], "cr")
    check("cut counted + exactly one corrected resample", row["length_cuts"] == 1
          and row["retry_corrected"] == 1 and row["fuse_blown_shots"] == 0)
    check("corrective marker present in call log",
          any(c.get("corrected_retry") for c in row["llm_call_log"]))
    check("an official grade landed (no NoSubmit anywhere)",
          row["official_submits"] >= 1 and row["slot_salvages"] == 0
          and row["error_type"] == "")
    check("call accounting consistent", client.n_calls == row["llm_calls"])


def test_fuse() -> None:
    print("C. fuse (cap=1: cut, paid retry also cut, then a normal cut blows)")
    old = fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"]
    fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"] = 1
    try:
        # call1 CUT -> retry paid (call2, also cut -> gated at fallback);
        # call3 CUT is a normal draw: cuts=2 > cap=1 -> blown, no resample;
        # call4 tail GOOD reaches the fallback path
        row, client = _run_base([(CUT_TEXT, "length"), (CUT_TEXT, "length"),
                                 (CUT_TEXT, "length")], "fuse")
    finally:
        fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"] = old
    corrected = [c for c in row["llm_call_log"] if c.get("corrected_retry")]
    check("exactly one corrected retry, fuse blown once",
          row["length_cuts"] == 2 and len(corrected) == 1
          and row["fuse_blown_shots"] == 1)
    check("blown cut paid no resample (cap=1, only one resample in log)",
          len([c for c in row["llm_call_log"] if c.get("length_retry")]) == 1)
    check("episode still reaches real grades", row["official_submits"] >= 1
          and row["error_type"] == "")


def test_artifact_gate() -> None:
    print("D. artifact gate (truncated draws never reach the fallback submit)")
    old = fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"]
    fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"] = 1
    try:
        # call1 CUT -> paid retry (call2, also cut -> gated); call3 CUT blows
        # the fuse (gated too); call4 tail GOOD reaches the fallback path
        row, client = _run_base([(CUT_TEXT, "length"), (CUT_TEXT, "length"),
                                 (CUT_TEXT, "length")], "gate")
    finally:
        fcfg.DEURQ_BASE_CONSTANTS["exec_length_fuse_cap"] = old
    check("both truncated residues gated (retry draw + blown cut)",
          row["artifact_gate_rejects"] == 2)
    check("episode still reached real grades via clean draws",
          row["official_submits"] >= 1 and row["error_type"] == "")
    check("accounting consistent", client.n_calls == row["llm_calls"])


def test_slot_salvage() -> None:
    print("E. slot salvage (written-but-unevaluated candidate graded at close)")
    script = [("tool", _write_call("attempt_1.py", GOOD_RAW))]
    script += [(_EMPTY["content"], _EMPTY["finish"])] * 15
    row, client = _run_base(script, "salvage")
    check("shot budget exhausted before any official eval (16 draws in shot 1)",
          client.n_calls >= 16 and row["llm_calls"] >= 16)
    check("salvage graded the candidate instead of NoSubmit",
          row["slot_salvages"] == 1 and row["official_submits"] >= 1
          and row["error_type"] != "NoSubmit")
    check("salvage visible in tool_log",
          any(t.get("slot_salvage") for t in row["tool_log"]))
    check("accounting consistent", client.n_calls == row["llm_calls"])


def main() -> None:
    test_unit()
    test_corrective_retry()
    test_fuse()
    test_artifact_gate()
    test_slot_salvage()
    print(f"\ndeurq_base selftest: {_PASS} checks passed")


if __name__ == "__main__":
    main()
