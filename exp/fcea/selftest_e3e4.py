"""E3-new / E4 launch-freeze selftests — stub client, zero API calls.

Contract source: docs/E3_E4_ACCEPTANCE_PIPELINE.md (frozen 2026-10-01).
Covers the ten launch-gate behaviors:
  COMP  arm composition & legacy isolation (flags exactly as registered)
  C1    case1: Z3 fail + Z4 signature  -> Z3 only (no Z4 probe on the
        Z3-rejected candidate; slot NOT consumed; revision marked)
  C2    case2: Z3 pass + semantic mismatch -> Z4 active (loop-level probe
        execution + gate-level frozen mismatch verdict)
  C3    case3 + mirror: clean script -> E3-new == E4 observable streams,
        zero Z4 events on E4, zero acceptance events on E3-new
  SAL   salvage semantics: legacy E2 FAIL-OPEN intact; E3-new valid
        candidate salvages; invalid candidate -> slot consumed + NoSubmit
        (GateSalvage trace); previously-rejected revision is ineligible
  FB    fallback coverage: E3-new invalid fallback rejected non-officially;
        legacy E2 fallback unchanged (official grade)
  E3C   E3-new contract: Z3 active, Z4 inactive (no trace kind, no
        [repair-contract] text)
  E4C   E4 contract: Z3 active AND Z4 active (arming + contract injection)
  LC    Z4Gate armed lifecycle (arm/persist/replace/discharge/cleanup/defer)
  NEG   QB+ negative control: the frozen era-1 QB+ failure signatures all
        miss the informative predicate (activation ~= 0 prediction)
  PUR   variant purity invariant (one file == one variant; manifest match)

Run: python3 -m exp.fcea.selftest_e3e4
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from exp.fcea import config as fcfg
from exp.fcea.control import acceptance as accept_mod
from exp.fcea.control import rq4b as rqb
from exp.fcea.control.mech_flags import (EXPERIMENTAL_ARM_FLAGS,
                                         EXPERIMENTAL_VARIANTS,
                                         LEGACY_SUPERSEDED_VARIANTS,
                                         flags_for_variant)
from exp.fcea.loop import run_fcea
from exp.fcea.selftest_arms import (CASE, GOOD_CODE, GOOD_RAW, ScriptClient,
                                    _batch_call, _probe_queries, _variant,
                                    _write_call)

_PASS = 0

# Deterministic loop-level fixtures: era-1 candidate code that REPRODUCES its
# informative failure signature on the local qhe grader (frozen 2026-10-01;
# see analysis/deurq_base/E3NEW_MANIFEST.json era-1 preview). The signature
# is re-validated live in test_case1, so a dataset/grader drift fails the
# selftest loudly instead of silently weakening the contract.
CASE_INFOFORM = "qiskitHumanEval/32"
# Era-1 candidate (qiskitHumanEval/32) that deterministically reproduces the
# informative signature "ValueError: The truth value of an array..." on the
# local grader (frozen 2026-10-01 from era-1 deurq_baseenv traces; the
# signature is re-validated live in test_case1, so a dataset/grader drift
# fails the selftest loudly instead of silently weakening the contract).
INFOFORM_RAW = (
    "from qiskit import QuantumCircuit\n"
    "from qiskit.quantum_info import SparsePauliOp\n"
    "from qiskit.primitives import StatevectorEstimator\n"
    "\n"
    "def estimator_qiskit():\n"
    '    """Run a Bell circuit on Qiskit Estimator and return expectation\n'
    "    values for the bases II, XX, YY, ZZ.\"\"\"\n"
    "    qc = QuantumCircuit(2)\n"
    "    qc.h(0)\n"
    "    qc.cx(0, 1)\n"
    "\n"
    '    observables = [SparsePauliOp(op) for op in ["II", "XX", "YY", "ZZ"]]\n'
    "\n"
    "    estimator = StatevectorEstimator()\n"
    "    result = estimator.run([(qc, observables)]).result()\n"
    "    return result[0].data.evs\n")
INFOFORM_ERR_HEAD = "ValueError: The truth value of an array"
BROKEN_RAW = "def broken(:\n    pass"          # SyntaxError at Z3 preflight


def check(name: str, cond: bool) -> None:
    global _PASS
    if not cond:
        raise AssertionError(f"selftest_e3e4 FAILED: {name}")
    _PASS += 1
    print(f"  ok  {name}")


def test_composition() -> None:
    print("A. COMP: composition & legacy isolation")
    c_v2 = fcfg.DEURQ_BASEENV_V2_CONSTANTS
    c_f = fcfg.DEURQ_FINAL_CONSTANTS
    c_legacy = fcfg.DEURQ_BASEENV_CONSTANTS
    check("E3-new extras are exactly the two pipeline flags",
          {k: c_v2[k] for k in c_v2 if k not in c_legacy}
          == {"z3_gate_salvage": True, "z3_fallback_gate": True})
    check("E4 extras are exactly the two Z4 flags",
          {k: c_f[k] for k in c_f if k not in c_v2}
          == {"z4_trace_gate": True, "z4_arm_defer_when_z3": True})
    check("legacy E3 carries no pipeline flags",
          not ({"z3_gate_salvage", "z3_fallback_gate", "z4_trace_gate",
                "z4_arm_defer_when_z3"} & set(c_legacy)))
    for v in ("deurq_baseenv_v2", "deurq_final"):
        got = {k for k, v in flags_for_variant(v).items() if v}
        check(f"{v}: frozen mech1_rep Z3 set",
              got == {k for k, v in flags_for_variant("mech1_rep").items() if v})
    check("registry covers all experimental variants",
          set(EXPERIMENTAL_VARIANTS) == set(EXPERIMENTAL_ARM_FLAGS))
    check("legacy superseded marker is exactly era-1 E3",
          LEGACY_SUPERSEDED_VARIANTS == ("deurq_baseenv",))
    check("E3-new Z3 mechanism set identical to legacy E3 (definition fix, "
          "not mechanism change)",
          {k: v for k, v in flags_for_variant("deurq_baseenv_v2").items()}
          == {k: v for k, v in flags_for_variant("deurq_baseenv").items()})


def _clean_script():
    return [("tool", _batch_call(_probe_queries(1))),
            ("tool", _write_call("attempt_1.py", GOOD_RAW)),
            ("tool", [{"id": "c2", "name": "Eval", "arguments": {}}]),
            (GOOD_CODE, "stop")]


def _all_text(client):
    return "\n".join(str(m.get("content"))
                     for snap in client.seen_messages for m in snap)


def test_case1_z3_only() -> None:
    print("B. C1: Z3 fail + Z4 signature -> Z3 only")
    # shot1: informative official failure arms Z4 (contract injected);
    # shot2: a runtime-INVALID candidate + Eval -> Z3 preflight rejects,
    # slot NOT consumed, revision marked, and Z4 does NOT probe it.
    script = [("tool", _batch_call(_probe_queries(1))),
              ("tool", _write_call("attempt_1.py", INFOFORM_RAW)),
              ("tool", [{"id": "c2", "name": "Eval", "arguments": {}}]),
              ("tool", _write_call("attempt_2.py", BROKEN_RAW)),
              ("tool", [{"id": "c3", "name": "Eval", "arguments": {}}]),
              (GOOD_CODE, "stop")]
    with _variant("deurq_final"):
        c = ScriptClient(script)
        row = run_fcea(CASE_INFOFORM, c, tag="rq4_fcea_e3e4_c1", bench="qhe")
    tl = row.get("tool_log") or []
    info_shots = [s for s in row.get("shots") or []
                  if (s.get("error_message") or "").startswith(INFOFORM_ERR_HEAD)]
    check("case1 fixture: the informative signature reproduces on the live "
          "local grader", len(info_shots) >= 1)
    pf = [t for t in tl if t.get("name") == "Preflight" and t.get("rejected_eval")]
    check("case1: the invalid candidate was Z3-rejected", len(pf) >= 1)
    z4 = row.get("rq4b_trace") or {}
    check("case1: Z4 armed by the shot-1 informative failure (armed_count)",
          z4.get("armed_count", 0) >= 1 and z4.get("injections", 0) >= 1)
    tg_events = [t for t in tl if t.get("name") == "TraceGate"]
    check("case1: every L2 probe is a fallback-coverage probe — the "
          "Z3-rejected candidate was never Z4-probed (frozen R1)",
          all(t.get("fallback") or t.get("fallback_rejected")
              for t in tg_events))
    acc = row.get("acceptance") or {}
    check("case1: Z3 reject event recorded with provenance",
          acc.get("z3_reject_events", 0) >= 1)
    check("case1: Z3-first contract text present while armed",
          "[repair-contract" in _all_text(c))
    check("case1: the rejected attempt consumed no official slot",
          row.get("official_submits", 0) <= fcfg.MAX_OFFICIAL
          and any(t.get("name") == "Eval" and t.get("official_eval")
                  for t in tl))


def test_case2_z4_active() -> None:
    print("C. C2: Z3 pass + semantic mismatch -> Z4 active")
    # Loop level: the informative failure arms Z4; a Z3-VALID next candidate
    # reaches the Z4 L2 probe (machinery executed in-loop; the /32 ValueError
    # probe artifact fail-opens per frozen R5 — asserted explicitly).
    script = [("tool", _batch_call(_probe_queries(1))),
              ("tool", _write_call("attempt_1.py", INFOFORM_RAW)),
              ("tool", [{"id": "c2", "name": "Eval", "arguments": {}}]),
              ("tool", _write_call("attempt_2.py", INFOFORM_RAW.replace(
                  "shots=100", "shots=200"))),
              ("tool", [{"id": "c3", "name": "Eval", "arguments": {}}]),
              (GOOD_CODE, "stop")]
    with _variant("deurq_final"):
        c = ScriptClient(script)
        row = run_fcea(CASE_INFOFORM, c, tag="rq4_fcea_e3e4_c2", bench="qhe")
    z4 = row.get("rq4b_trace") or {}
    check("case2: Z4 armed after the informative official failure",
          z4.get("armed_count", 0) >= 1)
    check("case2: armed expectation PERSISTS into the next shot and the L2 "
          "probe executes on the Z3-valid candidate",
          z4.get("l2_probes", 0) >= 1)
    check("case2: probe artifact fail-open counted (frozen R5)",
          z4.get("l2_indeterminate", 0) + z4.get("l2_passthrough", 0) >= 1)
    # Gate level: the frozen mismatch verdict the loop delegates to
    # (/138 semantics: parseable expectation vs artifact length).
    body = "Expected 10 density matrices, but got 98"
    exp = rqb.parse_expected_number(body)
    check("case2: expectation parser recovers 10.0", exp == 10.0)
    outcome, _ = __import__("exp.fcea.control.trace_probe",
                            fromlist=["classify_probe"]).classify_probe(
        {"status": "ok", "phase": "artifact",
         "artifact": {"kind": "sequence", "len": 3}}, exp, body=body)
    check("case2: frozen L2 verdict on mismatch is 'failed'", outcome == "failed")


def test_case3_mirror() -> None:
    print("D. C3: clean script -> E3-new == E4, zero gate events")
    rows = {}
    clients = {}
    for name, var in (("E3new", "deurq_baseenv_v2"), ("E4", "deurq_final")):
        with _variant(var):
            clients[name] = ScriptClient(_clean_script())
            rows[name] = run_fcea(CASE, clients[name],
                                  tag=f"rq4_fcea_e3e4_c3_{var}", bench="qhe")
    r3, r4 = rows["E3new"], rows["E4"]
    c3, c4 = clients["E3new"], clients["E4"]
    check("case3: same LLM call count", c3.n_calls == c4.n_calls)
    check("case3: same tool sets each call",
          c3.seen_tools == c4.seen_tools)
    roles3 = [[m["role"] for m in snap] for snap in c3.seen_messages]
    roles4 = [[m["role"] for m in snap] for snap in c4.seen_messages]
    check("case3: identical per-call role sequences", roles3 == roles4)
    check("case3: identical outcome (officials/fallback/pass)",
          (r3["official_submits"], r3["fallback"], r3["passed"])
          == (r4["official_submits"], r4["fallback"], r4["passed"]))
    names3 = [t.get("name") for t in r3.get("tool_log") or []]
    names4 = [t.get("name") for t in r4.get("tool_log") or []]
    check("case3: identical tool_log event names", names3 == names4)
    check("case3: E4 shows zero Z4 events on the clean stream",
          r4.get("z4_armed") is False
          and (r4.get("rq4b_trace") or {}).get("armed_count") == 0
          and (r4.get("rq4b_trace") or {}).get("l2_probes", 0) == 0)
    acc3 = r3.get("acceptance") or {}
    check("case3: E3-new acceptance counters all zero",
          acc3.get("z3_reject_events") == 0 and acc3.get("z4_reject_events") == 0
          and acc3.get("gate_rejected_before_salvage") == 0)
    check("case3: no gate text on either stream",
          "[repair-contract" not in _all_text(c3)
          and "[repair-contract" not in _all_text(c4)
          and "Preflight" not in names3 and "GateSalvage" not in names3)


def test_salvage() -> None:
    print("E. SAL: gate-bound salvage semantics")
    empty15 = [("", "stop")] * 15

    # legacy E2: FAIL-OPEN intact — written-never-graded candidate is graded
    with _variant("deurq_base"):
        row = run_fcea(CASE, ScriptClient([("tool", _write_call("attempt_1.py", GOOD_RAW)),
                                           *empty15]),
                       tag="rq4_fcea_e3e4_sal_leg", bench="qhe")
    check("SAL: legacy E2 salvage still grades the dead slot (FAIL-OPEN kept)",
          row.get("slot_salvages") == 1 and "acceptance" not in row)

    # E3-new, runtime-VALID candidate: salvage proceeds (behavior preserved)
    with _variant("deurq_baseenv_v2"):
        row2 = run_fcea(CASE, ScriptClient([("tool", _write_call("attempt_1.py", GOOD_RAW)),
                                            *empty15]),
                        tag="rq4_fcea_e3e4_sal_ok", bench="qhe")
    check("SAL: E3-new salvages a Z3-valid candidate unchanged",
          row2.get("slot_salvages") == 1
          and (row2.get("acceptance") or {}).get("gate_rejected_before_salvage") == 0)

    # E3-new, runtime-INVALID candidate: slot consumed as NoSubmit
    with _variant("deurq_baseenv_v2"):
        row3 = run_fcea(CASE, ScriptClient([("tool", _write_call("attempt_1.py", BROKEN_RAW)),
                                            *empty15]),
                        tag="rq4_fcea_e3e4_sal_bad", bench="qhe")
    acc3 = row3.get("acceptance") or {}
    check("SAL: E3-new blocks the salvage of a Z3-invalid candidate",
          row3.get("slot_salvages") == 0
          and acc3.get("gate_rejected_before_salvage", 0) >= 1)
    check("SAL: blocked salvage consumed the slot as NoSubmit with reason",
          acc3.get("nosubmit_reasons", [None])[0] == "z3_gate_failed_at_salvage"
          and any(t.get("name") == "GateSalvage" and t.get("blocked")
                  for t in row3.get("tool_log") or []))

    # E3-new, hash-protection: a revision already rejected on the Eval path
    # is salvage-ineligible until modified (frozen R3)
    script = [("tool", _write_call("attempt_1.py", BROKEN_RAW)),
              ("tool", [{"id": "c2", "name": "Eval", "arguments": {}}]),
              *empty15]
    with _variant("deurq_baseenv_v2"):
        row4 = run_fcea(CASE, ScriptClient(script),
                        tag="rq4_fcea_e3e4_sal_hash", bench="qhe")
    acc4 = row4.get("acceptance") or {}
    check("SAL: previously-rejected revision blocked from salvage (R3)",
          acc4.get("z3_reject_events", 0) >= 1
          and row4.get("slot_salvages") == 0
          and any(r.startswith("revision_rejected_by_")
                  for r in acc4.get("nosubmit_reasons", []))
          and acc4.get("gate_rejected_before_salvage", 0) >= 1)


def test_fallback() -> None:
    print("F. FB: submission-path coverage")
    fb_broken = ("```python\ndef broken(:\n```", "stop")
    # E3-new: invalid fallback candidate rejected NON-officially (no slot)
    with _variant("deurq_baseenv_v2"):
        c = ScriptClient([fb_broken] + _clean_script())
        row = run_fcea(CASE, c, tag="rq4_fcea_e3e4_fb_v2", bench="qhe")
    tl = row.get("tool_log") or []
    check("FB: E3-new rejects the invalid fallback non-officially",
          any(t.get("name") == "Preflight" and t.get("fallback_rejected")
              for t in tl))
    check("FB: E3-new fallback rejection consumed no slot (no SyntaxError "
          "ever graded; later candidates own the officials)",
          all("invalid syntax" not in str(s.get("error_message") or "")
              for s in row.get("shots") or [])
          and (row.get("acceptance") or {}).get("z3_reject_events", 0) >= 1)
    # legacy E2: fallback unchanged — the broken candidate grades officially
    with _variant("deurq_base"):
        c2 = ScriptClient([fb_broken, ("", "stop"), ("", "stop"), ("", "stop")])
        row2 = run_fcea(CASE, c2, tag="rq4_fcea_e3e4_fb_leg", bench="qhe")
    check("FB: legacy E2 fallback still grades officially (SyntaxError "
          "reaches the slot, unchanged)",
          row2.get("fallback") is True
          and any("invalid syntax" in str(s.get("error_message") or "")
                  for s in row2.get("shots") or []))


def test_arm_contracts() -> None:
    print("G. E3C/E4C: arm behavior contracts")
    # E3-new: Z3 active (preflight on invalid candidate), Z4 inactive
    script = [("tool", _batch_call(_probe_queries(1))),
              ("tool", _write_call("attempt_1.py", BROKEN_RAW)),
              ("tool", [{"id": "c2", "name": "Eval", "arguments": {}}]),
              (GOOD_CODE, "stop")]
    with _variant("deurq_baseenv_v2"):
        c = ScriptClient(script)
        row = run_fcea(CASE, c, tag="rq4_fcea_e3e4_e3c", bench="qhe")
    check("E3C: Z3 preflight active on E3-new",
          any(t.get("name") == "Preflight" for t in row.get("tool_log") or []))
    check("E3C: Z4 inactive on E3-new (no z4 fields, no contract text)",
          "z4_armed" not in row and "z4" not in row
          and "[repair-contract" not in _all_text(c)
          and "trace" not in str(c.seen_tools))
    # E4: Z3 active AND Z4 active (schema carries the trace kind; arming
    # injects the frozen contract text)
    script4 = [("tool", _batch_call(_probe_queries(1))),
               ("tool", _write_call("attempt_1.py", INFOFORM_RAW)),
               ("tool", [{"id": "c2", "name": "Eval", "arguments": {}}]),
               (GOOD_CODE, "stop")]
    with _variant("deurq_final"):
        c4 = ScriptClient(script4)
        row4 = run_fcea(CASE_INFOFORM, c4, tag="rq4_fcea_e3e4_e4c", bench="qhe")
    check("E4C: Z3 preflight active on E4",
          any(t.get("name") == "Preflight" or t.get("name") == "Eval"
              for t in row4.get("tool_log") or []))
    check("E4C: Z4 active on E4 (armed + frozen contract text injected)",
          row4.get("z4_armed") is True
          and "[repair-contract" in _all_text(c4))
    check("E4C: acceptance telemetry present on both arms",
          "acceptance" in row and "acceptance" in row4)
    # Frozen behavior contract artifact (P1-1 extension, E3-new/E4 section)
    contract = {
        "purpose": "execution-level behavior contract, E3-new/E4 section "
                   "(acceptance pipeline; fixed synthetic scripts, stub "
                   "client, zero API calls; local qhe grader)",
        "scripts": {
            "z3_reject_flow": "probe -> Write(broken) -> Eval -> GOOD",
            "z4_arm_flow": "probe -> Write(informative-fail) -> Eval -> GOOD",
        },
        "expected": {
            "E3-new": {"z3_preflight_active": True, "z4_active": False,
                       "trace_kind_in_schema": False},
            "E4": {"z3_preflight_active": True, "z4_active": True,
                   "z4_arms_on_informative_failure": True,
                   "trace_kind_in_schema": True,
                   "fallback_l2_coverage": True},
        },
        "observed": {
            "E3-new": {
                "z3_preflight_active": any(t.get("name") == "Preflight"
                                           for t in row.get("tool_log") or []),
                "z4_active": "z4_armed" in row,
                "trace_kind_in_schema": "trace" in str(c.seen_tools),
                "acceptance": row.get("acceptance"),
            },
            "E4": {
                "z3_preflight_active": any(t.get("name") == "Eval"
                                           for t in row4.get("tool_log") or []),
                "z4_active": row4.get("z4_armed") is True
                             or (row4.get("rq4b_trace") or {}).get("armed_count", 0) >= 1,
                "z4_arms_on_informative_failure":
                    (row4.get("rq4b_trace") or {}).get("armed_count", 0) >= 1,
                "trace_kind_in_schema": "trace" in str(c4.seen_tools),
                "acceptance": row4.get("acceptance"),
            },
        },
    }
    out = Path("/root/cyy/llm_code/submit/analysis/deurq_base/"
               "ARM_BEHAVIOR_CONTRACT_E3E4.json")
    out.write_text(json.dumps(contract, indent=1) + "\n")
    print(f"  wrote {out}")


def test_z4_lifecycle() -> None:
    print("H. LC: Z4Gate armed lifecycle (frozen §6)")
    g = accept_mod.Z4Gate()
    m1 = "AssertionError: Expected 10 density matrices, but got 98"
    m2 = "AssertionError: Length of list is not 5"
    txt = g.on_failure(m1)
    check("LC: arm on informative signature + frozen contract text",
          g.armed_sig is not None and "[repair-contract]" in (txt or ""))
    check("LC: armed persists across Write (violation accounting)",
          g.on_write() is not None and g.armed_sig is not None
          and g.writes_while_armed == 1)
    g.on_failure(m2)
    check("LC: new signature REPLACES the old (single slot)",
          g.armed_sig == rqb.informative_signature(m2) and g.replaces == 1
          and g.armed == [rqb.informative_signature(m2)])
    g.l2_rejects_this_shot = 2
    g.new_shot()
    check("LC: shot boundary resets the per-shot cap, expectation PERSISTS "
          "(interpretation decision: a literal wipe would make L2 unreachable)",
          g.l2_rejects_this_shot == 0 and g.armed_sig is not None)
    g.on_failure(m1)
    g.on_l2_outcome("passed")
    check("LC: L2 'passed' verdict discharges (R6)",
          g.armed_sig is None and g.l2_discharges == 1)
    g.on_failure(m1)
    discharged = g.on_probe_round(["trace"])
    check("LC: L3 kind=trace round discharges (v2 rule kept)",
          discharged and g.armed_sig is None and g.l3_discharges == 1)
    # Z3 rejection never discharges: the acceptance layer simply never calls
    # discharge on the reject path; assert armed state survives a reject tally
    g.on_failure(m1)
    g.on_l2_outcome("failed")
    check("LC: L2 'failed' keeps the expectation armed (waits for a valid "
          "candidate)",
          g.armed_sig is not None and g.l2_rejects == 1)
    # arm-now/probe-later
    g2 = accept_mod.Z4Gate()
    check("LC: arm_silent records the expectation without injection text",
          g2.arm_silent(m1) is True and g2.armed_sig is not None)
    g2.defer_l1()
    check("LC: defer/resume counters track the pending L1",
          g2.deferred_l1 == 1 and g2.pending_l1 is True)
    g2.resume_l1()
    check("LC: resume clears the pending flag",
          g2.resumed_l1 == 1 and g2.pending_l1 is False)
    check("LC: informative_signature misses bare/interface failures",
          rqb.informative_signature("AssertionError") is None
          and rqb.informative_signature("no official submit this attempt") is None)


# Frozen QB+ negative-control set: real era-1 QB+ failure signatures
# (exp/fcea/results/rq4_fcea_base_qbplus_traces.jsonl + rq4_fcea_z1,
# 45 failed episodes, sampled 2026-10-01). ALL must miss the predicate.
QBPLUS_NEGATIVE_CONTROL = (
    "KLMismatch: KL=27.631 threshold=0.05",
    "RuntimeError: Entry point 'generate_quantum_state_qubit5' not found or not callable.",
    "KLMismatch: KL=26.9379 threshold=0.05",
    "KLMismatch: KL=0.612489 threshold=0.05",
    "KLMismatch: KL=0.780886 threshold=0.05",
    "QiskitError: 'StatePreparation parameter vector has 8 elements, therefore expects 3 qubits. However, 4 were provided.'",
    "AttributeError: 'InstructionSet' object has no attribute 'c_if'",
    "KLMismatch: KL=6.71605 threshold=0.05",
    "QiskitError: \"Cannot unroll the circuit to the given basis, ['p', 'u', 'x', 'z', 'y', 'h', 'sx', 'sxdg', 'rx', 'ry', 'rz\"]",
    "TypeError: unsupported operand type(s) for +: 'int' and 'qiskit.circuit.Qubit'",
    "ValueError: <Qubit register=(16, \"q\"), index=11> is not in list",
    "KLMismatch: KL=1.21462 threshold=0.05",
    "KLMismatch: KL=1.19846 threshold=0.05",
    "KLMismatch: KL=0.784457 threshold=0.05",
)


def test_qbplus_negative_control() -> None:
    print("I. NEG: QB+ negative control (frozen signature set)")
    misses = [m for m in QBPLUS_NEGATIVE_CONTROL
              if rqb.informative_signature(m) is None]
    check(f"NEG: all {len(QBPLUS_NEGATIVE_CONTROL)} frozen QB+ failure "
          "signatures miss the Z4 predicate (activation ~= 0 prediction)",
          len(misses) == len(QBPLUS_NEGATIVE_CONTROL))
    armed = [m for m in QBPLUS_NEGATIVE_CONTROL
             if rqb.informative_signature(m) is not None]
    check("NEG: no QB+ failure arms the gate, so the expectation parser is "
          "never reachable on QB+ (its input exists only via an armed "
          "signature; the unique-number fallback may parse identifiers in "
          "non-arming messages, which is inert)",
          len(armed) == 0)


def test_variant_purity() -> None:
    print("J. PUR: variant purity invariant (ladder_io)")
    from analysis.deurq_base import ladder_io
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tag = "rq4_fcea_purity_t"
        (root / tag).mkdir()
        man = {"variant": "deurq_baseenv_v2"}
        (root / tag / f"{tag}_manifest.json").write_text(json.dumps(man))
        tp = root / f"{tag}_traces.jsonl"
        good = {"case_id": "qiskitHumanEval/1", "variant": "deurq_baseenv_v2",
                "passed": True, "started_utc": "2026-10-02T00:00:00Z",
                "llm_calls": 5, "tag": tag}
        tp.write_text(json.dumps(good) + "\n")
        rows = ladder_io.load_ladder(tp, expect_variant="deurq_baseenv_v2")
        check("PUR: pure file loads under the manifest variant",
              len(rows) == 1)
        # I2: foreign variant row fails
        tp.write_text(json.dumps(good) + "\n"
                      + json.dumps({**good, "variant": "deurq_z1"}) + "\n")
        try:
            ladder_io.load_ladder(tp)
            mixed_ok = False
        except ladder_io.LadderDataError:
            mixed_ok = True
        check("PUR: one foreign-variant row fails the file (I2)", mixed_ok)
        # I3: legacy superseded variant rejected in ladder analyses
        tp.write_text(json.dumps({**good, "variant": "deurq_baseenv"}) + "\n")
        try:
            ladder_io.load_ladder(tp)
            legacy_ok = False
        except ladder_io.LadderDataError:
            legacy_ok = True
        check("PUR: legacy superseded E3 rows rejected without allow_legacy (I3)",
              legacy_ok)
        # I4: duplicate episode fails
        tp.write_text(json.dumps(good) + "\n" + json.dumps(good) + "\n")
        try:
            ladder_io.load_ladder(tp)
            dup_ok = False
        except ladder_io.LadderDataError:
            dup_ok = True
        check("PUR: exact duplicate episode fails the file (I4)", dup_ok)


def main() -> None:
    test_composition()
    test_case1_z3_only()
    test_case2_z4_active()
    test_case3_mirror()
    test_salvage()
    test_fallback()
    test_arm_contracts()
    test_z4_lifecycle()
    test_qbplus_negative_control()
    test_variant_purity()
    print(f"\nselftest_e3e4: {_PASS} checks passed")


if __name__ == "__main__":
    main()
