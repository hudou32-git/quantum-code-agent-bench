"""No-LLM selftest for the v6 baseline engine. Run: python3 -m exp.common.baseline.selftest"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exp.common.baseline.config import (  # noqa: E402
    DECODING_TEMPERATURE,
    LLM_PROVIDER,
    MODEL,
    MODEL_FAMILY,
    PASSK_ARMS,
    PASS_K,
    default_tag,
    normalize_arm,
    refuse_locked_tag,
    require_model,
)
from exp.common.baseline.feedback import feedback_for  # noqa: E402
from exp.common.baseline.prompts import first_user, spec_user  # noqa: E402
from exp.common.env_guard import require_grader_python  # noqa: E402
from exp.common.llm import resolve_model  # noqa: E402
from exp.config import QBPLUS_SMOKE_CASES, TEMPERATURE  # noqa: E402


class Failed(AssertionError):
    pass


def test_model_and_tags() -> None:
    require_model(MODEL)
    if MODEL != resolve_model():
        raise Failed(f"MODEL must come from .env DEEPSEEK_MODEL, got {MODEL}")
    if MODEL_FAMILY != MODEL:
        raise Failed(MODEL_FAMILY)
    if LLM_PROVIDER != "deepseek":
        raise Failed(LLM_PROVIDER)
    for allowed in ("deepseek-flash", "deepseek-v4-flash-0731"):
        if require_model(allowed) != allowed:
            raise Failed(f"channel gating removed: {allowed} must pass through")
    for locked in (
        "e4_base_v4_oneshot",
        "e4_base_v5_oneshot",
        "e4_iso",
        "e4_qhe_ef_loop",
    ):
        try:
            refuse_locked_tag(locked)
        except ValueError:
            continue
        raise Failed(f"must refuse {locked}")
    if DECODING_TEMPERATURE != TEMPERATURE or TEMPERATURE != 0.6:
        raise Failed(f"v6 decoding pin drifted: config={TEMPERATURE} baseline={DECODING_TEMPERATURE}")
    if PASS_K != 3 or PASSK_ARMS != {"zeroshot", "cot", "qscot", "rag"}:
        raise Failed((PASS_K, sorted(PASSK_ARMS)))
    if default_tag("loop", bench="qbplus") != "e4_base_v8_loop_qbplus":
        raise Failed(default_tag("loop", bench="qbplus"))
    if default_tag("zeroshot") != "e4_base_v8_passk3_zeroshot":
        raise Failed(default_tag("zeroshot"))
    if default_tag("qscot", dev=True) != "e4_base_v8_passk3_qscot_dev":
        raise Failed(default_tag("qscot", dev=True))
    if default_tag("cot", bench="qbplus", pass_k=1) != "e4_base_v8_passk1_cot_qbplus":
        raise Failed(default_tag("cot", bench="qbplus", pass_k=1))
    if default_tag("loop_cot") != "e4_base_v8_loop_cot":
        raise Failed(default_tag("loop_cot"))
    if default_tag("loop_rag", bench="qbplus", dev=True) != "e4_base_v8_loop_rag_qbplus_dev":
        raise Failed(default_tag("loop_rag", bench="qbplus", dev=True))
    if set(normalize_arm(a) for a in (
        "zeroshot", "cot", "qscot", "rag", "loop",
        "loop_cot", "loop_qscot", "loop_rag",
    )) != {
        "zeroshot",
        "cot",
        "qscot",
        "rag",
        "loop",
        "loop_cot",
        "loop_qscot",
        "loop_rag",
    }:
        raise Failed("arm set drifted")


def test_prompts() -> None:
    case = {
        "case_id": "qiskitHumanEval/0",
        "entry_point": "create_quantum_circuit",
        "prompt": "Generate a Quantum Circuit for n_qubits.",
        "benchmark": "qhe",
        "framework": "qiskit",
    }
    zeroshot = first_user("zeroshot", case)
    if "Public specification:" not in zeroshot or "```python" not in zeroshot:
        raise Failed(zeroshot[:200])
    cot = first_user("cot", case)
    if "think step by step" not in cot.lower():
        raise Failed(cot[:200])
    qscot = first_user("qscot", case)
    if "Demonstration 1" not in qscot or "Q-SCoT" not in qscot:
        raise Failed(qscot[:300])
    if "qiskitHumanEval" in qscot and "local_hard" in qscot:
        raise Failed("demos must not mention local_hard")
    rag = first_user(
        "qscot" if False else "rag",
        case,
        rag_block="<retrieved_knowledge>\nSDK excerpt\n</retrieved_knowledge>",
    )
    if "retrieved_knowledge" not in rag:
        raise Failed(rag[:200])
    for text in (zeroshot, cot, qscot, rag):
        if "check(" in text or "sealed" in text or "canonical_output" in text:
            raise Failed("leak")
        if "```python" not in text and "python fence" not in text.lower():
            raise Failed("missing fence instruction")


def test_feedback() -> None:
    # v7: feedback template aligned byte-for-byte with the official QuanBench+
    # feedback_loop (attempt framing + stage label + instruction + code echo).
    fb = feedback_for(
        error="KL=0.2 threshold=0.05",
        attempt=2,
        max_attempts=3,
        code_snippet="def make_bell():\n    pass",
    )
    for marker in (
        "failed on attempt 2 of 3.",
        "Error from execution / transpilation:",
        "KL=0.2 threshold=0.05",
        "Fix the implementation and respond with corrected Python code only",
        "Your previous code (for reference):",
        "```python",
        "def make_bell():",
    ):
        if marker not in fb:
            raise Failed(marker)
    long = feedback_for(error="boom", attempt=1, max_attempts=3, code_snippet="x" * 7000)
    if "# ... [truncated]" not in long:
        raise Failed("long snippet must carry the truncation marker")
    bare = feedback_for(error="", attempt=1, max_attempts=3)
    if "(no message)" not in bare or "Your previous code" in bare:
        raise Failed(bare)


def test_grader_python() -> None:
    # 2026-09-19 grader unification: the main-table record must describe the
    # conda qhe spawn env (qiskit 2.x); the legacy 1.2.4 in-process record is
    # only produced with QHE_GRADER_INPROCESS=1 (frozen-row reproduction).
    rec = require_grader_python()
    if rec.get("mode") == "conda_qhe_spawn":
        if not rec["qiskit"].startswith("2.") or rec["executable"] != str(
            Path("/root/anaconda3/envs/qhe/bin/python")
        ):
            raise Failed(rec)
    elif rec.get("mode") == "inprocess_legacy_1_2_4":
        if rec["qiskit"].startswith("2."):
            raise Failed(rec)
    else:
        raise Failed(rec)


def test_load_cases() -> None:
    from exp.common.cases import load_base_case

    qhe = load_base_case("qiskitHumanEval/15", bench="qhe")
    if not qhe.get("prompt") or qhe.get("test") is None:
        raise Failed(sorted(qhe.keys()))
    qb = load_base_case(QBPLUS_SMOKE_CASES[0], bench="qbplus")
    if qb.get("entry_point") is None:
        raise Failed(qb)


def test_parse_extraction() -> None:
    """Extraction regressions: historical xfix shapes + adversarial traps."""
    from exp.common.parse import (
        extract_module,
        extract_module_v2,
        extraction_status,
    )

    docstring_first = (
        '```python\n"""Module providing a circuit builder."""\n'
        "from qiskit import QuantumCircuit\n\n"
        "def create_quantum_circuit(n):\n    return QuantumCircuit(n)\n```"
    )
    try_first = (
        "```python\ntry:\n    from qiskit.synthesis import LieTrotter\n"
        "except ImportError:\n    from qiskit.synthesis.evolution import LieTrotter\n\n"
        "def build():\n    return LieTrotter()\n```"
    )
    if extract_module(docstring_first):
        raise Failed("v1 gate must stay strict (history compat), got docstring accepted")
    for text in (docstring_first, try_first):
        if not extract_module_v2(text):
            raise Failed("v2 must recover docstring/try-first fenced modules")
    if extraction_status(docstring_first)["extraction_status"] != "recovered":
        raise Failed("status must be 'recovered' for v1-empty v2-ok")
    ok_row = extraction_status("```python\nimport qiskit\n```")
    if ok_row["extraction_status"] != "ok" or ok_row["extraction_recovery"]:
        raise Failed(ok_row)
    if extraction_status("no code here at all")["extraction_status"] != "empty":
        raise Failed("status must be 'empty' with no code")
    # prose containing 'def ' must not be extracted as code (prose-trap)
    prose = "A good approach is to def use the function later. See docs."
    if extract_module_v2(prose):
        raise Failed(extract_module_v2(prose)[:80])
    # full module beats a trailing call-example block when no entry hint
    trap = (
        "Final implementation:\n```python\nfrom qiskit import QuantumCircuit\n\n"
        "def solve(n):\n    return QuantumCircuit(n)\n```\n"
        "Usage example:\n```python\nprint(solve(3))\n```"
    )
    code = extract_module_v2(trap)
    if "def solve" not in code:
        raise Failed(f"last-block trap: got {code[:60]!r}")
    # unterminated trailing fence is recovered
    unterminated = "Answer:\n```python\nfrom qiskit import QuantumCircuit\n\ndef solve(n):\n    return n"
    if not extract_module_v2(unterminated):
        raise Failed("unterminated trailing fence must be recovered")


def test_parse_v3_prototype() -> None:
    """v3 candidate+ast ranking: entry-point signal and trap resistance."""
    from exp.common.parse_v3 import extract_module_v3

    docstring_first = (
        '```python\n"""Module providing a circuit builder."""\n'
        "from qiskit import QuantumCircuit\n\n"
        "def create_quantum_circuit(n):\n    return QuantumCircuit(n)\n```"
    )
    r = extract_module_v3(docstring_first, entry_point="create_quantum_circuit")
    if not r.parse_ok or not r.defines_entry_point or r.source != "fenced_tagged":
        raise Failed(r)
    trap = (
        "Final implementation:\n```python\nfrom qiskit import QuantumCircuit\n\n"
        "def solve(n):\n    return QuantumCircuit(n)\n```\n"
        "Usage example:\n```python\nprint(solve(3))\n```"
    )
    r = extract_module_v3(trap, entry_point="solve")
    if r.candidate_index != 0 or not r.defines_entry_point or r.is_call_example:
        raise Failed(r)
    prose = "We can def init the matrix and print(1) later."
    r = extract_module_v3(prose)
    if r.code:
        raise Failed(f"prose-trap: {r.code[:60]!r}")
    r = extract_module_v3("no candidates at all")
    if r.code or not r.diagnostics:
        raise Failed("empty extraction must carry diagnostics")


class _FakeResult:
    def __init__(self, content: str):
        self.content = content
        self.usage = {"prompt_tokens": 10, "completion_tokens": 20}
        # e7 P0-1: engine reads finish_reason for the length-retry rule
        self.finish_reason = "stop"


class _FakeClient:
    """Scripted fake: reply[i] is returned to the i-th chat call."""

    temperature = 0.6

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def chat_messages(self, messages, *, tools=None, **kwargs):
        self.calls.append([dict(m) for m in messages])
        return _FakeResult(self.replies[len(self.calls) - 1])


_CODE_OK = "```python\nfrom qiskit import QuantumCircuit\n\n\ndef create_quantum_circuit(n):\n    return QuantumCircuit(n)\n```"


def test_passk_engine() -> None:
    """v6 pass@k: k independent samples, no feedback, any-pass aggregation."""
    import exp.common.baseline.loop as loop_mod
    from exp.common.baseline.loop import run_base_task

    replies = [_CODE_OK, _CODE_OK, "no code in this reply at all"]
    client = _FakeClient(replies)

    def fake_grade(case, code, *, bench, results_root, tag, k, case_id=""):
        # sample 2 passes; samples 1 and 3 fail
        return {"passed": k == 2, "error_type": "" if k == 2 else "AssertionError",
                "error_message": "" if k == 2 else "assert failed"}

    orig = loop_mod._grade_case
    loop_mod._grade_case = fake_grade
    try:
        with tempfile.TemporaryDirectory() as td:
            row = run_base_task(
                "qiskitHumanEval/15",
                client,
                arm="zeroshot",
                bench="qhe",
                tag="e4_base_v8_passk3_zeroshot_selftest",
                results_root=Path(td),
                pass_k=3,
            )
    finally:
        loop_mod._grade_case = orig

    if row["passed"] is not True or row["pass_fail"] != "PASS":
        raise Failed("any-pass aggregation broken: sample 2 passed but row failed")
    if row["sampling_mode"] != "independent_passk" or row["pass_k"] != 3:
        raise Failed((row["sampling_mode"], row["pass_k"]))
    if row["n_samples_passed"] != 1 or row["llm_calls"] != 3 or row["official_attempts"] != 3:
        raise Failed((row["n_samples_passed"], row["llm_calls"], row["official_attempts"]))
    if len(client.calls) != 3:
        raise Failed(f"expected 3 LLM calls, got {len(client.calls)}")
    for i, msgs in enumerate(client.calls):
        if len(msgs) != 1 or msgs[0]["role"] != "user":
            raise Failed(f"sample {i + 1} must be a fresh single-turn conversation, got {msgs}")
    for s in row["shots"]:
        if s.get("feedback_sent"):
            raise Failed("pass@k samples must never receive feedback")
        if "extraction_status" not in s:
            raise Failed("shots must carry extraction_status labels")
    if row["shots"][2]["extraction_status"] != "empty":
        raise Failed(row["shots"][2])
    if abs(row["decoding_temperature"] - 0.6) > 1e-9:
        raise Failed(row["decoding_temperature"])

    # all-fail variant: anypass must be False
    client2 = _FakeClient([_CODE_OK] * 3)

    def fake_grade2(case, code, *, bench, results_root, tag, k, case_id=""):
        return {"passed": False, "error_type": "AssertionError", "error_message": "x"}

    loop_mod._grade_case = fake_grade2
    try:
        with tempfile.TemporaryDirectory() as td:
            row2 = run_base_task(
                "qiskitHumanEval/15",
                client2,
                arm="zeroshot",
                bench="qhe",
                tag="e4_base_v8_passk3_zeroshot_selftest",
                results_root=Path(td),
                pass_k=3,
            )
    finally:
        loop_mod._grade_case = orig
    if row2["passed"] or row2["n_samples_passed"] != 0:
        raise Failed((row2["passed"], row2["n_samples_passed"]))

    # loop arm keeps its adaptive schedule: feedback present, cap=3, pass_k=1
    client3 = _FakeClient([_CODE_OK, _CODE_OK, _CODE_OK])

    def fake_grade3(case, code, *, bench, results_root, tag, k, case_id=""):
        return {"passed": k == 3, "error_type": "" if k == 3 else "RuntimeError",
                "error_message": "" if k == 3 else "boom"}

    loop_mod._grade_case = fake_grade3
    try:
        with tempfile.TemporaryDirectory() as td:
            row3 = run_base_task(
                "qiskitHumanEval/15",
                client3,
                arm="loop",
                bench="qhe",
                tag="e4_base_v7_loop_selftest",
                results_root=Path(td),
            )
    finally:
        loop_mod._grade_case = orig
    if row3["sampling_mode"] != "adaptive_feedback" or row3["pass_k"] != 1:
        raise Failed((row3["sampling_mode"], row3["pass_k"]))
    if not any(s.get("feedback_sent") for s in row3["shots"]):
        raise Failed("loop arm must keep the adaptive feedback schedule")
    if len(client3.calls) != 3 or len(client3.calls[1]) != 3:
        raise Failed("loop arm rounds must grow the conversation (user, asst, feedback)")


def test_passk_summary() -> None:
    """build_summary pass@k semantics: metric label, curve, extraction dist."""
    from exp.common.baseline.runner import build_summary

    def row(case_id: str, outcomes: list[bool], ext: str = "ok") -> dict:
        return {
            "case_id": case_id,
            "arm": "ZEROSHOT",
            "passed": any(outcomes),
            "pass_fail": "PASS" if any(outcomes) else "FAIL",
            "llm_calls": len(outcomes),
            "official_attempts": len(outcomes),
            "pass_k": len(outcomes),
            "n_samples_passed": sum(outcomes),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "canary_hits": 0,
            "shots": [
                {"k": i + 1, "passed": p, "extraction_status": ext}
                for i, p in enumerate(outcomes)
            ],
        }

    rows = [
        row("a", [False, True, False]),
        row("b", [False, False, True]),
        row("c", [False, False, False], ext="empty"),
    ]
    with tempfile.TemporaryDirectory() as td:
        s = build_summary(
            ids=["a", "b", "c"],
            rows=rows,
            tag="e4_base_v8_passk3_zeroshot_selftest",
            arm="zeroshot",
            bench="qhe",
            out_path=Path(td) / "t.jsonl",
            n_workers=1,
            n_skipped=0,
            n_errors=0,
            split="eval",
            proto={"pass_k": 3, "max_attempts": 1},
        )
    if s["pass"] != 2 or s["metric"] != "pass@3":
        raise Failed((s["pass"], s["metric"]))
    if (s["pass_at_1"], s["pass_at_2"], s["pass_at_3"]) != (0, 1, 2):
        raise Failed((s["pass_at_1"], s["pass_at_2"], s["pass_at_3"]))
    if s["pass_rate"] != round(2 / 3, 4) or s["samples_passed_mean"] != round(2 / 3, 4):
        raise Failed((s["pass_rate"], s["samples_passed_mean"]))
    if s["extraction_status_dist"] != {"ok": 6, "empty": 3}:
        raise Failed(s["extraction_status_dist"])
    lo, hi = s["pass_rate_wilson95"]
    if not (0.0 <= lo <= 2 / 3 <= hi <= 1.0):
        raise Failed(s["pass_rate_wilson95"])
    if s["sample_1_pass"] != 0 or s["sample_2_pass"] != 1 or s["sample_3_pass"] != 1:
        raise Failed((s["sample_1_pass"], s["sample_2_pass"], s["sample_3_pass"]))


def test_loop_first_shot() -> None:
    """loop_X first shots must be byte-identical to arm X's first shots."""
    case = {
        "case_id": "qiskitHumanEval/0",
        "entry_point": "create_quantum_circuit",
        "prompt": "Generate a Quantum Circuit for n_qubits.",
        "benchmark": "qhe",
        "framework": "qiskit",
    }
    for sub in ("cot", "qscot", "rag"):
        arm = f"loop_{sub}"
        if first_user(arm, case, rag_block="<retrieved_knowledge>X</retrieved_knowledge>") != (
            first_user(sub, case, rag_block="<retrieved_knowledge>X</retrieved_knowledge>")
        ):
            raise Failed(f"{arm} first shot must be byte-identical to {sub}")
    if first_user("loop_cot", case) != first_user("loop_cot", case, rag_block=""):
        raise Failed("cot first shot must not depend on rag_block")


def test_loop_family_engine() -> None:
    """loop_X keeps the adaptive EFx3 schedule: enhanced first shot, plain feedback after."""
    import exp.common.baseline.loop as loop_mod
    from exp.common.baseline.loop import run_base_task

    retrieve_calls = []

    def fake_retrieve(case):
        retrieve_calls.append(case.get("case_id"))
        return ("<retrieved_knowledge>doc</retrieved_knowledge>", {"backend": "TEST", "n_docs": 1})

    def fake_grade(case, code, *, bench, results_root, tag, k, case_id=""):
        return {"passed": k == 3, "error_type": "" if k == 3 else "RuntimeError",
                "error_message": "" if k == 3 else "boom"}

    orig = loop_mod._grade_case
    loop_mod._grade_case = fake_grade
    try:
        with tempfile.TemporaryDirectory() as td:
            row = run_base_task(
                "qiskitHumanEval/15",
                _FakeClient([_CODE_OK, _CODE_OK, _CODE_OK]),
                arm="loop_cot",
                bench="qhe",
                tag="e4_base_v8_loop_cot_selftest",
                results_root=Path(td),
            )
        with tempfile.TemporaryDirectory() as td:
            row_rag = run_base_task(
                "qiskitHumanEval/15",
                _FakeClient([_CODE_OK, _CODE_OK, _CODE_OK]),
                arm="loop_rag",
                bench="qhe",
                tag="e4_base_v7_loop_rag_selftest",
                results_root=Path(td),
                retrieve_fn=fake_retrieve,
            )
    finally:
        loop_mod._grade_case = orig

    if row["sampling_mode"] != "adaptive_feedback" or row["pass_k"] != 1:
        raise Failed((row["sampling_mode"], row["pass_k"]))
    if row["first_shot_prompt"] != "cot":
        raise Failed(row["first_shot_prompt"])
    if row["official_attempts"] != 3 or not row["passed"]:
        raise Failed((row["official_attempts"], row["passed"]))
    # rounds 2-3 must carry the official QuanBench+ feedback template
    # (attempt framing + error + repair instruction + code echo), no cot text
    for j in (1, 2):
        hist = row["messages_head"][2 * j]  # user turn of round j+1
        for marker in (
            f"failed on attempt {j} of 3.",
            "Error from execution / transpilation:",
            "boom",
            "Fix the implementation and respond with corrected Python code only",
            "Your previous code (for reference):",
        ):
            if marker not in hist["content"]:
                raise Failed(f"round {j + 1} must use the official template ({marker})")
        if "think step by step" in hist["content"].lower():
            raise Failed("feedback rounds must not re-inject the cot instruction")
    # rag flavor: retrieval exactly once, injected into the first shot only
    if retrieve_calls != ["qiskitHumanEval/15"]:
        raise Failed(retrieve_calls)
    if row_rag["first_shot_prompt"] != "rag" or "retrieved_knowledge" not in row_rag["messages_head"][0]["content"]:
        raise Failed("loop_rag first shot must carry the retrieved block")
    if "retrieved_knowledge" in row_rag["messages_head"][2]["content"]:
        raise Failed("feedback rounds must not re-inject retrieval")
    if row_rag.get("rag", {}).get("backend") != "TEST":
        raise Failed(row_rag.get("rag"))


def test_ragflow_gate() -> str:
    from exp.rag.retrieve import RagFlowUnavailable, require_ragflow

    try:
        meta = require_ragflow()
    except RagFlowUnavailable as exc:
        return f"FAIL {exc}"
    if not meta.get("ids") and meta.get("n_docs", 0) <= 0:
        return f"FAIL empty {meta}"
    return f"PASS backend={meta.get('backend')} n={meta.get('n_docs')}"


def main() -> int:
    tests = [
        ("model_and_tags", test_model_and_tags),
        ("prompts", test_prompts),
        ("feedback", test_feedback),
        ("grader_python", test_grader_python),
        ("load_cases", test_load_cases),
        ("parse_extraction", test_parse_extraction),
        ("parse_v3_prototype", test_parse_v3_prototype),
        ("passk_engine", test_passk_engine),
        ("passk_summary", test_passk_summary),
        ("loop_first_shot", test_loop_first_shot),
        ("loop_family_engine", test_loop_family_engine),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}", flush=True)
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"FAIL {name}: {type(exc).__name__}: {exc}", flush=True)
    rag_line = test_ragflow_gate()
    print(f"RAGFLOW {rag_line}", flush=True)
    print(f"{len(tests) - len(failed)}/{len(tests)} core passed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
