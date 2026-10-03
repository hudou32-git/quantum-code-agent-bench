"""MECH-1 A / D1: resolved-contract probe (ApiProbe).

Answers exactly the question the QHE ENV residuals failed on: *which class
does the installed environment actually resolve for this name, what is its
constructor contract, and does a minimal instantiation work*. Read-only
introspection of installed packages; never touches dataset/sealed/grader
files; standard probe caps + canary.
"""
from __future__ import annotations

import re
from typing import Any

from exp.common.canary import scan_text
from exp.eqpa.bwrap import run_sandboxed, SandboxError

from exp.fcea import config as fcfg
from exp.fcea.control.mech_flags import MECH_CONSTANTS

_TARGET_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,%d}$"
                        % MECH_CONSTANTS["api_probe_target_max_len"])

_API_PROBE_TEMPLATE = (
    "import importlib, inspect, json\n"
    "t = {target!r}\n"
    "out = {'target': t}\n"
    "try:\n"
    "    mod_path, _, attr = t.rpartition('.')\n"
    "    if not mod_path:\n"
    "        out['error'] = 'need a dotted path like pkg.mod.Class'\n"
    "    else:\n"
    "        obj = getattr(importlib.import_module(mod_path), attr)\n"
    "        out['resolved_module'] = getattr(obj, '__module__', '?')\n"
    "        out['qualname'] = getattr(obj, '__qualname__', '?')\n"
    "        try:\n"
    "            out['signature'] = str(inspect.signature(obj))[:200]\n"
    "        except (TypeError, ValueError):\n"
    "            out['signature'] = None\n"
    "        try:\n"
    "            obj()\n"
    "            out['no_arg'] = 'OK'\n"
    "        except Exception as ex:\n"
    "            out['no_arg'] = type(ex).__name__ + ': ' + str(ex)[:100]\n"
    "except Exception as ex:\n"
    "    out['error'] = type(ex).__name__ + ': ' + str(ex)[:120]\n"
    "print(json.dumps(out))\n"
)


def valid_target(target: str) -> bool:
    return bool(_TARGET_RE.match(target or ""))


# Frozen candidate modules for resolving bare class tokens (protocol §3);
# ordered by hit likelihood in the QHE ENV residual set (2026-09-30 analysis).
_CANDIDATE_MODULES = (
    "qiskit_ibm_runtime",
    "qiskit.primitives",
    "qiskit_aer.primitives",
    "qiskit.circuit",
    "qiskit.circuit.library",
    "qiskit.quantum_info",
    "qiskit.transpiler",
    "qiskit",
)


def resolve_targets(token: str) -> list[str]:
    """Dotted-path candidates for a bare API token (e.g. SamplerV2)."""
    token = (token or "").strip()
    if not token or not valid_target(token):
        return []
    if "." in token:
        return [token]
    return [f"{mod}.{token}" for mod in _CANDIDATE_MODULES]


def api_probe_script(target: str) -> str:
    """Frozen probe program for one dotted target (pure; selftest-checked)."""
    if not valid_target(target):
        raise ValueError(f"invalid ApiProbe target: {target!r}")
    return _API_PROBE_TEMPLATE.replace("{target!r}", repr(target))


def api_probe_command(target: str) -> str:
    return "python -c " + _shell_quote(api_probe_script(target))


def run_api_probe(target: str, *, session: Any) -> dict[str, Any]:
    """Execute one contract probe in the episode sandbox."""
    if not valid_target(target):
        return {"ok": False, "target": target, "text": "invalid target"}
    cmd = api_probe_command(target)
    try:
        obs = run_sandboxed(cmd, jail=session.host_dir,
                            timeout=fcfg.PROBE_TIMEOUT_S,
                            max_bytes=fcfg.PROBE_MAX_CHARS)
    except SandboxError as exc:
        return {"ok": False, "target": target,
                "text": f"api probe blocked: {exc}"}
    out = obs.get("text") or ""
    if scan_text(out):
        return {"ok": False, "target": target,
                "text": "api probe blocked by canary"}
    return {"ok": bool(obs.get("ok")), "target": target,
            "text": out[:400]}


def auto_probe_block(result: dict[str, Any]) -> str:
    """[auto contract probe] block injected with the failure feedback (D1)."""
    return ("\n[auto contract probe — resolved contract of the failing API, "
            "harness-provided]\n" + (result.get("text") or "")[:400])


def _shell_quote(script: str) -> str:
    return "'" + script.replace("'", "'\\''") + "'"


# Tool spec for the ApiProbe surface (MECH-1 A; schema mirrors BATCH_TOOL)
API_PROBE_TOOL = {
    "type": "function",
    "function": {
        "name": "ApiProbe",
        "description": (
            "Resolve one API name against the INSTALLED environment and return "
            "its actual module, constructor signature, and a no-argument "
            "instantiation result. Use before constructing primitives/classes "
            "you are not 100% sure about (versions differ from training data). "
            "Give a dotted path, e.g. qiskit_ibm_runtime.SamplerV2."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Dotted path of the class/function to inspect",
                },
            },
            "required": ["target"],
        },
    },
}
