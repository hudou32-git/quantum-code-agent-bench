"""No-LLM regression suite for Evidence-EQPA. Synthetic commands only.

Covers: tool schema parity, batch execution order/structure, clipping, caps,
dedup, canary gating, kind classification, plan templates, replan trigger,
tag refusal, and Write/Eval passthrough (reused from exp.eqpa unchanged).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

from exp import config  # noqa: E402
from exp.common.canary import ensure_canaries, scan_text  # noqa: E402
from exp.eqpa.jail import ensure_jail  # noqa: E402
from exp.eqpa.tools import run_write  # noqa: E402
from exp.evidence_eqpa import config as bcfg  # noqa: E402
from exp.evidence_eqpa.prompts import plan_from_error  # noqa: E402
from exp.evidence_eqpa.tools import (  # noqa: E402
    EVIDENCE_TOOLS,
    classify_output_kind,
    run_batch_probe,
)

_PASS = 0
_FAIL = 0


class Failed(AssertionError):
    pass


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"PASS  {name}")
    else:
        _FAIL += 1
        print(f"FAIL  {name} {detail}")


def main() -> None:
    ensure_canaries()
    session = ensure_jail("qiskitHumanEval/0", tag="e7_evidence_eqpa_selftest",
                          prompt="synthetic isolation task")

    # 1. tool schema: BatchProbe present with queries; Write/Eval reused
    names = [t["function"]["name"] for t in EVIDENCE_TOOLS]
    check("schema_tools", names == ["BatchProbe", "Write", "Eval"], str(names))
    batch_schema = EVIDENCE_TOOLS[0]["function"]["parameters"]["properties"]["queries"]
    check("schema_queries_array", batch_schema.get("type") == "array")

    # 2. batch execution: ordered structured evidence
    pr = run_batch_probe([
        {"kind": "env", "query": "python -c \"import qiskit; print(qiskit.__version__)\""},
        {"kind": "api", "query": "python -c \"from qiskit import QuantumCircuit; import inspect; print(inspect.signature(QuantumCircuit.h))\""},
        "echo batch-e2e-ok",
    ], session=session)
    ev = pr.get("evidence") or []
    check("batch_runs", pr.get("ok") and pr.get("n_run") == 3 and len(ev) == 3,
          json.dumps(pr)[:200])
    check("batch_ordered", [e["i"] for e in ev] == [1, 2, 3])
    check("batch_structured", all({"i", "kind", "ok", "output"} <= set(e) for e in ev))
    check("batch_version", any("2." in (e.get("output") or "") and e["kind"] in ("env", "version") for e in ev))

    # 3. clipping
    pr = run_batch_probe(["python -c \"print('x'*20000)\""], session=session)
    ev = pr.get("evidence") or []
    check("clip_len", ev and len(ev[0]["output"]) <= bcfg.PROBE_MAX_CHARS,
          str(len(ev[0]["output"])) if ev else "no evidence")

    # 4. cap: >5 queries -> extras rejected with reason, first 5 run
    pr = run_batch_probe([f"echo q{i}" for i in range(8)], session=session)
    check("cap_run5", pr.get("n_run") == 5, str(pr.get("n_run")))
    check("cap_reject3", len(pr.get("rejected") or []) == 3)
    check("cap_reason", (pr.get("rejected") or [{}])[0].get("reason", "").startswith("batch cap"))

    # 5. dedup
    pr = run_batch_probe(["echo dup", "echo dup", "echo other"], session=session)
    check("dedup", pr.get("n_run") == 2, str(pr.get("n_run")))

    # 6. canary: sealed pattern in output -> whole batch blocked, no content
    canary = None
    from exp.common.canary import canary_values
    cv = canary_values()
    canary = next((v for v in cv if v), None)
    if canary:
        pr = run_batch_probe([f"echo leak_{canary}", "echo fine"], session=session)
        check("canary_blocks_batch", pr.get("blocked") and "sealed pattern" in (pr.get("text") or ""))
    else:
        check("canary_blocks_batch", False, "no canary values configured")

    # 7. kind classification
    check("kind_api", classify_output_kind("(self, qubit: 'Qubit') -> InstructionSet") == "api_fact")
    check("kind_behavior", classify_output_kind("{'00': 520, '11': 480}") == "behavior_probe")
    check("kind_error", classify_output_kind("stderr:\nTraceback (most recent call last)") == "error_probe")

    # 8. plan templates
    check("plan_api", "signature" in plan_from_error("TypeError: __init__() got an unexpected keyword argument 'backend'"))
    check("plan_semantic", "distribution" in plan_from_error("KLMismatch: KL=27.6 threshold=0.05"))
    check("plan_semantic_assert", "behavioral" in plan_from_error("AssertionError: wrong counts"))
    check("plan_runtime", "reproduction" in plan_from_error("ValueError: shape mismatch"))
    check("plan_uncertain", "discriminative" in plan_from_error("some totally unclear failure"))
    check("plan_nosubmit", "no submit" in plan_from_error("no official submit this attempt"))

    # 9. replan trigger normalization (loop._norm_err): paths differ, same error
    from exp.evidence_eqpa.loop import _norm_err
    a = _norm_err("TypeError at /root/cyy/llm_code/submit/x.py: bad kwarg")
    b = _norm_err("TypeError at /tmp/other.py: bad kwarg")
    check("replan_same_after_norm", a == b)

    # 10. tag refusal
    try:
        bcfg.refuse_foreign_tag("e4_eqpa_40960")
        check("tag_refusal", False, "e4_* tag accepted")
    except ValueError:
        check("tag_refusal", True)

    # 11. Write passthrough (eqpa tool reused, exact filenames enforced)
    wr = run_write(path="attempt_1.py", contents="x = 1\n", session=session)
    check("write_passthrough", wr.get("ok") and wr.get("path") == "attempt_1.py")
    wr = run_write(path="/tmp/evil.py", contents="x", session=session)
    check("write_exact_names", wr.get("blocked"))

    # 12. probe timeout respected (bwrap timeout path)
    pr = run_batch_probe([f"sleep {bcfg.PROBE_TIMEOUT_S + 5}"], session=session)
    ev = pr.get("evidence") or []
    check("probe_timeout", ev and not ev[0].get("ok"), json.dumps(ev)[:120])

    # 13. no canary leakage anywhere in produced observations
    obs_all = ""
    pr2 = run_batch_probe(["python -c \"print(open('/workspace/prompt.txt').read()[:50])\""], session=session)
    obs_all += pr2.get("text") or ""
    check("no_canary_in_obs", not scan_text(obs_all))

    print(f"\nselftest: {_PASS} pass / {_FAIL} fail")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
