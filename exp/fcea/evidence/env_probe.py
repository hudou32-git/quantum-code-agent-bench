"""MECH-1 E: fixed environment probe, executed once at episode start.

Harness-initiated (no system-prompt change, no LLM call): the script below is
frozen text — it reads ONLY the installed environment (versions + resolved
primitive classes + constructor signatures + a no-arg instantiation attempt).
It never touches dataset/sealed/grader files; output passes the canary scan
and the standard 8s/900-char probe caps.
"""
from __future__ import annotations

import json
from typing import Any

from exp.common.canary import scan_text
from exp.eqpa.bwrap import run_sandboxed, SandboxError

from exp.fcea import config as fcfg

TARGETS = [
    "qiskit.primitives.Sampler",
    "qiskit.primitives.StatevectorSampler",
    "qiskit_ibm_runtime.Sampler",
    "qiskit_ibm_runtime.SamplerV2",
    "qiskit_ibm_runtime.EstimatorV2",
    "qiskit_aer.primitives.Sampler",
]

_ENV_PROBE_TEMPLATE = (
    "import importlib, inspect, json\n"
    "out = {}\n"
    "for mod in ('qiskit', 'qiskit_aer', 'qiskit_ibm_runtime'):\n"
    "    try:\n"
    "        out['ver:' + mod] = importlib.import_module(mod).__version__\n"
    "    except Exception as ex:\n"
    "        out['ver:' + mod] = 'ERR:' + type(ex).__name__\n"
    "targets = {t}\n"
    "for t in targets:\n"
    "    try:\n"
    "        mod_path, _, attr = t.rpartition('.')\n"
    "        obj = getattr(importlib.import_module(mod_path), attr)\n"
    "        out[t] = {'module': getattr(obj, '__module__', '?'),\n"
    "                  'sig': str(inspect.signature(obj))[:160]}\n"
    "        try:\n"
    "            obj()\n"
    "            out[t]['no_arg'] = 'OK'\n"
    "        except Exception as ex:\n"
    "            out[t]['no_arg'] = type(ex).__name__ + ': ' + str(ex)[:80]\n"
    "    except Exception as ex:\n"
    "        out[t] = 'RESOLVE_ERR:' + type(ex).__name__\n"
    "print(json.dumps(out))\n"
)


def env_probe_script(targets: list[str] | None = None) -> str:
    """Frozen probe program (pure; selftest asserts determinism)."""
    ts = targets if targets is not None else TARGETS
    repr_list = "[" + ", ".join(repr(t) for t in ts) + "]"
    # NOTE: .replace, not .format — braces in the template are literal
    # Python dicts/lists; only the {t} placeholder is substituted.
    return _ENV_PROBE_TEMPLATE.replace("{t}", repr_list)


def run_env_probe(*, session: Any) -> dict[str, Any]:
    """Execute the frozen environment probe in the episode sandbox."""
    cmd = "python -c " + _shell_quote(env_probe_script())
    try:
        obs = run_sandboxed(cmd, jail=session.host_dir,
                            timeout=fcfg.PROBE_TIMEOUT_S,
                            max_bytes=fcfg.PROBE_MAX_CHARS)
    except SandboxError as exc:
        return {"ok": False, "text": f"env probe blocked: {exc}"}
    out = obs.get("text") or ""
    status = "ok" if obs.get("ok") else (obs.get("reason") or "nonzero exit")
    if scan_text(out):
        return {"ok": False, "text": "env probe blocked by canary"}
    return {"ok": bool(obs.get("ok")), "status": status, "text": out[:400]}


def env_probe_block(result: dict[str, Any]) -> str:
    """[environment probe] block injected after the first task message (E)."""
    return ("\n[environment probe — installed runtime facts, harness-provided]\n"
            + (result.get("text") or "")[:400])


def _shell_quote(script: str) -> str:
    return "'" + script.replace("'", "'\\''") + "'"
