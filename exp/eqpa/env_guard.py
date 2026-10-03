"""QHE grader-env guard: canary, preflight anti-pip/stub, import-error rewrite.

Default off in protocol. Does not change locked v2a prompt_hash unless qhe_env_guard=True.
Canary itself is a runner validity gate and is not model-facing.
"""

from __future__ import annotations

import ast
import re
import subprocess
import threading
from typing import Any

from exp import config

# Frozen model-facing strings. Changing them changes prompt_hash when guard is on.
PREFLIGHT_NO_PIP = (
    "preflight: do not pip install packages; the grader environment is fixed. "
    "Inspect installed APIs and fix the call."
)
PREFLIGHT_NO_STUB = (
    "preflight: do not stub sys.modules or invent fake qiskit packages. "
    "Inspect the live interpreter and fix the function body."
)
REWRITE_SUFFIX = (
    "\n\nThe official grader Python already has `{module}` installed"
    "{version_clause}. This is not a missing-package failure in the grader. "
    "Do not pip install, do not assign sys.modules stubs, and do not wrap that "
    "import in try/except to fake the package. Inspect the installed API "
    "(import / inspect.signature / dir) and fix the function body."
)

# Same restricted builtins as eval_blind's child exec.
_CANARY_PY = r"""
import builtins as _b
blocked = {"exec", "eval", "compile", "breakpoint", "input"}
ns = {"__builtins__": {k: v for k, v in vars(_b).items() if k not in blocked}}
src = (
    "import qiskit\n"
    "import qiskit_aer\n"
    "import qiskit_ibm_runtime\n"
    "from qiskit_ibm_runtime import Sampler\n"
    "from qiskit_ibm_runtime.fake_provider import FakeOslo\n"
    "_ = FakeOslo()\n"
    "print('qiskit', qiskit.__version__)\n"
    "print('aer', qiskit_aer.__version__)\n"
    "print('ibm_runtime', qiskit_ibm_runtime.__version__)\n"
    "print('sampler', Sampler.__module__ + '.' + Sampler.__name__)\n"
    "print('fake_oslo', FakeOslo.__module__ + '.' + FakeOslo.__name__)\n"
)
exec(src, ns)
"""

_MISSING_MODULE_RE = re.compile(
    r"No module named ['\"](?P<mod>[A-Za-z0-9_.]+)['\"]",
    re.IGNORECASE,
)
_PIP_TEXT_RE = re.compile(
    r"""(?:python\s+-m\s+pip|\bpip3?\b|\bsys\.executable\b).{0,80}\binstall\b""",
    re.IGNORECASE | re.DOTALL,
)
_QISKIT_MOD_RE = re.compile(r"^qiskit(?:_|$)")

_LOCK = threading.Lock()
_CANARY_CACHE: dict[str, Any] | None = None

LOCKED_GUARD_TAGS = frozenset(
    {
    }
)


class GraderRuntimeError(RuntimeError):
    """Eval Python cannot import the QHE runtime stack. Refuse to start the job."""


def canary_probe(*, python: str | None = None, timeout: float = 60.0) -> dict[str, Any]:
    """Run the grader-import canary in eval Python with restricted builtins."""
    py = str(python or config.QHE_PYTHON)
    try:
        proc = subprocess.run(
            [py, "-c", _CANARY_PY],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "python": py,
            "error": f"{type(exc).__name__}: {exc}",
            "versions": {},
        }
    versions: dict[str, str] = {}
    for line in (proc.stdout or "").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            versions[parts[0]] = parts[1]
    ok = proc.returncode == 0 and "ibm_runtime" in versions and "sampler" in versions
    err = ""
    if not ok:
        err = ((proc.stderr or proc.stdout or "") or f"exit {proc.returncode}").strip()[:1500]
        if "No module named 'qiskit_ibm_runtime'" in err or "qiskit_ibm_runtime" in err:
            err = "qiskit_ibm_runtime missing or failed under eval builtins: " + err
    return {"ok": ok, "python": py, "error": err, "versions": versions, "returncode": proc.returncode}


def cached_canary() -> dict[str, Any]:
    global _CANARY_CACHE
    with _LOCK:
        if _CANARY_CACHE is None:
            _CANARY_CACHE = canary_probe()
        return _CANARY_CACHE


def require_grader_runtime() -> dict[str, Any]:
    """Hard-fail a QHE job if eval Python cannot import ibm_runtime under grader builtins."""
    rec = cached_canary()
    if not rec.get("ok"):
        raise GraderRuntimeError(
            "QHE eval Python failed the ibm_runtime canary; refusing to burn LLM. "
            + str(rec.get("error") or "unknown")
        )
    return rec


def parse_missing_module(error: str) -> str | None:
    text = error or ""
    m = _MISSING_MODULE_RE.search(text)
    if m:
        return m.group("mod")
    return None


def grader_has_module(module: str) -> bool:
    """True if eval Python can import the top-level package of `module`."""
    if not module:
        return False
    rec = cached_canary()
    if not rec.get("ok"):
        return False
    top = module.split(".", 1)[0]
    versions = rec.get("versions") or {}
    if top == "qiskit_ibm_runtime" or module.startswith("qiskit_ibm_runtime"):
        return "ibm_runtime" in versions
    if top == "qiskit_aer":
        return "aer" in versions
    if top == "qiskit":
        return "qiskit" in versions
    return False


def rewrite_eval_feedback(error: str) -> dict[str, Any]:
    """If grader already has the missing module, tell the model not to pip/stub."""
    raw = (error or "").strip()
    out = {"error": raw, "rewritten": False, "module": ""}
    mod = parse_missing_module(raw)
    if not mod or not grader_has_module(mod):
        return out
    ver = ""
    versions = cached_canary().get("versions") or {}
    if mod.startswith("qiskit_ibm_runtime"):
        ver = str(versions.get("ibm_runtime") or "")
    elif mod == "qiskit" or mod.startswith("qiskit."):
        ver = str(versions.get("qiskit") or "")
    clause = f" (version {ver})" if ver else ""
    out["error"] = raw + REWRITE_SUFFIX.format(module=mod, version_clause=clause)
    out["rewritten"] = True
    out["module"] = mod
    return out


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _subscript_str(slice_node: ast.AST) -> str | None:
    if isinstance(slice_node, ast.Slice):
        return None
    got = _const_str(slice_node)
    if got is not None:
        return got
    if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):  # py<3.9
        return _const_str(slice_node.value)
    return None


def _is_sys_modules(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "modules"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _iter_call_strings(node: ast.Call) -> list[str]:
    found: list[str] = []
    for arg in list(node.args) + [kw.value for kw in node.keywords]:
        s = _const_str(arg)
        if s:
            found.append(s)
        elif isinstance(arg, (ast.List, ast.Tuple)):
            for elt in arg.elts:
                t = _const_str(elt)
                if t:
                    found.append(t)
    return found


def preflight_env_guard(code: str) -> dict[str, Any]:
    """Reject pip install and qiskit sys.modules stubs. Does not consume an official gun."""
    src = (code or "").replace("\r\n", "\n")
    if _PIP_TEXT_RE.search(src):
        return {"ok": False, "reason": PREFLIGHT_NO_PIP, "kind": "pip"}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"ok": True, "reason": "", "kind": ""}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            strings = _iter_call_strings(node)
            joined = " ".join(strings).lower()
            if name in {"run", "Popen", "call", "check_call", "check_output"} or name == "system":
                if "pip" in joined and "install" in joined:
                    return {"ok": False, "reason": PREFLIGHT_NO_PIP, "kind": "pip"}
            if name == "ModuleType":
                for s in strings:
                    if s.startswith("qiskit"):
                        return {"ok": False, "reason": PREFLIGHT_NO_STUB, "kind": "stub"}
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and _is_sys_modules(t.value):
                    key = _subscript_str(t.slice)
                    if key is None or key.startswith("qiskit"):
                        return {"ok": False, "reason": PREFLIGHT_NO_STUB, "kind": "stub"}
    return {"ok": True, "reason": "", "kind": ""}


def refuse_locked_tag(tag: str | None) -> None:
    t = str(tag or "")
    if "qheenv" not in t:
        raise ValueError(
            f"qhe_env_guard requires a *qheenv* tag, got {t!r}; use e4_iso_v2a_qheenv"
        )
    if t in LOCKED_GUARD_TAGS:
        raise ValueError(
            f"qhe_env_guard refuses locked tag {t}; use e4_iso_v2a_qheenv or a new tag"
        )
    if t.startswith("e4_iso_v2a") and "qheenv" not in t:
        raise ValueError(f"qhe_env_guard refuses locked v2a family tag {t}")
