#!/usr/bin/env python3
"""rq4b offline selftest (no LLM, no sandbox, read-only).

Covers: trigger predicate, TraceGate state machine, ReplanState trigger
table + protection valve, surgery content, prompt byte-identity vs the
frozen file (rq4b_frozen_prompts.md), variant registration.
Run: python3 -m exp.fcea.selftest_rq4b  (from submit/)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FAILS: list[str] = []


def check(name: str, cond: bool) -> None:
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        FAILS.append(name)


def main() -> int:
    from exp.fcea.control import rq4b as rqb

    # ── 1. trigger predicate (frozen real messages) ──────────────────────
    trig = {
        "AssertionError: Expected 10 density matrices, but got 98": "Expected N density matrices, but got N",
        "AssertionError: Live bomb predictions should be high": "Live bomb predictions should be high",
        "AssertionError: Circuit consists of gates with unassigned parameters.": "Circuit consists of gates with unassigned parameters.",
        "KeyError: 'x'": "KeyError: 'x'",
        "ValueError: The truth value of an array with more than one element is ambiguous": "ValueError: The truth value of an array",
    }
    for msg, expect_sig in trig.items():
        sig = rqb.informative_signature(msg)
        check(f"trigger+sig {msg[:44]!r}", sig is not None and sig.startswith(expect_sig[:20]))
    non_trig = [
        "AssertionError: ",                       # bare
        "TypeError: SamplerV2.__init__() got an unexpected keyword argument 'backend'",
        "no official submit this attempt",
        "KLMismatch: KL=27.631 threshold=0.05",   # QB+ domain, not A's scope
        "",
    ]
    for msg in non_trig:
        check(f"no-trigger {msg[:44]!r}", rqb.informative_signature(msg) is None)

    # ── 2. TraceGate state machine ───────────────────────────────────────
    g = rqb.TraceGate()
    inj = g.on_failure("AssertionError: Expected 10 density matrices, but got 98")
    check("gate arms + injects", inj is not None and "[repair-contract]" in inj
          and '  "Expected 10 density matrices, but got 98"' in inj)
    check("gate no re-inject same sig",
          g.on_failure("AssertionError: Expected 10 density matrices, but got 50") is None)
    rem = g.on_write()
    check("gate violation on write", g.violations == 1 and rem is not None
          and "[repair-contract still pending]" in rem)
    g.on_failure("AssertionError: Output format incorrect")
    discharged = g.on_probe_round(["api", "trace", "env"])
    check("gate discharged by trace probe", discharged and not g.armed)
    g.on_write()
    st = g.stats()
    check("gate stats", st["injections"] == 2 and st["violations"] == 1
          and st["probe_rounds_with_trace_kind"] == 1
          and st["writes_while_armed"] == 1 and st["writes_compliant"] == 1)

    # ── 3. ReplanState trigger table ─────────────────────────────────────
    def rs(kind="replan"):
        return rqb.ReplanState(kind)

    s = rs()
    s.on_official_failure("KLMismatch: KL=12.9 threshold=0.05")
    check("no trigger at shot1", not s.on_shot2_boundary(1))
    s.on_official_failure("KLMismatch: KL=13.2 threshold=0.05")   # stalled far
    check("trigger shot2 stalled-far", s.on_shot2_boundary(2) and s.pending)
    check("max-uses respected", not s.on_shot2_boundary(2))

    s = rs(); s.on_official_failure("KLMismatch: KL=27.6 threshold=0.05")
    s.on_official_failure("KLMismatch: KL=27.0 threshold=0.05")   # −0.6: no meaningful improvement
    check("trigger big-KL slow-drift", s.on_shot2_boundary(2))

    s = rs(); s.on_official_failure("KLMismatch: KL=8.0 threshold=0.05")
    s.on_official_failure("KLMismatch: KL=0.14 threshold=0.05")   # improved a lot
    check("no trigger big improvement", not s.on_shot2_boundary(2))

    s = rs(); s.on_official_failure("KLMismatch: KL=0.06 threshold=0.05")
    s.on_official_failure("KLMismatch: KL=0.068 threshold=0.05")
    check("PROTECTION VALVE near-band never triggers", not s.on_shot2_boundary(2))

    s = rs(); s.on_official_failure("KLMismatch: KL=3.0 threshold=0.05")
    s.on_official_failure("KLMismatch: KL=3.2 threshold=0.05")
    check("no trigger mid-band (KL<5)", not s.on_shot2_boundary(2))

    s = rs(); s.on_official_failure("KLMismatch: KL=9.0 threshold=0.05")
    s.on_official_failure("TypeError: boom")                       # non-KL shot2
    check("no trigger non-KL shot2", not s.on_shot2_boundary(2))

    # ── 4. surgery ───────────────────────────────────────────────────────
    s = rs("restart")
    s.on_official_failure("KLMismatch: KL=12.5331 threshold=0.05")
    s.on_official_failure("KLMismatch: KL=12.6 threshold=0.05")
    s.on_shot2_boundary(2)
    msgs = s.surgery("SYS", "SPEC")
    check("surgery 3 messages [system,spec,injection]",
          len(msgs) == 3 and msgs[0]["content"] == "SYS"
          and msgs[1]["content"] == "SPEC" and msgs[2]["role"] == "user")
    check("surgery injection KL raw preserved",
          "KL=12.6" in msgs[2]["content"] and "12.5331" not in msgs[2]["content"])
    check("surgery pending cleared", not s.pending)
    check("restart text has no strategy clause",
          "may be invalid" not in msgs[2]["content"])
    s2 = rs("replan"); s2.on_official_failure("KLMismatch: KL=20 threshold=0.05")
    s2.on_official_failure("KLMismatch: KL=21 threshold=0.05")
    s2.on_shot2_boundary(2)
    check("replan text carries strategy clause",
          "may be invalid" in s2.surgery("SYS", "SPEC")[2]["content"])

    # ── 5. prompt byte-identity vs frozen file ───────────────────────────
    frozen = Path("/root/cyy/llm_code/submit/analysis/agent_ceiling_analysis/"
                  "rq4b_frozen_prompts.md").read_text()
    a1 = re.search(r"## 1\. A1.*?```(.*?)```", frozen, re.S).group(1).strip()
    a1 = a1.replace("<assertion body verbatim>", "BODY")
    check("A1 bytes == frozen file", rqb.trace_contract("BODY") == a1)
    b1 = re.search(r"B1\(restart\):\s*```(.*?)```", frozen, re.S).group(1).strip()
    check("B1 bytes == frozen file",
          rqb.replan_injection("restart", "12.6") == b1.replace("<X.XX>", "12.6"))
    b2 = re.search(r"B2\(replan\):\s*```(.*?)```", frozen, re.S).group(1).strip()
    check("B2 bytes == frozen file",
          rqb.replan_injection("replan", "12.6") == b2.replace("<X.XX>", "12.6"))
    r1 = rqb.replan_injection("restart", "9")
    r2 = rqb.replan_injection("replan", "9")
    clause = ("The previous solution strategy may be invalid. Re-derive the "
              "solution from the task specification, then ")
    check("B2 == B1 + strategy clause inserted at the fixed position",
          r2 == r1.replace("unavailable. Create",
                           "unavailable. " + clause + "create"))
    # tag identity
    check("both arms share neutral tag",
          rqb._RESTART_TMPL.split()[0] == rqb._REPLAN_TMPL.split()[0] == "[attempt-3]")

    # ── 6. variant registration ──────────────────────────────────────────
    from exp.fcea import config as fcfg
    check("variants registered",
          all(v in fcfg.VARIANTS for v in
              ("deurc_trace", "deurc_restart", "deurc_replan")))
    check("tag prefix registered", "rq4b_fcea" in fcfg.TAG_PREFIXES)
    check("constants on noctx stack",
          fcfg.RQB_TRACE_CONSTANTS.get("enable_context_gate") is False
          and fcfg.RQB_RESTART_CONSTANTS["rq4b_replan_kind"] == "restart"
          and fcfg.RQB_REPLAN_CONSTANTS["rq4b_replan_kind"] == "replan")

    # ── 7. A16 v2: frozen constants + expectation parser ─────────────────
    check("v2 constants frozen",
          rqb.TRACE_REJECT_CAP_PER_SHOT == 3 and rqb.TRACE_TIMEOUT_S == 16
          and rqb.TRACE_MAX_CALL_COMBOS == 24
          and rqb.TRACE_DUMMY_LADDER == (0.5, 3, "00", [], True))
    v2parse = {
        # task 138 family: the flagship parseable expectation
        "Expected 10 density matrices, but got 98": 10.0,
        "Expected 10 density matrices, but got 0": 10.0,
        # sentinel 137: "is not N" pattern
        "Length of list is not 10": 10.0,
        # sentinel 144: expected 0
        "The concurrence of the density matrix is not 0": 0.0,
        # numberless bodies -> FAIL-OPEN (None)
        "Live bomb predictions should be high": None,
        "Output format incorrect": None,
        "Circuit should contain barriers when insert_barriers=True": None,
        "Expected result to be CNOTDihedral, but got "
        "<class 'qiskit.circuit.quantumcircuit.QuantumCircuit'>": None,
        "KeyError: 'x'": None,
        "ValueError: The truth value of an array with more than one element "
        "is ambiguous. Use a.any() or a.all()": None,
        "Circuit consists of gates with unassigned parameters.": None,
        "The list doesn't contain density matrices": None,
        "The circuit doesn't cover the bloch sphere.": None,
        "Circuit contains gates outside the given dense subset": None,
        "Operators are not the same": None,
        "The candidate circuit does not match the expected solution.": None,
    }
    for body, exp in v2parse.items():
        got = rqb.parse_expected_number(body)
        check(f"parse_expected {body[:44]!r}",
              got == exp and (exp is None or isinstance(got, float)))
    check("mismatch type-coherence guard",
          # collection artifacts need a size-flavored body (frozen hint set)
          not rqb.mismatch(0.0, 10.0, body="The concurrence of the density matrix is not 0",
                           artifact_kind="sequence")
          and rqb.mismatch(10.0, 98.0, body="Expected 10 density matrices, but got 98",
                           artifact_kind="sequence")
          and rqb.mismatch(10.0, 98.0, body="Length of list is not 10",
                           artifact_kind="sequence")
          and not rqb.mismatch(10.0, 98.0, body="The circuit doesn't cover the bloch sphere.",
                               artifact_kind="sequence")
          # scalar artifacts compare for any parseable expectation
          and rqb.mismatch(0.0, 0.3, body="The concurrence of the density matrix is not 0",
                           artifact_kind="scalar"))
    check("probe value rules",
          rqb.probe_numeric_value({"kind": "scalar", "value": 98}) == 98.0
          and rqb.probe_numeric_value({"kind": "scalar", "value": 2.5}) == 2.5
          and rqb.probe_numeric_value({"kind": "scalar", "value": "98"}) is None
          and rqb.probe_numeric_value({"kind": "scalar", "value": True}) is None
          and rqb.probe_numeric_value({"kind": "sequence", "len": 98}) == 98.0
          and rqb.probe_numeric_value({"kind": "dict", "n_keys": 4}) == 4.0
          and rqb.probe_numeric_value({"kind": "QuantumCircuit",
                                       "num_qubits": 3}) is None
          and rqb.probe_numeric_value(None) is None)

    # ── 8. A16 v2: TraceGateV2 state machine ─────────────────────────────
    g2 = rqb.TraceGateV2()
    inj2 = g2.on_failure("AssertionError: Expected 10 density matrices, but got 98")
    check("v2 arms + injects + body", inj2 is not None and "[repair-contract]" in inj2
          and g2.last_body == "Expected 10 density matrices, but got 98"
          and g2.armed and len(g2.armed_bodies) == 1)
    rem2 = g2.on_write()
    check("v2 write: violation + reminder + armed PERSISTS",
          g2.violations == 1 and rem2 is not None
          and "[repair-contract still pending]" in rem2 and g2.armed)
    g2.new_shot()
    check("v2 new_shot resets per-shot reject cap", g2.l2_rejects_this_shot == 0)
    dis2 = g2.on_probe_round(["api", "trace"])
    check("v2 L3 discharge clears armed+bodies",
          dis2 and not g2.armed and not g2.armed_bodies)
    g2.on_failure("KeyError: 'x'")
    check("v2 manual-prefix body captured", g2.last_body == "KeyError: 'x'")
    check("v2 stats fields", all(k in g2.stats() for k in
          ("informative_boundaries", "boundary_probes", "blocks_delivered",
           "delivery_rate", "l2_probes", "l2_rejects", "l2_indeterminate",
           "l2_passthrough")))
    check("v2 body_of rules",
          rqb.TraceGateV2.body_of("AssertionError: Expected 10, but got 2")
          == "Expected 10, but got 2"
          and rqb.TraceGateV2.body_of("KeyError: 'x'") == "KeyError: 'x'")
    # v1 gate untouched: write still discharges v1 armed state
    g1 = rqb.TraceGate()
    g1.on_failure("AssertionError: Expected 10 density matrices, but got 98")
    g1.on_write()
    check("v1 on_write still clears armed (byte-identical v1 semantics)",
          not g1.armed)

    # ── 9. A16 v2: L1/L2 block bytes ─────────────────────────────────────
    art_probe = {"status": "ok", "phase": "artifact",
                 "artifact": {"kind": "sequence", "len": 98, "first_type": "DensityMatrix"}}
    blk = rqb.l1_block("Expected 10 density matrices, but got 98", art_probe)
    check("L1 artifact block bytes",
          blk == '[trace] assertion expects Expected 10 density matrices, but got 98; '
                 'your artifact: {"kind":"sequence","len":98,"first_type":"DensityMatrix"}')
    crash_probe = {"status": "ok", "phase": "call", "error": "ValueError: boom"}
    check("L1 crash block bytes",
          rqb.l1_block("Live bomb predictions should be high", crash_probe)
          == "[trace] assertion expects Live bomb predictions should be high; "
             "your artifact: <entry crash: ValueError: boom>")
    cons_probe = {"status": "ok", "phase": "construct", "error": "TypeError: no"}
    check("L1 construct block bytes",
          rqb.l1_block("KeyError: 'x'", cons_probe)
          == "[trace] assertion expects KeyError: 'x'; "
             "your artifact: <not constructed: TypeError: no>")
    check("L1 blocked probe -> no block",
          rqb.l1_block("body", {"status": "blocked", "phase": "invalid"}) is None
          and rqb.l1_block("", art_probe) is None)
    rej = rqb.l2_reject_block("Expected 10 density matrices, but got 98",
                              art_probe, 10.0, 98.0)
    check("L2 reject block bytes",
          rej.startswith("[trace — non-official check, this attempt was NOT consumed]\n")
          and "[trace] assertion expects Expected 10 density matrices, but got 98" in rej
          and "parsed expectation = 10.0; probe value = 98.0" in rej)

    # ── 10. A16 v2: classify_probe tri-state ─────────────────────────────
    from exp.fcea.control import trace_probe as tp
    check("classify blocked -> indeterminate",
          tp.classify_probe({"status": "blocked", "phase": "invalid"}, 10.0)[0]
          == "indeterminate")
    crash_assert = {"status": "ok", "phase": "call", "error": "AssertionError: bad input"}
    crash_other = {"status": "ok", "phase": "call", "error": "QiskitError: Invalid input data"}
    check("classify AssertionError crash -> failed",
          tp.classify_probe(crash_assert, None)[0] == "failed")
    check("classify non-assertion crash -> indeterminate (fail-open)",
          tp.classify_probe(crash_other, None)[0] == "indeterminate")
    check("classify construct -> indeterminate",
          tp.classify_probe(cons_probe, 10.0)[0] == "indeterminate")
    check("classify no expectation -> indeterminate",
          tp.classify_probe(art_probe, None, body="Expected 10 density matrices")[0]
          == "indeterminate")
    check("classify incomparable artifact -> indeterminate",
          tp.classify_probe({"status": "ok", "phase": "artifact",
                             "artifact": {"kind": "QuantumCircuit", "num_qubits": 3}},
                            10.0, body="Expected 10")[0] == "indeterminate")
    check("classify mismatch -> failed",
          tp.classify_probe(art_probe, 10.0, body="Expected 10 density matrices, but got 98")
          == ("failed", "mismatch: expected 10.0, probe value 98.0"))
    check("classify collection mismatch needs size-flavored body (/144 guard)",
          tp.classify_probe({"status": "ok", "phase": "artifact",
                             "artifact": {"kind": "sequence", "len": 10}},
                            0.0, body="The concurrence of the density matrix is not 0")[0]
          == "indeterminate")
    check("classify match -> passed",
          tp.classify_probe({"status": "ok", "phase": "artifact",
                             "artifact": {"kind": "sequence", "len": 10}},
                            10.0, body="Length of list is not 10")[0]
          == "passed")

    # ── 11. A16 v2: probe script (bytes + host execution) ────────────────
    import subprocess
    import tempfile
    script = tp.trace_probe_script("attempt_1.py", "compute")
    check("probe script deterministic bytes", script == tp.trace_probe_script("attempt_1.py", "compute"))
    try:
        compile(script, "<trace-probe>", "exec")
        compiles = True
    except SyntaxError:
        compiles = False
    check("probe script compiles", compiles)

    def run_host_script(attempt_src: str, entry: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "attempt_1.py").write_text(attempt_src, encoding="utf-8")
            out = subprocess.run(
                [sys.executable, "-c", tp.trace_probe_script("attempt_1.py", entry)],
                cwd=td, capture_output=True, text=True, timeout=60)
            for line in reversed(out.stdout.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    return json.loads(line)
            return {"phase": "no-json", "stderr": out.stderr[-200:]}

    r = run_host_script("def compute():\n    return [1, 2, 3]\n", "compute")
    check("probe host: no-arg artifact",
          r.get("phase") == "artifact" and r["artifact"]["len"] == 3)
    r = run_host_script("def compute(n: int):\n    return list(range(n))\n", "compute")
    check("probe host: typed int dummy -> 3",
          r.get("phase") == "artifact" and r["artifact"]["len"] == 3)
    r = run_host_script("def compute(x):\n    return x.foo\n", "compute")
    check("probe host: dummy crash -> call phase",
          r.get("phase") == "call" and "AttributeError" in (r.get("error") or ""))
    r = run_host_script("def compute(a):\n    raise TypeError('no rung')\n", "compute")
    check("probe host: all-TypeError -> construct phase",
          r.get("phase") == "construct" and "TypeError" in (r.get("error") or ""))
    r = run_host_script("def compute():\n    return {'a': 1, 'b': 2}\n", "nope")
    check("probe host: entry missing -> entry phase", r.get("phase") == "entry")
    r = run_host_script("def compute(:\n", "compute")
    check("probe host: import error -> import phase", r.get("phase") == "import")
    r = run_host_script("def compute():\n"
                        "    class C:\n"
                        "        __struct_fields__ = ('x', 'y')\n"
                        "    return C()\n", "compute")
    check("probe host: struct container fields",
          r.get("phase") == "artifact" and r["artifact"].get("fields") == ["x", "y"])
    r = run_host_script("def compute(n=None):\n    return n\n", "compute")
    check("probe host: defaulted param -> None artifact scalar",
          r.get("phase") == "artifact" and r["artifact"]["value"] is None)
    check("probe filename/entry validation",
          not tp.valid_filename("attempt_x.py") and not tp.valid_filename("../evil.py")
          and not tp.valid_filename("attempt_1.py "))

    # ── 12. A16 v2: variant registration ─────────────────────────────────
    check("v2 variant registered", "deurc_trace_v2" in fcfg.VARIANTS)
    check("v2 constants on noctx stack + flag",
          fcfg.RQB_TRACE_V2_CONSTANTS.get("enable_context_gate") is False
          and fcfg.RQB_TRACE_V2_CONSTANTS.get("rq4b_trace_v2") is True)
    check("v1 trace variant keeps v1 flag only",
          fcfg.RQB_TRACE_CONSTANTS.get("rq4b_trace") is True
          and "rq4b_trace_v2" not in fcfg.RQB_TRACE_CONSTANTS)

    print("\n" + ("ALL PASS" if not FAILS else f"FAILURES: {len(FAILS)}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
