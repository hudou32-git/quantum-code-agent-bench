"""MECH-1 B: L1 preflight gate before Eval (non-official).

Executes the candidate module in the episode sandbox exactly like the grader
would (compile+exec, no hidden tests attached). A preflight failure returns a
traceback to the model as NON-official feedback: it does not consume an
official attempt, does not write a shot row, and is counted separately
(`preflight_rejects`, additive episode field). L2 (introspected entry
invocation) is reserved behind `mech_preflight_l2` (default False).
"""
from __future__ import annotations

import json
import re
from typing import Any

from exp.common.canary import scan_text
from exp.eqpa.bwrap import run_sandboxed, SandboxError

from exp.fcea import config as fcfg
from exp.fcea.control.mech_flags import MECH_CONSTANTS

_FILENAME_RE = re.compile(r"^attempt_\d+\.py$")

_TEMPLATE = (
    "import json\n"
    "src = open({filename!r}, encoding='utf-8').read()\n"
    "try:\n"
    "    exec(compile(src, '<preflight>', 'exec'), {}, {})\n"
    "    print(json.dumps({'ok': True}))\n"
    "except Exception as ex:\n"
    "    import traceback\n"
    "    tb = traceback.format_exc(limit=3)\n"
    "    print(json.dumps({'ok': False,\n"
    "                       'error': type(ex).__name__ + ': ' + str(ex)[:150],\n"
    "                       'tb': tb[-400:]}))\n"
)


def valid_filename(filename: str) -> bool:
    return bool(_FILENAME_RE.match(filename or ""))


def preflight_script(filename: str) -> str:
    """Frozen preflight program (pure; selftest-checked)."""
    if not valid_filename(filename):
        raise ValueError(f"invalid preflight filename: {filename!r}")
    # NOTE: .replace, not .format — the filename repr is substituted
    # verbatim; braces in the template are literal Python dicts.
    return _TEMPLATE.replace("{filename!r}", repr(filename))


def preflight_command(filename: str) -> str:
    return "python -c " + _shell_quote(preflight_script(filename))


def run_preflight(filename: str, *, session: Any) -> dict[str, Any]:
    """Run L1 preflight. Outcome is three-valued:
      passed        — module compiled and executed cleanly
      failed        — the runner JSON reported an exception (positive signal)
      indeterminate — sandbox/blocked/timeout/invalid-JSON (no signal; the
                      caller must FAIL OPEN and let the official Eval proceed)
    """
    if not valid_filename(filename):
        return {"outcome": "indeterminate", "error": "invalid filename"}
    cmd = preflight_command(filename)
    try:
        obs = run_sandboxed(cmd, jail=session.host_dir,
                            timeout=MECH_CONSTANTS["preflight_timeout_s"],
                            max_bytes=fcfg.PROBE_MAX_CHARS)
    except SandboxError as exc:
        return {"outcome": "indeterminate", "error": f"preflight blocked: {exc}"}
    out = obs.get("text") or ""
    if scan_text(out):
        return {"outcome": "indeterminate", "error": "preflight blocked by canary"}
    # the runner prints exactly one json line; sandbox noise (if any) may
    # precede it — take the last line that parses
    parsed = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if parsed is None:
        return {"outcome": "indeterminate",
                "error": f"no runner json (exit={obs.get('exit_code')})",
                "output": out[:400]}
    if parsed.get("ok") is True:
        return {"outcome": "passed"}
    return {"outcome": "failed",
            "error": str(parsed.get("error") or "")[:200],
            "tb": str(parsed.get("tb") or "")[-400:]}


def preflight_feedback_block(result: dict[str, Any]) -> str:
    """Feedback text for a rejected Eval (non-official, attempt preserved)."""
    body = (str(result.get("tb") or "") or str(result.get("error") or "")
            or str(result.get("output") or ""))
    return ("[preflight — non-official check, this attempt was NOT consumed]\n"
            "The candidate module failed to execute standalone:\n" + body[:400])


def _shell_quote(script: str) -> str:
    return "'" + script.replace("'", "'\\''") + "'"
