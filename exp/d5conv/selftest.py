"""D5 (d5conv) selftest — no LLM, no sandbox, no benchmark cases.

Part 1 (environment-free): tag discipline, budget pins, prompt identity with
the frozen D4_SYSTEM, mechanism invariants, deviation-record shape, hashes.

Part 2 (loop-level, stub client + patched tools): each D5 mechanism fires at
the right boundary with the right accounting, and invariant I-1 holds (from
call 15 of any shot without an official eval, the tools list is [Write, Eval]).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from exp.d4shell import config as d4cfg
from exp.d5conv import config as dcfg
from exp.d5conv import loop as d_loop
from exp.common.parse import extract_module_v2 as extract_module
from exp.fcea import config as fcfg

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))


# ---------------------------------------------------------------- Part 1
def config_checks() -> None:
    for bad in ("rq4_d4shell_qbplus", "e4_eqpa", "rq4_fcea_qbplus_deurq_fix"):
        try:
            dcfg.refuse_foreign_tag(bad)
            check(f"tag_refuse_{bad}", False, "no exception")
        except ValueError:
            check(f"tag_refuse_{bad}", True)
    check("tag_default", dcfg.default_tag(bench="qbplus") == "rq4_d5conv_qbplus")
    check("tag_default_dev", dcfg.default_tag(bench="qbplus", dev=True)
          == "rq4_d5conv_qbplus_dev")

    check("pin_llm_budget", dcfg.MAX_LLM_PER_SHOT == 16)
    check("pin_official", dcfg.MAX_OFFICIAL == 3)
    check("pin_shell_budget", dcfg.MAX_SHELL_PER_SHOT == 8)
    check("prompt_byte_identical_to_d4", dcfg.D5_SYSTEM == d4cfg.D4_SYSTEM)
    check("prompt_tail_frozen",
          dcfg.D5_SYSTEM.split("After a failure")[1]
          == fcfg.FCEA_SYSTEM.split("After a failure")[1])
    check("mechanism_invariants", dcfg.mechanism_invariants_ok(),
          "0 < ESCALATE < NARROW < 16")
    check("mechanism_flags_on", dcfg.SHELL_BUDGET_HARD and dcfg.RETRY_CORRECTIVE
          and dcfg.FALLBACK_ARTIFACT_GATE)
    for tpl, keys in ((dcfg.A1_REFUSAL, {"used", "cap", "k"}),
                      (dcfg.A2_S1, {"k", "left"}),
                      (dcfg.A2_S2_WRITE, {"k"}), (dcfg.A2_S2_EVAL, {"k"}),
                      (dcfg.A2_S2_FIX, {"k"}), (dcfg.B1_CORRECTIVE, {"k"}),
                      (dcfg.B2_REJECT, {"k", "tb"})):
        try:
            tpl.format(**{kk: 1 for kk in keys})
            check(f"template_ok_{keys}", True)
        except (KeyError, IndexError) as exc:
            check(f"template_ok_{keys}", False, str(exc))
    dev = dcfg.d5_deviation_record()
    check("deviation_four_mechanisms_plus_d6", len(dev["mechanisms"]) == 5)
    check("deviation_exclusions_recorded", len(dev["excluded_this_round"]) == 4)
    check("deviation_d5_6_streaming",
          any("D5-6" in m and "streaming" in m for m in dev["mechanisms"]))
    check("frozen_constants_transport_stream",
          "stream" in dcfg.batch_frozen_constants()["transport"])
    # D5-6: the runner must opt into streaming (source-text check, no API)
    run_src = (Path(__file__).resolve().parent / "run.py").read_text(encoding="utf-8")
    check("runner_opts_into_stream", "stream=True" in run_src,
          "d5conv run.py must pass stream=True to DeepSeekClient")
    # ...and the shared client must keep stream opt-in (frozen arms unaffected)
    llm_src = (Path(__file__).resolve().parents[1] / "common" / "llm.py").read_text(encoding="utf-8")
    check("stream_routing_opt_in_only",
          "if getattr(self, \"stream\", False):" in llm_src
          and "self.stream = bool(stream)" in llm_src)
    try:
        json.dumps(dev)
        check("deviation_serializable", True)
    except (TypeError, ValueError) as exc:
        check("deviation_serializable", False, str(exc))
    h = dcfg.config_hashes()
    check("config_hashes_shape",
          "d5conv/loop.py" in h and "d4shell/config.py" in h
          and all(len(v) == 16 for v in h.values()))


# ---------------------------------------------------------------- Part 2
class StubResult:
    def __init__(self, *, finish_reason="stop", content="", tool_calls=None):
        self.content = content
        self.finish_reason = finish_reason
        self.usage = {"prompt_tokens": 10, "completion_tokens": 20}
        self.tool_calls = tool_calls or []
        self.assistant_message = {"role": "assistant", "content": content,
                                  "tool_calls": self.tool_calls}
        self.repeat_guard = {}
        self.completion_tokens_estimated = False


class StubClient:
    """Scripted client: pops one step per call; a callable default serves the
    rest. Records the tools list it was handed at every call."""

    def __init__(self, script, default=None):
        self.script = list(script)
        self.default = default
        self.i = 0
        self.tools_seen: list[list[str]] = []
        self.shell_calls_served = 0

    def chat_messages(self, messages, tools=None, **kw):
        self.tools_seen.append([t.get("function", {}).get("name") for t in (tools or [])])
        if self.i < len(self.script):
            step = self.script[self.i]
        elif self.default is not None:
            step = self.default
        else:
            step = {"finish_reason": "stop", "content": "no more script"}
        self.i += 1
        if callable(step):
            step = step(messages)
        if isinstance(step, StubResult):
            return step
        return StubResult(**step)


def shell_step():
    return {"finish_reason": "tool_calls", "content": "",
            "tool_calls": [{"name": "Shell", "arguments": {"command": "python -c print(1)"},
                            "id": "c%d" % id(step_counter_next())}]}


def step_counter_next():
    step_counter_next.n = getattr(step_counter_next, "n", 0) + 1
    return step_counter_next.n


def write_eval_step(k=1):
    return {"finish_reason": "tool_calls", "content": "",
            "tool_calls": [
                {"name": "Write", "arguments": {"path": f"attempt_{k}.py",
                                                "contents": "VALUE = 1\n"},
                 "id": f"w{k}"},
                {"name": "Eval", "arguments": {}, "id": f"e{k}"},
            ]}


def write_step(k=1):
    return {"finish_reason": "tool_calls", "content": "",
            "tool_calls": [{"name": "Write", "arguments": {"path": f"attempt_{k}.py",
                                                           "contents": "VALUE = 2\n"},
                            "id": f"w{k}b"}]}


CODE_TEXT = ("Here is the code:\n```python\nimport numpy as np\n\n\ndef f(x):\n"
             "    return int(x) + 1\n```\ndone.")


class FakeEnv:
    """Patched tool surface for the loop under test."""

    def __init__(self, *, preflight_outcome="passed", preflight_tb=""):
        self.preflight_outcome = preflight_outcome
        self.preflight_tb = preflight_tb
        self.shell_execs = 0
        self.writes: list[str] = []
        self.official_evals = 0
        self.session = SimpleNamespace(host_dir=Path("/tmp/d5conv_selftest"),
                                       last_write_name=None, written=set())
        # save + patch
        import exp.d5conv.loop as L
        self._L = L
        self._saved = {name: getattr(L, name) for name in
                       ("ensure_jail", "load_qbplus_case", "run_shell", "run_write",
                        "run_eval", "mech_preflight")}
        L.ensure_jail = lambda *a, **k: self.session
        L.load_qbplus_case = lambda cid: {"prompt": "stub prompt", "entry_point": "f",
                                          "test": ""}
        L.run_shell = self._run_shell
        L.run_write = self._run_write
        L.run_eval = self._run_eval
        L.mech_preflight = SimpleNamespace(run_preflight=self._run_preflight)

    def _run_shell(self, command, *, session, **kw):
        self.shell_execs += 1
        return {"ok": True, "blocked": False, "kind": "shell", "text": "ok-out"}

    def _run_write(self, *, path, contents, session, **kw):
        if path not in ("attempt_1.py", "attempt_2.py", "attempt_3.py"):
            return {"ok": False, "blocked": True, "text": "Write blocked: path"}
        self.writes.append(path)
        session.last_write_name = path
        session.written.add(path)
        return {"ok": True, "blocked": False, "text": f"wrote {path}", "path": path,
                "official_eval": False}

    def _run_eval(self, *, session, k=None, grade_fn=None):
        name = f"attempt_{int(k)}.py" if k is not None else session.last_write_name
        if not name or name not in session.written:
            return {"ok": False, "blocked": False, "official_eval": False, "passed": False,
                    "error": "Eval: no successful Write for that attempt",
                    "text": "Eval: no successful Write for that attempt"}
        self.official_evals += 1
        return {"ok": True, "official_eval": True, "passed": False,
                "error": "KLMismatch: KL=1.0 threshold=0.05",
                "text": "official eval fail", "code": "VALUE = 1\n"}

    def _run_preflight(self, filename, *, session=None):
        if self.preflight_outcome == "failed":
            return {"outcome": "failed", "error": "NameError: broken",
                    "tb": self.preflight_tb or "Traceback...\nNameError: broken"}
        return {"outcome": self.preflight_outcome}

    def restore(self):
        for name, val in self._saved.items():
            setattr(self._L, name, val)

    def run(self, client):
        row = self._L.run_d5("01", client, tag="rq4_d5conv_qbplus_selftest",
                             bench="qbplus")
        return row


def loop_checks() -> None:
    check("precondition_extract_module", bool(extract_module(CODE_TEXT).strip()),
          "stub code text must yield a module for the B2 tests")

    # ---- T1 (A1): hard shell budget ----
    env = FakeEnv()
    try:
        stub = StubClient([shell_step() for _ in range(16)],
                          default=write_eval_step())
        row = env.run(stub)
        check("A1_exec_capped_at_8", env.shell_execs == 8,
              f"shell execs={env.shell_execs}")
        # shot 1: responses 9-14 refused on budget (6), 15-16 on deadline (2)
        check("A1_budget_refusals", row["shell_budget_refusals"] == 6,
              f"got {row['shell_budget_refusals']}")
        check("A1_deadline_refusals_t1", row["shell_deadline_refusals"] == 2,
              f"got {row['shell_deadline_refusals']}")
        check("A1_no_probe_log_past_cap",
              len(row["probe_log"]) == 8, f"probe_log={len(row['probe_log'])}")
        check("A1_ladder_ran_once", row["escalate_injections"] == 1
              and row["narrowed_shots"] == 1)
        check("A1_shot1_nosubmit_still_accounted",
              sum(1 for s in row["shots"]
                  if (s.get("error_message") or "").startswith("no official submit")) == 1)
    finally:
        env.restore()

    # ---- T2 (A2, no file): chatter to exhaustion; invariant I-1 ----
    env = FakeEnv()
    try:
        stub = StubClient([], default={"finish_reason": "stop",
                                       "content": "Still analyzing the approach."})
        row = env.run(stub)
        check("A2_three_shots_all_ns", len(row["shots"]) == 3
              and all((s.get("error_message") or "").startswith("no official submit")
                      for s in row["shots"]))
        check("A2_escalation_per_shot", row["escalate_injections"] == 3,
              f"got {row['escalate_injections']}")
        check("A2_narrowed_per_shot", row["narrowed_shots"] == 3,
              f"got {row['narrowed_shots']}")
        # invariant I-1: calls 15-16 of every shot see only [Write, Eval]
        ok_i1 = all(stub.tools_seen[s * 16 + j] == ["Write", "Eval"]
                    for s in range(3) for j in (14, 15))
        check("A2_invariant_I1", ok_i1,
              f"tools tail={[stub.tools_seen[14], stub.tools_seen[15]]}")
        check("A2_s1_text_present",
              any("deadline: only 4 model calls remain" in (m.get("content") or "")
                  for m in _messages_of(stub, row)))
        # S1 fires before call 13 (llm_this=12, left=4)
    finally:
        env.restore()

    # ---- T3 (A2, file on disk): EVAL variant + deadline refusal ----
    env = FakeEnv()
    try:
        script = [shell_step() for _ in range(10)] + [write_step(1)]
        stub = StubClient(script, default=shell_step())
        row = env.run(stub)
        msgs = _messages_of(stub, row)
        check("A2_eval_variant_used",
              any("is on disk — call Eval() now" in (m.get("content") or "") for m in msgs))
        check("A2_deadline_refusals_t3", row["shell_deadline_refusals"] == 2,
              f"got {row['shell_deadline_refusals']}")
        check("A2_exec_capped_t3", env.shell_execs == 8,
              f"execs={env.shell_execs}")
    finally:
        env.restore()

    # ---- T4 (B1): single cut -> corrective retry -> recovery ----
    env = FakeEnv()
    try:
        cut = {"finish_reason": "length", "content": "TRUNCATED_BODY_PARTIAL" * 50,
               "tool_calls": []}
        stub = StubClient([cut, write_eval_step(1)], default=write_eval_step())
        row = env.run(stub)
        msgs = _messages_of(stub, row)
        check("B1_retry_corrected_once", row["retry_corrected"] == 1)
        check("B1_calllog_flag",
              any(c.get("corrected_retry") for c in row["llm_call_log"]))
        check("B1_corrective_injected",
              any("hit the output token limit and was discarded" in (m.get("content") or "")
                  for m in msgs))
        check("B1_cut_message_discarded",
              not any("TRUNCATED_BODY_PARTIAL" in str(m.get("content"))
                      for m in msgs if m.get("role") == "assistant"))
        check("B1_recovery_eval_ran", env.official_evals >= 1)
    finally:
        env.restore()

    # ---- T5 (B1): double cut -> single retry, nothing submitted ----
    env = FakeEnv()
    try:
        cut = {"finish_reason": "length", "content": "DOUBLE_CUT_BODY" * 80,
               "tool_calls": []}
        stub = StubClient([cut, cut, write_eval_step(1)], default=write_eval_step())
        row = env.run(stub)
        msgs = _messages_of(stub, row)
        retries = [c for c in row["llm_call_log"] if c.get("length_retry")]
        check("B5_double_cut_single_retry",
              row["retry_corrected"] == 1 and len(retries) == 1)
        check("B5_double_cut_discarded",
              not any("DOUBLE_CUT_BODY" in str(m.get("content"))
                      for m in msgs if m.get("role") == "assistant"))
        check("B5_no_fallback_from_truncated",
              all(not (s.get("error_message") or "").startswith("no official submit")
                  for s in row["shots"]))
    finally:
        env.restore()

    # ---- T6 (B2): gate rejects broken fallback artifact ----
    env = FakeEnv(preflight_outcome="failed",
                  preflight_tb="Traceback (most recent call last):\nNameError: name 'QuantumRegister' is not defined")
    try:
        stub = StubClient([{"finish_reason": "stop", "content": CODE_TEXT}],
                          default=write_eval_step())
        row = env.run(stub)
        msgs = _messages_of(stub, row)
        check("B2_reject_counted", row["artifact_gate_rejects"] == 1,
              f"got {row['artifact_gate_rejects']}")
        check("B2_feedback_text",
              any("NOT submitted for official grading" in (m.get("content") or "")
                  for m in msgs))
        check("B2_no_nosubmit_shot",
              all(not (s.get("error_message") or "").startswith("no official submit")
                  for s in row["shots"]))
        check("B2_slot_only_via_explicit_eval", env.official_evals == 3)
    finally:
        env.restore()

    # ---- T7 (B2): gate passes valid fallback artifact ----
    env = FakeEnv(preflight_outcome="passed")
    try:
        stub = StubClient([{"finish_reason": "stop", "content": CODE_TEXT}],
                          default=write_eval_step())
        row = env.run(stub)
        check("B2_pass_consumes_slot", row["official_submits"] >= 1
              and row["artifact_gate_rejects"] == 0)
        check("B2_fallback_flag", row["fallback"] is True)
    finally:
        env.restore()


def _messages_of(stub, row):
    """The loop doesn't return messages; rebuild the marker check from the
    episode's message-bearing artifacts (tool_log texts + counters) is not
    possible, so tests assert on a shared capture list instead."""
    return _CAPTURED_MESSAGES[-1] if _CAPTURED_MESSAGES else []


_CAPTURED_MESSAGES: list[list] = []


def main() -> int:
    config_checks()

    # message capture: wrap run_d5 to keep the final messages list per episode
    orig_run_d5 = d_loop.run_d5

    def capturing_run(case_id, client, **kw):
        # piggy-back on the client's visibility: rebuild from a hooked
        # chat_messages is intrusive; simplest correct capture is a wrapper
        # that snapshots messages via a patched client that stores them.
        msgs: list = []
        orig_chat = client.chat_messages

        def chat(messages, tools=None, **kw2):
            msgs.append(list(messages))
            return orig_chat(messages, tools=tools, **kw2)

        client.chat_messages = chat
        try:
            return orig_run_d5(case_id, client, **kw)
        finally:
            _CAPTURED_MESSAGES.append(list(msgs[-1]) if msgs else [])
            client.chat_messages = orig_chat

    d_loop.run_d5 = capturing_run
    try:
        loop_checks()
    finally:
        d_loop.run_d5 = orig_run_d5

    ok = sum(1 for _, p, _ in RESULTS if p)
    for name, passed, detail in RESULTS:
        print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))
    print(f"\nselftest: {ok} pass / {len(RESULTS) - ok} fail")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
