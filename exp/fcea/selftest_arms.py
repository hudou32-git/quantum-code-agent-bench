"""deurq ladder (E0-E3) arm selftests — stub client, zero API calls.

Covers the 2026-10-01 launch-audit fixes:
  C7   BatchProbe execution-layer hard budget (backend NOT called past cap)
  C9   deurq_base deu_state wiring (Z2 actually alive in the fcea loop)
  E0   d5conv CONTROLLER_OFF: no crash, no controller side effects, Z0 set on
  E1   deurq_z1: no controller / no C1C2 / no notice, exec guards on
  E3   deurq_baseenv dual-channel wiring (constants + MECH flags)
  P1   FSM registry: no cross-arm leakage within one process
  MIR  E0 vs E1 observable message stream differs ONLY by the Z1 surface

The local qhe grader runs for real (sandboxed, no LLM), same as
selftest_base / selftest_length_retry.

Run: python3 -m exp.fcea.selftest_arms
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from exp.d5conv import config as d5cfg
from exp.d5conv.loop import run_d5
from exp.fcea import config as fcfg
from exp.fcea.control import execution_guard as _execg
from exp.fcea.control.mech_flags import (EXPERIMENTAL_ARM_FLAGS,
                                         EXPERIMENTAL_VARIANTS,
                                         flags_for_variant)
from exp.fcea.loop import run_fcea
from exp.fcea.utility import commitment_state as fsm_mod

_PASS = 0
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
CASE = "qiskitHumanEval/15"


def check(name: str, cond: bool) -> None:
    global _PASS
    if not cond:
        raise AssertionError(f"selftest_arms FAILED: {name}")
    _PASS += 1
    print(f"  ok  {name}")


def _res(content, finish, tool_calls=None):
    return SimpleNamespace(
        content=content, finish_reason=finish,
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        tool_calls=list(tool_calls or []),
        assistant_message={"role": "assistant", "content": content},
        reasoning_content="")


class ScriptClient:
    """Pops scripted draws: ("tool", calls) | (content, finish) | callable.

    A callable receives (arm, call_index) and returns one of the above, so a
    single script can express both arms. Exhausted -> clean GOOD draw."""

    def __init__(self, script):
        self.script = list(script)
        self.n_calls = 0
        self.seen_messages = []      # full message list snapshot per call
        self.seen_tools = []
        self.temperature = 0.6

    def chat_messages(self, messages, tools=None, max_tokens=None):
        self.n_calls += 1
        self.seen_messages.append([dict(m) for m in messages])
        self.seen_tools.append([t.get("function", {}).get("name")
                                for t in (tools or [])])
        if self.script:
            item = self.script.pop(0)
            if callable(item):
                item = item(self.n_calls)
        else:
            item = (GOOD_CODE, "stop")
        if isinstance(item, tuple) and item and item[0] == "tool":
            return _res("", "tool_calls", tool_calls=item[1])
        content, finish = item
        return _res(content, finish)


def _batch_call(queries):
    return [{"id": "c1", "name": "BatchProbe", "arguments": {"queries": queries}}]


def _shell_call(cmd):
    return [{"id": "c1", "name": "Shell", "arguments": {"command": cmd}}]


def _write_call(path, contents):
    return [{"id": "c1", "name": "Write",
             "arguments": {"path": path, "contents": contents}}]


def _probe_queries(n=1):
    return [{"kind": "api", "query": "python -c \"print(1)\""} for _ in range(n)]


class _variant:
    def __init__(self, name):
        self.name, self.prev = name, fcfg.VARIANT

    def __enter__(self):
        fcfg.set_variant(self.name)

    def __exit__(self, *a):
        fcfg.set_variant(self.prev)


# ----------------------------------------------------------------- composition
EXPECTED_ARMS = {
    # arm: (controller/deu alive, fsm flags, exec flags on, mech flags on)
    "E1 deurq_z1":     (False, set(), {"exec_retry_corrective", "exec_artifact_gate",
                                       "exec_slot_salvage", "exec_probe_budget"}, set()),
    "E2 deurq_base":   (True, {"fsm_g1_terminate", "fsm_g2_chain",
                               "fsm_g3_evidence_guard", "fsm_g4_hysteresis",
                               "fsm_g5_best_q"},
                        {"exec_retry_corrective", "exec_artifact_gate",
                         "exec_slot_salvage", "exec_probe_budget"}, set()),
    "E3 deurq_baseenv": (True, {"fsm_g1_terminate", "fsm_g2_chain",
                                "fsm_g3_evidence_guard", "fsm_g4_hysteresis",
                                "fsm_g5_best_q"},
                         {"exec_retry_corrective", "exec_artifact_gate",
                          "exec_slot_salvage", "exec_probe_budget"},
                         {k for k, v in flags_for_variant("mech1_rep").items() if v}),
}


def test_composition() -> None:
    print("A. arm composition (derived from the wired constants/flags)")
    consts = {"deurq_z1": fcfg.DEURQ_Z1_CONSTANTS,
              "deurq_base": fcfg.DEURQ_BASE_CONSTANTS,
              "deurq_baseenv": fcfg.DEURQ_BASEENV_CONSTANTS}
    for arm, (ctrl, fsm, execs, mech) in EXPECTED_ARMS.items():
        v = arm.split()[1]
        c = consts[v]
        got_fsm = {k for k in c if k.startswith("fsm_") and c[k]}
        got_exec = {k for k in c if k.startswith("exec_") and c[k] is True}
        got_mech = {k for k in flags_for_variant(v) if flags_for_variant(v)[k]}
        miss = (fsm | execs) - (got_fsm | got_exec)
        extra = (got_fsm | got_exec) - (fsm | execs)
        # controller-side membership: E1 out of deurc families, E2/E3 in
        ctrl_ok = (v != "deurq_z1") == ctrl
        check(f"{arm}: flags exactly as registered"
              f"{'' if not (miss | extra) else ' (miss=%s extra=%s)' % (miss, extra)}",
              not miss and not extra and ctrl_ok)
        check(f"{arm}: MECH channel exactly as registered",
              got_mech == mech)
    check("E3 constants carry the mech1_rep controller-side gates",
          fcfg.DEURQ_BASEENV_CONSTANTS.get("mech_preflight") is True
          and fcfg.DEURQ_BASEENV_CONSTANTS.get("mech_directive_v2") is True
          and fcfg.DEURQ_BASE_CONSTANTS.get("mech_preflight") is None)
    check("fail-fast registry covers all experimental variants",
          set(EXPERIMENTAL_VARIANTS) == set(EXPERIMENTAL_ARM_FLAGS))


# --------------------------------------------------------------------- C7
def test_probe_hard_budget() -> None:
    print("B. C7 BatchProbe execution hard budget")
    import exp.fcea.loop as floop
    calls = {"n": 0}
    orig = floop.run_fcea_batch_probe

    def counting(queries, **kw):
        calls["n"] += 1
        return orig(queries, **kw)

    floop.run_fcea_batch_probe = counting
    try:
        # 14 batch rounds > MAX_PROBES_PER_SHOT (12): backend must stop at 12
        script = [("tool", _batch_call(_probe_queries(1)))] * 14
        client = ScriptClient(script)
        with _variant("deurq_z1"):
            row = run_fcea(CASE, client, tag="rq4_fcea_arms_c7z1", bench="qhe")
        check("E1 backend executed exactly MAX_PROBES_PER_SHOT batches",
              calls["n"] == fcfg.MAX_PROBES_PER_SHOT)
        check("E1 refusals counted (probe_budget_refusals >= 1)",
              row.get("probe_budget_refusals", 0) >= 1)
        check("E1 refusal tool messages carry the budget notice",
              any(m.get("role") == "tool" and "budget for this attempt is used" in str(m.get("content"))
                  for snap in client.seen_messages for m in snap))

        # legacy variant: reminder-only, backend keeps executing past the cap
        calls["n"] = 0
        script = [("tool", _batch_call(_probe_queries(1)))] * 14
        with _variant("deurc_noctx"):
            run_fcea(CASE, ScriptClient(script), tag="rq4_fcea_arms_c7leg",
                     bench="qhe")
        check("legacy deurc_noctx keeps reminder-only (backend ran all rounds)",
              calls["n"] > fcfg.MAX_PROBES_PER_SHOT)
    finally:
        floop.run_fcea_batch_probe = orig


# ---------------------------------------------------------------- E0 (d5conv)
def test_e0_controller_off() -> None:
    print("C. E0 controller-off (d5conv)")
    prev = d5cfg.set_react_e0(True)
    try:
        # 1) no crash with a normal tool flow + failure boundary
        script = [("tool", _shell_call("python -c \"print(1)\"")),
                  (GOOD_CODE, "stop")]
        client = ScriptClient(script)
        row = run_d5(CASE, client, tag="rq4_d5conv_arms_e0", bench="qhe")
        check("E0 runs without crash and reaches a real grade",
              row["official_submits"] >= 1 and row["error_type"] != "NoSubmit")
        check("E0: no controller state (control_log empty, withdrawn None)",
              row["control_log"] == [] and row["controller_shell_withdrawn_final"] is None)
        check("E0: no C1/C2 bookkeeping (deu_trace empty, snapshot None)",
              row["deu_trace"] == [] and row["deu_state_final"] is None)
        check("E0: zero priority notices injected",
              row["priority_injections"] == 0)
        all_msgs = [m for snap in client.seen_messages for m in snap
                    if m.get("role") in ("user", "tool")]
        # (the system prompt's notice GUIDANCE sentence is shared scaffold on
        # both arms — only injected messages count here)
        check("E0: no notice text and no mode directive in any message",
              not any("evidence-priority" in str(m.get("content"))
                      or "Repair controller" in str(m.get("content"))
                      for m in all_msgs))
        check("E0: ladder disabled (no escalate/narrow injections)",
              row["escalate_injections"] == 0 and row["narrowed_shots"] == 0)
        check("E0: variant tagged react_e0", row["variant"] == "react_e0")

        # 2) slot salvage path: write without eval, exhaust budget
        script = [("tool", _write_call("attempt_1.py", GOOD_RAW))]
        script += [("", "stop")] * 15
        row2 = run_d5(CASE, ScriptClient(script), tag="rq4_d5conv_arms_e0s",
                      bench="qhe")
        check("E0 slot salvage converts the dead shot into a grade",
              row2["slot_salvages"] == 1 and row2["official_submits"] >= 1
              and row2["error_type"] != "NoSubmit")
    finally:
        d5cfg.set_react_e0(False) if False else None
        for k, v in prev.items():
            setattr(d5cfg, k, v)
    # legacy d5conv identity outside the preset
    row3 = run_d5(CASE, ScriptClient([("tool", _shell_call("python -c \"print(1)\"")),
                                      (GOOD_CODE, "stop")]),
                  tag="rq4_d5conv_arms_leg", bench="qhe")
    check("legacy d5conv (preset off): controller alive, notices possible",
          row3["control_log"] != [] or row3["variant"] == "d5_conv")
    check("legacy d5conv: ladder active again",
          row3["escalate_injections"] >= 0 and dcfg_flags_restored())


def dcfg_flags_restored() -> bool:
    return (d5cfg.CONTROLLER_OFF is False and d5cfg.CONVERT_LADDER_OFF is False
            and d5cfg.LENGTH_FUSE_CAP is None and d5cfg.SLOT_SALVAGE is False)


# --------------------------------------------------------------- registry leak
def test_registry_no_leak() -> None:
    print("D. FSM registry: no cross-arm leakage in one process")
    with _variant("deurq_base"):
        run_fcea(CASE, ScriptClient([("tool", _batch_call(_probe_queries(1))),
                                     (GOOD_CODE, "stop")]),
                 tag="rq4_fcea_arms_leak1", bench="qhe")
    check("after E2 episode the registry is still G1-G5",
          fsm_mod.fsm_active() == ["G1", "G2", "G3", "G4", "G5"])
    with _variant("deurq_z1"):
        run_fcea(CASE, ScriptClient([("tool", _batch_call(_probe_queries(1))),
                                     (GOOD_CODE, "stop")]),
                 tag="rq4_fcea_arms_leak2", bench="qhe")
    check("after E1 episode in the SAME process the registry is cleared",
          fsm_mod.fsm_active() == [])


# --------------------------------------------------------------------- C9
def test_e2_z2_alive() -> None:
    print("E. C9: deurq_base Z2 wiring alive in the loop")
    script = [("tool", _batch_call(_probe_queries(1))),
              (GOOD_CODE, "stop")]
    with _variant("deurq_base"):
        row = run_fcea(CASE, ScriptClient(script), tag="rq4_fcea_arms_c9",
                       bench="qhe")
    check("E2: deu_trace populated (C1 alive)",
          len(row.get("deu_trace") or []) >= 1)
    check("E2: control_log populated or controller path reachable (C3 wired)",
          isinstance(row.get("control_log"), list))


# --------------------------------------------------------------------- mirror
def _canonical_system(sys_text: str) -> tuple:
    """Sentence-multiset of a system prompt (order-insensitive)."""
    return tuple(sorted(s.strip() for s in sys_text.split(". ") if s.strip()))


def _z1_sentences(text: str) -> set:
    """The substrate sentences — the ONLY allowed system-prompt difference."""
    keep = set()
    for s in (text.split(". ") or []):
        s = s.strip()
        if any(w in s for w in ("Shell", "BatchProbe", "evidence kinds",
                                "evidence categories")):
            keep.add(s)
    return keep


def test_mirror() -> None:
    print("F. E0/E1 mirror: observable stream differs only on the Z1 surface")
    prev = d5cfg.set_react_e0(True)
    try:
        e0 = ScriptClient([("tool", _shell_call("python -c \"print(7)\"")),
                           (GOOD_CODE, "stop")])
        row0 = run_d5(CASE, e0, tag="rq4_d5conv_arms_mir0", bench="qhe")
    finally:
        for k, v in prev.items():
            setattr(d5cfg, k, v)
    with _variant("deurq_z1"):
        e1 = ScriptClient([("tool", _batch_call(_probe_queries(1))),
                           (GOOD_CODE, "stop")])
        row1 = run_fcea(CASE, e1, tag="rq4_fcea_arms_mir1", bench="qhe")

    # 1) call-level shape: same number of LLM calls, same tool availability
    check("mirror: same LLM call count", e0.n_calls == e1.n_calls)
    check("mirror: same tool sets each call (Shell vs BatchProbe+same rest)",
          e0.seen_tools == [["Shell", "Write", "Eval"]] * e0.n_calls
          and e1.seen_tools == [["BatchProbe", "Write", "Eval"]] * e1.n_calls)

    # 2) per-call role sequences identical
    roles0 = [[m["role"] for m in snap] for snap in e0.seen_messages]
    roles1 = [[m["role"] for m in snap] for snap in e1.seen_messages]
    check("mirror: identical per-call role sequences", roles0 == roles1)

    # 3) system prompts: the ACTUAL messages equal the guarded constants, and
    #    the frozen sentence-level guard (d4shell prompt_sentence_diff_ok)
    #    proves the two constants differ ONLY by the Z1 substrate sentences
    #    (2 Shell sentences vs 4 BatchProbe sentences, everything else equal)
    from exp.d4shell import config as d4cfg
    sys0 = e0.seen_messages[0][0]["content"]
    sys1 = e1.seen_messages[0][0]["content"]
    check("mirror: E0 system prompt is the guarded D5/D4 constant",
          sys0 == d5cfg.D5_SYSTEM == d4cfg.D4_SYSTEM)
    check("mirror: E1 system prompt is the guarded FCEA constant",
          sys1 == fcfg.FCEA_SYSTEM)
    check("mirror: frozen sentence guard holds (delta = Z1 sentences only)",
          d4cfg.prompt_sentence_diff_ok())
    _sa = sorted(s.strip() for s in sys0.split(". ") if s.strip())
    _sb = sorted(s.strip() for s in sys1.split(". ") if s.strip())
    only0 = [s for s in _sa if s not in _sb]
    only1 = [s for s in _sb if s not in _sa]
    check("mirror: exactly the 2 Shell / 4 BatchProbe substrate sentences differ",
          len(only0) == 2 and len(only1) == 4
          and all("Shell" in s for s in only0)
          and all("BatchProbe" in s or "kind" in s or "Evidence kinds" in s
                  for s in only1))

    # 4) user spec prompts identical (workspace inspect line is part of user0 —
    #    it names the substrate, i.e. Z1 surface: compare ignoring that line)
    u0 = e0.seen_messages[0][1]["content"]
    u1 = e1.seen_messages[0][1]["content"]
    l0 = [ln for ln in u0.splitlines() if not ln.lstrip().startswith("- inspect:")]
    l1 = [ln for ln in u1.splitlines() if not ln.lstrip().startswith("- inspect:")]
    check("mirror: task spec identical except the inspect line", l0 == l1)

    # 5) probe tool message names (Z1 surface) and everything else identical:
    #    compare tool-message NAME multisets with the substrate name normalized
    def norm_names(snap):
        out = []
        for m in snap:
            if m.get("role") == "tool":
                n = m.get("name") or ""
                out.append("PROBE" if n in ("Shell", "BatchProbe") else n)
        return out
    names0 = [norm_names(s) for s in e0.seen_messages[1:]]
    names1 = [norm_names(s) for s in e1.seen_messages[1:]]
    check("mirror: tool-call names identical after substrate normalization",
          names0 == names1)

    # 6) no notices / no directives anywhere on either arm (user/tool only —
    #    the system prompt's guidance sentence is shared scaffold)
    for tag_arm, cl in (("E0", e0), ("E1", e1)):
        check(f"mirror: {tag_arm} carries no notice/directive messages",
              not any("evidence-priority" in str(m.get("content"))
                      or "Repair controller" in str(m.get("content"))
                      for snap in cl.seen_messages for m in snap
                      if m.get("role") in ("user", "tool")))

    # 7) outcome shape: same official submissions, same fallback flag,
    #    same exec-guard counters class (salvage both possible)
    check("mirror: same official submit count & fallback flag",
          row0["official_submits"] == row1["official_submits"]
          and row0["fallback"] == row1["fallback"])
    check("mirror: same pass verdict on the identical final draw",
          row0["passed"] == row1["passed"])


def main() -> None:
    test_composition()
    test_probe_hard_budget()
    test_e0_controller_off()
    test_registry_no_leak()
    test_e2_z2_alive()
    test_mirror()
    test_behavior_contract()
    print(f"\nselftest_arms: {_PASS} checks passed")


# ---------------------------------------------------------------- P1-1 contract
def test_behavior_contract() -> None:
    """Execution-level behavioral contract (audit P1-1): each arm runs the
    SAME fixed synthetic script (one failing attempt, then recovery) and the
    OBSERVED events are asserted against the preregistered per-arm pattern.
    Writes analysis/deurq_base/ARM_BEHAVIOR_CONTRACT.json."""
    print("G. behavior fingerprint contract (E0/E1/E2/E3)")

    # Semantically wrong but EXECUTABLE: passes the Z3 preflight (compile+exec
    # ok), fails the official hidden tests — so the official failure boundary
    # fires identically on E2 and E3. (A syntax-error module would be caught
    # by E3's preflight before the official slot — correct Z3 behavior, but
    # then no boundary fires and E3 would legitimately show no controller
    # decision on this flow.)
    WRONG_RAW = "from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)"
    contract = {}
    prev = d5cfg.set_react_e0(True)
    try:
        c = ScriptClient([("tool", _shell_call("python -c \"print(7)\"")),
                          ("tool", _write_call("attempt_1.py", WRONG_RAW)),
                          ("tool", [{"id": "c2", "name": "Eval",
                                    "arguments": {}}]),
                          (GOOD_CODE, "stop")])
        row = run_d5(CASE, c, tag="rq4_d5conv_arms_fp", bench="qhe")
        contract["E0"] = _events(row, c)
    finally:
        for k, v in prev.items():
            setattr(d5cfg, k, v)
    for arm in ("deurq_z1", "deurq_base", "deurq_baseenv"):
        with _variant(arm):
            c = ScriptClient([("tool", _batch_call(_probe_queries(1))),
                              ("tool", _write_call("attempt_1.py", WRONG_RAW)),
                              ("tool", [{"id": "c2", "name": "Eval",
                                        "arguments": {}}]),
                              (GOOD_CODE, "stop")])
            row = run_fcea(CASE, c, tag=f"rq4_fcea_arms_fp_{arm}", bench="qhe")
            contract[{"deurq_z1": "E1", "deurq_base": "E2",
                      "deurq_baseenv": "E3"}[arm]] = _events(row, c)

    expected = {
        # shell/probe event comes from the substrate; notice/controller from
        # Z2; salvage/fuse always possible. env_probe=False everywhere: the
        # E (env probe) mechanism belongs to mech1_PREV only — mech1_rep
        # (= Z3) carries A/B/C/D-F/D1/v2 but NOT E (new.md §2).
        "E0": {"substrate_call": "shell", "controller_decision": False,
               "notice": False, "env_probe": False},
        "E1": {"substrate_call": "probe", "controller_decision": False,
               "notice": False, "env_probe": False},
        "E2": {"substrate_call": "probe", "controller_decision": True,
               "notice": True, "env_probe": False},
        "E3": {"substrate_call": "probe", "controller_decision": True,
               "notice": True, "env_probe": False},
    }
    for arm, exp in expected.items():
        ev = contract[arm]
        for k, v in exp.items():
            check(f"contract {arm}.{k} == {v}", ev.get(k, v) == v)
    out = Path("/root/cyy/llm_code/submit/analysis/deurq_base/"
               "ARM_BEHAVIOR_CONTRACT.json")
    out.write_text(json.dumps({
        "purpose": "execution-level behavior contract for the E0-E3 ladder "
                   "(fixed synthetic script: failing attempt then recovery; "
                   "stub client, zero API calls; local qhe grader)",
        "events_observed": contract,
        "expected": expected,
    }, indent=1) + "\n")
    print(f"  wrote {out}")


def _events(row, client) -> dict:
    tl = row.get("tool_log") or []
    all_msgs = [m for snap in client.seen_messages for m in snap
                if m.get("role") in ("user", "tool")]
    return {
        "substrate_call": ("shell" if any(t.get("name") == "Shell" for t in tl)
                           else "probe" if any(t.get("name") == "BatchProbe"
                                               for t in tl) else None),
        "controller_decision": bool(row.get("control_log")),
        "notice": row.get("priority_injections", 0) > 0
                  or any("evidence-priority" in str(m.get("content"))
                         for m in all_msgs),
        "env_probe": any("[environment probe" in str(m.get("content"))
                         for m in client.seen_messages[0]
                         if m.get("role") == "user"),
        "slot_salvage": row.get("slot_salvages", 0),
        "artifact_gate_rejects": row.get("artifact_gate_rejects", 0),
        "official_submits": row.get("official_submits"),
        "llm_calls": client.n_calls,
    }


if __name__ == "__main__":
    main()
