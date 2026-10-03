"""rq4b A16 L1/L2: forced contract probe runner (harness-side, zero model
compliance dependence).

At a trigger boundary (L1) and before an armed official Eval (L2) the
harness executes the candidate's entry function inside the episode sandbox
with a frozen dummy-argument ladder and describes the returned artifact.
Structure mirrors MECH-1's control/preflight.py (tri-state skeleton) and
evidence/contract_probe.py (sandbox execution); the probe never touches
dataset/sealed/grader files and never performs the official check itself —
the L2 verdict only gates whether the official Eval may run.

Frozen constants live in control/rq4b.py (TRACE_*); any byte change to the
template below = A16 protocol amendment + re-pilot.
"""
from __future__ import annotations

import json
import re
from typing import Any

from exp.common.canary import scan_text
from exp.eqpa.bwrap import run_sandboxed, SandboxError

from exp.fcea import config as fcfg
from exp.fcea.control import rq4b as rqb

_FILENAME_RE = re.compile(r"^attempt_\d+\.py$")

# The runner prints exactly one JSON line. Phases:
#   import     — the attempt module could not be imported        -> indeterminate
#   entry      — entry missing/not callable/sig unreadable       -> indeterminate
#   construct  — every ladder rung raised TypeError              -> indeterminate
#   call       — a constructed rung raised a non-TypeError       -> failed (crash)
#   artifact   — entry returned; artifact described              -> compare vs body
# Substitution is .replace (preflight pattern): the filename/entry reprs are
# inserted verbatim; every brace below is a literal Python brace.
_TRACE_PROBE_TEMPLATE = (
    "import importlib, inspect, itertools, json, sys\n"
    "MOD, ENTRY = {mod!r}, {entry!r}\n"
    "out = {}\n"
    "def _ladder(ann):\n"
    "    name = ann if isinstance(ann, str) else getattr(ann, '__name__', None)\n"
    "    typed = list({typed!r}.get(str(name), ()))\n"
    "    return typed + list({generic!r})\n"
    "def _describe(a):\n"
    "    tn = type(a).__name__\n"
    "    try:\n"
    "        import qiskit\n"
    "        if isinstance(a, qiskit.QuantumCircuit):\n"
    "            ops = a.count_ops()\n"
    "            return {'kind': 'QuantumCircuit', 'num_qubits': int(a.num_qubits),\n"
    "                    'count_ops': {str(k): int(v) for k, v in\n"
    "                                  list(ops.items())[:12]}}\n"
    "    except Exception:\n"
    "        pass\n"
    "    if isinstance(a, bool) or a is None:\n"
    "        return {'kind': 'scalar', 'type': tn,\n"
    "                'value': None if a is None else bool(a)}\n"
    "    if isinstance(a, (int, float)):\n"
    "        return {'kind': 'scalar', 'type': tn, 'value': a}\n"
    "    if isinstance(a, str):\n"
    "        return {'kind': 'scalar', 'type': 'str', 'value': a[:40]}\n"
    "    if isinstance(a, (list, tuple)):\n"
    "        return {'kind': 'sequence', 'type': tn, 'len': len(a),\n"
    "                'first_type': (type(a[0]).__name__ if len(a) else None)}\n"
    "    try:\n"
    "        if getattr(a, 'ndim', 0) >= 1:\n"
    "            return {'kind': 'sequence', 'type': tn, 'len': int(a.shape[0]),\n"
    "                    'first_type': (type(a[0]).__name__ if a.shape[0] else None)}\n"
    "    except Exception:\n"
    "        pass\n"
    "    if isinstance(a, dict):\n"
    "        return {'kind': 'dict', 'type': tn, 'n_keys': len(a),\n"
    "                'keys': sorted(str(k) for k in list(a.keys())[:24])[:12]}\n"
    "    for attr in ('__struct_fields__', '_fields'):\n"
    "        if hasattr(a, attr):\n"
    "            try:\n"
    "                return {'kind': 'container', 'type': tn,\n"
    "                        'fields': [str(f) for f in getattr(a, attr)][:12]}\n"
    "            except Exception:\n"
    "                pass\n"
    "    try:\n"
    "        import dataclasses\n"
    "        if dataclasses.is_dataclass(a):\n"
    "            return {'kind': 'container', 'type': tn,\n"
    "                    'fields': [f.name for f in dataclasses.fields(a)][:12]}\n"
    "    except Exception:\n"
    "        pass\n"
    "    try:\n"
    "        return {'kind': 'other', 'type': tn, 'repr': repr(a)[:120]}\n"
    "    except Exception:\n"
    "        return {'kind': 'other', 'type': tn, 'repr': '<unrepr>'}\n"
    "try:\n"
    "    if '.' not in sys.path:\n"
    "        sys.path.insert(0, '.')\n"
    "    mod = importlib.import_module(MOD)\n"
    "except Exception as ex:\n"
    "    out['phase'] = 'import'\n"
    "    out['error'] = type(ex).__name__ + ': ' + str(ex)[:150]\n"
    "    print(json.dumps(out))\n"
    "    raise SystemExit(0)\n"
    "fn = getattr(mod, ENTRY, None)\n"
    "if not callable(fn):\n"
    "    out['phase'] = 'entry'\n"
    "    out['error'] = 'entry not callable: ' + ENTRY\n"
    "    print(json.dumps(out))\n"
    "    raise SystemExit(0)\n"
    "try:\n"
    "    sig = inspect.signature(fn)\n"
    "    slots = []\n"
    "    for p in sig.parameters.values():\n"
    "        if (p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)\n"
    "                and p.default is p.empty):\n"
    "            slots.append(_ladder(p.annotation))\n"
    "        elif p.kind == p.VAR_POSITIONAL:\n"
    "            slots.append(_ladder(None))\n"
    "        elif p.kind == p.KEYWORD_ONLY and p.default is p.empty:\n"
    "            slots.append(_ladder(p.annotation))\n"
    "    combos = list(itertools.product(*slots))[:{max_combos}] if slots else [()]\n"
    "except Exception as ex:\n"
    "    out['phase'] = 'entry'\n"
    "    out['error'] = 'signature: ' + type(ex).__name__ + ': ' + str(ex)[:120]\n"
    "    print(json.dumps(out))\n"
    "    raise SystemExit(0)\n"
    "_SENTINEL = object()\n"
    "result = _SENTINEL\n"
    "last_err = None\n"
    "crashed = False\n"
    "for combo in combos:\n"
    "    try:\n"
    "        result = fn(*combo)\n"
    "        last_err = None\n"
    "        break\n"
    "    except TypeError as te:\n"
    "        last_err = te\n"
    "    except Exception as ex:\n"
    "        last_err = ex\n"
    "        crashed = True\n"
    "        break\n"
    "if crashed:\n"
    "    out['phase'] = 'call'\n"
    "    out['error'] = type(last_err).__name__ + ': ' + str(last_err)[:150]\n"
    "elif result is _SENTINEL:\n"
    "    out['phase'] = 'construct'\n"
    "    out['error'] = ((type(last_err).__name__ + ': ' + str(last_err)[:150])\n"
    "                    if last_err is not None else 'no ladder rung produced a call')\n"
    "else:\n"
    "    out['phase'] = 'artifact'\n"
    "    out['artifact'] = _describe(result)\n"
    "print(json.dumps(out))\n"
)


def valid_filename(filename: str) -> bool:
    return bool(_FILENAME_RE.match(filename or ""))


def trace_probe_script(filename: str, entry: str) -> str:
    """Frozen probe program (pure; selftest-checked byte-for-byte)."""
    if not valid_filename(filename):
        raise ValueError(f"invalid trace probe filename: {filename!r}")
    entry = (entry or "").strip()
    if not entry or not entry.isidentifier():
        raise ValueError(f"invalid trace probe entry: {entry!r}")
    body = (_TRACE_PROBE_TEMPLATE
            .replace("{mod!r}", repr(filename[:-3]))
            .replace("{entry!r}", repr(entry))
            .replace("{typed!r}", repr(rqb.TRACE_TYPED_DUMMIES))
            .replace("{generic!r}", repr(rqb.TRACE_DUMMY_LADDER))
            .replace("{max_combos}", str(rqb.TRACE_MAX_CALL_COMBOS)))
    return body


def trace_probe_command(filename: str, entry: str) -> str:
    return "python -c " + _shell_quote(trace_probe_script(filename, entry))


def run_trace_probe(filename: str, *, entry: str, session: Any) -> dict[str, Any]:
    """Execute the probe in the episode sandbox. Returns a raw probe record:
      {status: ok|blocked, phase: import|entry|construct|call|artifact,
       error?: str, artifact?: dict, blocked_reason?: str}
    Tri-state classification happens in classify_probe (frozen, pure)."""
    if not valid_filename(filename):
        return {"status": "blocked", "phase": "invalid",
                "blocked_reason": f"invalid filename {filename!r}"}
    try:
        cmd = trace_probe_command(filename, entry)
    except ValueError as exc:
        return {"status": "blocked", "phase": "invalid",
                "blocked_reason": str(exc)}
    try:
        obs = run_sandboxed(cmd, jail=session.host_dir,
                            timeout=rqb.TRACE_TIMEOUT_S,
                            max_bytes=fcfg.PROBE_MAX_CHARS)
    except SandboxError as exc:
        return {"status": "blocked", "phase": "invalid",
                "blocked_reason": f"trace probe blocked: {exc}"}
    out = obs.get("text") or ""
    if scan_text(out):
        return {"status": "blocked", "phase": "invalid",
                "blocked_reason": "trace probe blocked by canary"}
    reason = str(obs.get("reason") or "")
    if "timeout" in reason:
        return {"status": "blocked", "phase": "invalid",
                "blocked_reason": reason}
    parsed = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if not isinstance(parsed, dict) or "phase" not in parsed:
        return {"status": "blocked", "phase": "invalid",
                "blocked_reason": "no runner json ("
                                  + (reason or "exit=" + str(obs.get("exit_code")))
                                  + ")"}
    parsed["status"] = "ok"
    return parsed


def classify_probe(probe: dict, expected: float | None,
                   body: str | None = None) -> tuple[str, str]:
    """Frozen L2 tri-state (PROTOCOL_rq4b_A16.md §3-L2 + pre-freeze guard
    2026-10-01). Returns (outcome, reason) with outcome in:
      failed        — the constructed call raised AssertionError, OR a
                      type-coherent parseable mismatch (expected N vs probe
                      value != N; collection lengths need a size-flavored body)
      indeterminate — non-assertion entry crash / no parseable expectation /
                      artifact not comparable / construction failure /
                      sandbox block or timeout (FAIL-OPEN by design)
      passed        — constructed artifact comparable and equal to expected
    """
    if probe.get("status") != "ok":
        return "indeterminate", str(probe.get("blocked_reason") or "blocked")
    phase = probe.get("phase")
    if phase == "call":
        err = str(probe.get("error") or "")
        if err.startswith("AssertionError"):
            return "failed", "entry crash: " + err[:150]
        return "indeterminate", "entry crash (non-assertion, dummy artifact): " + err[:130]
    if phase != "artifact":
        return "indeterminate", ("phase=" + str(phase)
                                 + (": " + str(probe.get("error") or "")[:120]
                                    if probe.get("error") else ""))
    artifact = probe.get("artifact")
    kind = artifact.get("kind") if isinstance(artifact, dict) else None
    value = rqb.probe_numeric_value(artifact if isinstance(artifact, dict) else None)
    if expected is None:
        return "indeterminate", "assertion body has no parseable expectation"
    if value is None:
        return "indeterminate", "artifact not numeric-comparable"
    if kind in ("sequence", "dict") and not rqb.TRACE_SIZE_HINT_RE.search(body or ""):
        return ("indeterminate",
                "collection artifact without size-flavored expectation")
    if rqb.mismatch(expected, value, body=body, artifact_kind=kind):
        return "failed", f"mismatch: expected {expected}, probe value {value}"
    return "passed", f"probe value {value} == expected {expected}"


def _shell_quote(script: str) -> str:
    return "'" + script.replace("'", "'\\''") + "'"
