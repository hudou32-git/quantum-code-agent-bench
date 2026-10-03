"""EQPA tools: Shell (OS sandbox) + Write (host, exact names) + Eval (privileged)."""

from __future__ import annotations

import os
import stat
from typing import Any

from exp import config
from exp.eqpa.bwrap import SandboxError, run_sandboxed
from exp.common.canary import scan_text
from exp.eqpa.jail import ALLOWED_ATTEMPTS, IsoSession

SHELL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Shell",
        "description": (
            "Run one shell command in the isolated evaluation environment and return stdout/stderr. "
            "cwd is /workspace (read-only). Scratch files go in /tmp. "
            "Python and Qiskit are available. Do not expect host repository paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                }
            },
            "required": ["command"],
        },
    },
}

WRITE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Write",
        "description": (
            "Write one complete Python module as this task's official attempt. "
            "path must be exactly attempt_1.py, attempt_2.py, or attempt_3.py. "
            "Then call Eval()."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Exact filename: attempt_1.py, attempt_2.py, or attempt_3.py.",
                },
                "contents": {
                    "type": "string",
                    "description": "Full module text (imports + entry-point function). No markdown fences.",
                },
            },
            "required": ["path", "contents"],
        },
    },
}

EVAL_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Eval",
        "description": (
            "Run the official hidden tests on the latest successful Write for this task. "
            "Returns passed and a short error string. No extra arguments required."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "k": {
                    "type": "integer",
                    "description": "Optional attempt index 1, 2, or 3. Default: last successful Write.",
                }
            },
        },
    },
}

EQPA_TOOLS = [SHELL_TOOL, WRITE_TOOL, EVAL_TOOL]


def workspace_block(*, case_id: str) -> str:
    return (
        "Workspace:\n"
        f"- task_id: {case_id}\n"
        "- visible files: /workspace/prompt.txt, /workspace/attempt_k.py (read-only)\n"
        "- inspect: Shell in the isolated environment (python and Qiskit are on PATH)\n"
        "- scratch: /tmp\n"
        "- submit: Write with path exactly attempt_1.py (or attempt_2.py / attempt_3.py), then Eval()\n"
        "- Eval() grades the last successful Write and returns {passed, error}"
    )


def _blocked(text: str) -> dict[str, Any]:
    return {"ok": False, "blocked": True, "text": text, "official_eval": False}


def run_write(*, path: str, contents: str, session: IsoSession) -> dict[str, Any]:
    name = (path or "").strip()
    if name not in ALLOWED_ATTEMPTS:
        return _blocked(
            "Write blocked: path must be exactly attempt_1.py, attempt_2.py, or attempt_3.py"
        )
    dest = session.attempt_path(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = os.lstat(dest)
    except FileNotFoundError:
        st = None
    if st is not None and stat.S_ISLNK(st.st_mode):
        return _blocked("Write blocked: destination is a symlink")
    if st is not None and not stat.S_ISREG(st.st_mode):
        return _blocked("Write blocked: destination is not a regular file")
    body = (contents or "").replace("\r\n", "\n")
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3]
    payload = (body.strip() + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        fd = os.open(str(dest), flags, 0o644)
    except OSError as exc:
        return _blocked(f"Write blocked: {exc}")
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    session.last_write_name = name
    session.written.add(name)
    return {
        "ok": True,
        "blocked": False,
        "text": f"wrote {name}",
        "path": name,
        "official_eval": False,
    }


def run_shell(command: str, *, session: IsoSession, scratch_host=None, timeout=None, max_bytes=None) -> dict[str, Any]:
    try:
        obs = run_sandboxed(
            command,
            jail=session.host_dir,
            scratch_host=scratch_host,
            timeout=timeout,
            max_bytes=max_bytes,
        )
    except SandboxError as exc:
        return _blocked(f"Shell blocked: {exc}")
    text = obs.get("text") or ""
    hits = scan_text(text)
    if hits:
        return {
            "ok": False,
            "blocked": True,
            "kind": "shell",
            "official_eval": False,
            "sandboxed": True,
            "canary_hits": len(hits),
            "text": "REPL blocked: sealed pattern in output",
            "raw_leaked": True,
        }
    return {
        "ok": bool(obs.get("ok")),
        "blocked": bool(obs.get("blocked")),
        "kind": "shell",
        "official_eval": False,
        "sandboxed": True,
        "text": text or "Shell: empty output",
        "exit_code": obs.get("exit_code"),
        "stdout": obs.get("stdout") or "",
        "stderr": obs.get("stderr") or "",
    }


def run_eval(*, session: IsoSession, k: int | None = None, grade_fn=None) -> dict[str, Any]:
    name = None
    if k is not None:
        name = f"attempt_{int(k)}.py"
        if name not in session.written:
            return {
                "ok": False,
                "blocked": False,
                "official_eval": False,
                "passed": False,
                "error": "Eval: no successful Write for that attempt",
                "text": "Eval: no successful Write for that attempt",
            }
    elif session.last_write_name:
        name = session.last_write_name
    else:
        return {
            "ok": False,
            "blocked": False,
            "official_eval": False,
            "passed": False,
            "error": "Eval: no successful Write yet",
            "text": "Eval: no successful Write yet",
        }
    path = session.attempt_path(name)
    if not path.is_file() or path.is_symlink():
        return {
            "ok": False,
            "blocked": False,
            "official_eval": False,
            "passed": False,
            "error": "Eval: attempt file missing",
            "text": "Eval: attempt file missing",
        }
    code = path.read_text(encoding="utf-8")
    if grade_fn is None:
        if not session.task_id.startswith("qiskitHumanEval/"):
            return {
                "ok": False,
                "blocked": False,
                "official_eval": False,
                "passed": False,
                "error": "synthetic task: no official tests",
                "text": "Eval: synthetic task: no official tests",
            }
        from exp.common.grader_qhe import run_blind_eval

        out_path = (
            session.host_dir.parent
            / "eval"
            / session.task_id.replace("/", "_")
            / f"{path.stem}_result.json"
        )
        raw = run_blind_eval(
            completion=path,
            out=out_path,
            case_id=session.task_id,
        )
        passed = bool(raw.get("passed"))
        err = _sanitize_eval_error(str(raw.get("error") or ""))
    else:
        exe = grade_fn(code)
        passed = bool(exe.get("passed"))
        err = _sanitize_eval_error(str(exe.get("error_message") or exe.get("error") or ""))
    text = _eval_observation(passed, err)
    if scan_text(text):
        err = "Eval error redacted"
        text = "REPL blocked: sealed pattern in output"
    return {
        "ok": passed,
        "blocked": False,
        "kind": "eval",
        "official_eval": True,
        "passed": passed,
        "error": err,
        "text": text[:4000],
        "path": name,
        "code": code,
    }


def _eval_observation(passed: bool, error: str) -> str:
    import json as _json

    return _json.dumps({"passed": bool(passed), "error": error or ""}, ensure_ascii=False)


def _sanitize_eval_error(text: str) -> str:
    if not text:
        return ""
    from exp.common.canary import canary_values

    out = text
    replacements = [
        str(config.ROOT),
        str(config.QHE_DATASET_DIR),
        str(config.QHE_SEALED_DIR),
        str(config.EVAL_BLIND),
        "/root/cyy/llm_code",
        *canary_values(),
    ]
    for needle in replacements:
        if needle:
            out = out.replace(needle, "[redacted]")
    return out
