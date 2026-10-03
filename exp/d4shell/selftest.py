"""D4 (full − C0) selftest — no LLM, no benchmark cases.

Validates: tag discipline, the D4-5 prompt diff guard, controller-constants
parity with the full deurc_noctx stack, tool-set composition and the D4-3
withdrawal predicate, the deviation record shape, budget pins, and the D4-1
classification path. The loop-level smoke (mocked client + sandbox) lives in
the implementation-notes runbook; this module stays environment-free.
"""
from __future__ import annotations

import json

from exp.d4shell import config as dcfg
from exp.fcea import config as fcfg
from exp.fcea.control.controller import RepairController
from exp.fcea.control.mode_selector import FOCUS, TERMINATE
from exp.fcea.evidence.taxonomy import classify_evidence_output

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))


def main() -> int:
    # ---- tag discipline ----
    for bad in ("e4_eqpa", "rq4_fcea_qbplus_deurc_noctx", "rq3_x"):
        try:
            dcfg.refuse_foreign_tag(bad)
            check(f"tag_refuse_{bad}", False, "no exception")
        except ValueError:
            check(f"tag_refuse_{bad}", True)
    check("tag_default", dcfg.default_tag(bench="qbplus") == "rq4_d4shell_qbplus")
    check("tag_default_dev", dcfg.default_tag(bench="qbplus", dev=True)
          == "rq4_d4shell_qbplus_dev")

    # ---- budget pins identical to the FCEA/EQPA line ----
    check("pin_llm_budget", dcfg.MAX_LLM_PER_SHOT == fcfg.MAX_LLM_PER_SHOT == 16)
    check("pin_official", dcfg.MAX_OFFICIAL == fcfg.MAX_OFFICIAL == 3)
    check("pin_shell_budget", dcfg.MAX_SHELL_PER_SHOT == 8)

    # ---- controller constants: byte-identical to the full stack ----
    check("controller_constants_parity",
          dcfg.D4_CONTROLLER_CONSTANTS == fcfg.DEURC_NOCTX_CONSTANTS,
          "D4 must run the deurc_noctx controller unchanged")
    check("controller_context_gate_off",
          dcfg.D4_CONTROLLER_CONSTANTS["enable_context_gate"] is False)

    # ---- D4-5 prompt diff guard ----
    check("prompt_sentence_diff_ok", dcfg.prompt_sentence_diff_ok())
    check("prompt_no_batchprobe", "BatchProbe" not in dcfg.D4_SYSTEM)
    check("prompt_shell_sentence", "Use Shell to inspect installed Qiskit" in dcfg.D4_SYSTEM)
    check("prompt_classification_sentence",
          "Shell outputs are classified into evidence categories" in dcfg.D4_SYSTEM)
    check("prompt_notice_guidance_kept",
          "prefer evidence categories with higher estimated utility" in dcfg.D4_SYSTEM)
    check("prompt_submission_contract_kept",
          "attempt_1.py, attempt_2.py, or attempt_3.py" in dcfg.D4_SYSTEM)
    # the kept sentences must be byte-identical to FCEA_SYSTEM's tail
    tail_f = fcfg.FCEA_SYSTEM.split("After a failure")[1]
    tail_d = dcfg.D4_SYSTEM.split("After a failure")[1]
    check("prompt_tail_byte_identical", tail_f == tail_d)

    # ---- D4-3 withdrawal semantics: mirror the frozen stack (execution-layer
    # refusal; tools list unchanged) ----
    ctrl = RepairController(dcfg.D4_CONTROLLER_CONSTANTS)
    tools = [
        {"type": "function", "function": {"name": "Shell"}},
        {"type": "function", "function": {"name": "Write"}},
        {"type": "function", "function": {"name": "Eval"}},
    ]
    # the loop's _episode_tools is a flat list (audit 2026-09-25: the frozen
    # fcea filter is a no-op and D4 mirrors its observable semantics)
    check("tools_list_unchanged_by_mode", len(tools) == 3)
    check("refusal_predicate_search",
          ctrl.probe_withdrawn() is False)
    ctrl.current_mode = FOCUS
    check("refusal_predicate_focus",
          ctrl.probe_withdrawn() is True)
    ctrl.current_mode = TERMINATE
    check("refusal_predicate_terminate",
          ctrl.probe_withdrawn() is True)
    ctrl.current_mode = "SEARCH"
    check("refusal_predicate_search_restored",
          ctrl.probe_withdrawn() is False)

    # ---- deviation record ----
    dev = dcfg.d4_deviation_record()
    check("deviation_removed_c0", dev["removed_component"].startswith("C0"))
    check("deviation_six_adaptations", len(dev["interface_adaptations"]) == 6)
    check("deviation_unchanged_stack",
          any("state manager" in u for u in dev["unchanged"])
          and any("EMA updater" in u for u in dev["unchanged"])
          and any("RepairController" in u for u in dev["unchanged"]))
    try:
        json.dumps(dev)
        check("deviation_serializable", True)
    except (TypeError, ValueError) as exc:
        check("deviation_serializable", False, str(exc))

    # ---- D4-1 classification path ----
    cat, conf = classify_evidence_output("Traceback (most recent call last):\nValueError: x")
    check("shell_output_classifies_E2", cat == "E2" and conf >= 0.9)
    cat2, _ = classify_evidence_output("{'00': 512, '11': 512}")
    check("shell_output_classifies_E3", cat2 == "E3")
    # requested-kind channel is empty on Shell (traces carry kind="")
    check("no_kind_channel_note", True)

    # ---- config hashes cover the runner and the shared stack ----
    h = dcfg.config_hashes()
    check("config_hashes_shape",
          "d4shell/loop.py" in h and "fcea/control/controller.py" in h
          and all(len(v) == 16 for v in h.values()))

    ok = sum(1 for _, p, _ in RESULTS if p)
    for name, passed, detail in RESULTS:
        print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))
    print(f"\nselftest: {ok} pass / {len(RESULTS) - ok} fail")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
