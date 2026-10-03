"""QHE main-table grader.

2026-09-19 GRADER UNIFICATION (user directive): run_candidate spawns the conda
qhe interpreter (config.QHE_PYTHON, qiskit 2.4.1) per attempt via
exp/common/eval_qhe.py — the SAME environment as the 2026-09-17 canonical full
verification (README §4: QHE local_hard 143/143, QB+ 42/42 under conda qhe) and
the same interpreter QB+ grading and EQPA's blind eval already use. Before this
change QHE grading ran in-process under the runner interpreter (system
python3.8, qiskit 1.2.4); that exact path is preserved as
run_candidate_system_python / env QHE_GRADER_INPROCESS=1 so the frozen
1.2.4-era rows (every tag collected before 2026-09-19) stay reproducible.
Rows graded under the two environments must never be mixed in one column.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import subprocess
import tempfile
import traceback
from pathlib import Path
from typing import Any

GRADER_INPROCESS_ENV = "QHE_GRADER_INPROCESS"  # set to "1" for the legacy 1.2.4 in-process path
EVAL_QHE_SCRIPT = Path(__file__).resolve().parent / "eval_qhe.py"


def looks_like_full_module(code: str) -> bool:
    head = (code or "").lstrip()
    # Code-first statements a complete module may start with. Historical rows
    # all start with from/import/def (v1 extractor gate); try:/class/@/str
    # widenings only affect modules the old gate misclassified as prose.
    return head.startswith(
        ("from ", "import ", "def ", "class ", "try:", "try\n", "@", '"', "'")
    )


def extract_python(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            p = part.strip()
            first = p.split("\n", 1)[0].strip().lower()
            if first in {"python", "py", "qiskit"}:
                body = p.split("\n", 1)[1] if "\n" in p else ""
                if "def " in body or "import " in body:
                    return body.strip()
            elif "def " in p or p.startswith("from ") or p.startswith("import "):
                return p
    return text


def assemble_program(code: str, test: str, prompt: str) -> str:
    code = (code or "").rstrip() + "\n"
    test = test or ""
    if looks_like_full_module(code) and "def " in code:
        return code + test
    return (prompt or "").rstrip() + "\n" + code + test


# Uniform 60s for all tasks (user directive, 2026-09-16), with one exception:
# task 100 (Solovay-Kitaev, ~106s measured) rides the official 120s pin from
# bench/qhe/eval/evaluate_completions.py; 96/108 stay at the uniform 60s.
TASK_TIMEOUT_OVERRIDES: dict[str, float] = {
    "qiskitHumanEval/100": 120.0,
}


def run_candidate(
    *,
    code: str,
    test: str,
    entry: str,
    prompt: str = "",
    timeout: float = 60.0,
    case_id: str = "",
) -> dict[str, Any]:
    if case_id:
        timeout = max(float(timeout), TASK_TIMEOUT_OVERRIDES.get(str(case_id), 0.0))
    if os.environ.get(GRADER_INPROCESS_ENV) == "1":
        return run_candidate_system_python(
            code=code, test=test, entry=entry, prompt=prompt, timeout=timeout, case_id=case_id,
        )
    program = assemble_program(code, test, prompt)
    from exp import config

    tmp = Path(tempfile.mkdtemp(prefix="qhe_eval_"))
    prog_path = tmp / "program.py"
    out_path = tmp / "result.json"
    prog_path.write_text(program, encoding="utf-8")
    cmd = [
        str(config.QHE_PYTHON),
        str(EVAL_QHE_SCRIPT),
        "--program", str(prog_path),
        "--entry", str(entry),
        "--out", str(out_path),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(config.ROOT)
    try:
        subprocess.run(
            cmd, capture_output=True, text=True, timeout=float(timeout),
            cwd=str(config.ROOT), env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "error_type": "Timeout",
            "error_message": f"Execution timeout ({timeout}s)",
            "traceback": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "error_type": "ProcessError",
            "error_message": f"eval spawn failed: {type(exc).__name__}: {exc}",
            "traceback": "",
        }
    if not out_path.is_file():
        return {
            "passed": False,
            "error_type": "ProcessError",
            "error_message": "Worker exited without result",
            "traceback": "",
        }
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "passed": False,
            "error_type": "ProcessError",
            "error_message": "Worker result unreadable",
            "traceback": "",
        }
    return {
        "passed": bool(payload.get("passed")),
        "error_type": str(payload.get("error_type") or ""),
        "error_message": str(payload.get("error_message") or ""),
        "traceback": str(payload.get("traceback") or ""),
    }


def run_candidate_system_python(
    *,
    code: str,
    test: str,
    entry: str,
    prompt: str = "",
    timeout: float = 60.0,
    case_id: str = "",
) -> dict[str, Any]:
    """Legacy in-process path (system python3.8 + qiskit 1.2.4) — the exact
    grader that produced every QHE row frozen before 2026-09-19. Kept verbatim
    so those rows remain reproducible; do not use for new main-table rows."""
    if case_id:
        timeout = max(float(timeout), TASK_TIMEOUT_OVERRIDES.get(str(case_id), 0.0))
    program = assemble_program(code, test, prompt)
    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_worker, args=(program, entry, q))
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        return {
            "passed": False,
            "error_type": "Timeout",
            "error_message": f"Execution timeout ({timeout}s)",
            "traceback": "",
        }
    try:
        item = q.get_nowait()
        return item
    except Exception:
        return {
            "passed": False,
            "error_type": "ProcessError",
            "error_message": "Worker exited without result",
            "traceback": "",
        }


def _worker(program: str, entry: str, q: mp.Queue) -> None:
    try:
        ns: dict[str, Any] = {}
        exec(compile(program, "<k0>", "exec"), ns, ns)
        if entry not in ns:
            q.put(
                {
                    "passed": False,
                    "error_type": "MissingEntryPoint",
                    "error_message": f'Entry point "{entry}" not defined',
                    "traceback": "",
                }
            )
            return
        if "check" not in ns:
            q.put(
                {
                    "passed": False,
                    "error_type": "MissingTest",
                    "error_message": 'Test block did not define "check"',
                    "traceback": "",
                }
            )
            return
        ns["check"](ns[entry])
        q.put({"passed": True, "error_type": "", "error_message": "", "traceback": ""})
    except Exception as exc:
        q.put(
            {
                "passed": False,
                "error_type": type(exc).__name__,
                "error_message": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        )


def run_blind_eval(*, completion, out, case_id: str, timeout: float = 90.0) -> dict[str, Any]:
    """Run the frozen blind grader (bench/qhe/eval/eval_blind.py) on one attempt.

    Spawns QHE_PYTHON with cwd=bench/qhe so the grader resolves sealed files
    relative to the benchmark root. Returns {ok, passed, error, text, code}.
    """
    import json
    import subprocess
    from pathlib import Path

    from exp import config

    completion = Path(completion)
    out = Path(out)
    if not completion.is_file():
        return {
            "ok": False,
            "kind": "eval_blind",
            "official_eval": True,
            "passed": False,
            "error": f"missing file {completion}",
            "text": f"eval_blind: missing file {completion}",
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                str(config.QHE_PYTHON),
                str(config.EVAL_BLIND),
                "--task-id",
                str(case_id),
                "--completion",
                str(completion),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(config.QHE_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "kind": "eval_blind",
            "official_eval": True,
            "passed": False,
            "error": f"Execution timeout ({timeout}s)",
            "text": "eval_blind timeout",
        }
    payload = {}
    if out.is_file():
        try:
            payload = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    passed = bool(payload.get("passed"))
    err = str(payload.get("error") or "")
    text = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    text = text.strip() or json.dumps(payload, ensure_ascii=False)
    return {
        "ok": passed,
        "kind": "eval_blind",
        "official_eval": True,
        "passed": passed,
        "error": err,
        "text": text[:4000],
        "code": completion.read_text(encoding="utf-8"),
    }
