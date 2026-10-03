"""Launch Shell commands inside a bubblewrap mount/process sandbox.

Hard-fails if `bwrap` is missing. Never falls back to the host cwd/filesystem.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from exp import config

QHE_SANDBOX = "/opt/qhe"
WORKSPACE_SANDBOX = "/workspace"
_LEAK_NEEDLES = (str(config.ROOT), "/root/cyy/llm_code")
_OVERLAY_CACHE: list[tuple[Path, str]] | None = None
_OVERLAY_LOCK = threading.Lock()


class SandboxError(RuntimeError):
    pass


def require_bwrap() -> str:
    path = shutil.which("bwrap")
    if not path:
        raise SandboxError(
            "bwrap not found; EQPA refuses to execute Shell on the host filesystem"
        )
    return path


def _is_text_leaky(path: Path) -> bool:
    try:
        if path.stat().st_size > 2_000_000:
            return False
        data = path.read_bytes()
    except OSError:
        return False
    if b"\0" in data[:4096]:
        return any(n.encode() in data for n in _LEAK_NEEDLES)
    text = data.decode("utf-8", errors="ignore")
    return any(n in text for n in _LEAK_NEEDLES)


def _sanitized_bytes(path: Path) -> bytes:
    suffix = path.suffix
    if suffix == ".pth":
        return b"# stripped by EQPA\n"
    if suffix == ".json":
        return b"{}\n"
    if suffix in {".py", ".txt", ".egg-link"}:
        return b"# stripped by EQPA\n"
    return b""


def python_overlays() -> list[tuple[Path, str]]:
    """Host overlay file → sandbox dest path (under /opt/qhe)."""
    global _OVERLAY_CACHE
    with _OVERLAY_LOCK:
        if _OVERLAY_CACHE is not None:
            return _OVERLAY_CACHE
        env = config.QHE_ENV
        overlay_root = config.EQPA_OVERLAY_ROOT
        overlay_root.mkdir(parents=True, exist_ok=True)
        pairs: list[tuple[Path, str]] = []
        site = env / "lib/python3.10/site-packages"
        roots = [site]
        extra = env / "lib/python3.1/site-packages"
        if extra.is_dir():
            roots.append(extra)
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d != "__pycache__" or True]
                for name in filenames:
                    host = Path(dirpath) / name
                    rel = host.relative_to(env).as_posix()
                    leaky = False
                    if name.endswith((".pth", ".egg-link")) or "direct_url.json" in name:
                        leaky = _is_text_leaky(host) or name.startswith("__editable__")
                    elif "editable" in name.lower() or name.endswith((".py", ".pyc", ".json")):
                        leaky = _is_text_leaky(host)
                    if not leaky:
                        continue
                    dest = overlay_root / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(_sanitized_bytes(host))
                    pairs.append((dest, f"{QHE_SANDBOX}/{rel}"))
        _OVERLAY_CACHE = pairs
        return pairs


def _symlink_or_bind(argv: list[str], host: str, dest: str) -> None:
    path = Path(host)
    if not path.exists():
        return
    if path.is_symlink():
        argv.extend(["--symlink", os.readlink(host), dest])
    else:
        argv.extend(["--ro-bind", host, dest])


def build_bwrap_argv(jail: Path, command: str, *, scratch_host: Path | None = None) -> list[str]:
    bwrap = require_bwrap()
    env = str(config.QHE_ENV)
    argv: list[str] = [
        bwrap,
        "--die-with-parent",
        "--unshare-user",
        "--uid",
        "65534",
        "--gid",
        "65534",
        "--unshare-pid",
        "--unshare-net",
        "--unshare-uts",
        "--unshare-ipc",
        "--unshare-cgroup-try",
        "--hostname",
        "sandbox",
        "--cap-drop",
        "ALL",
        "--setenv",
        "HOME",
        "/home/agent",
        "--setenv",
        "PWD",
        WORKSPACE_SANDBOX,
        "--setenv",
        "PATH",
        f"{QHE_SANDBOX}/bin:/usr/bin:/bin",
        "--setenv",
        "LANG",
        "C.UTF-8",
        "--setenv",
        "LC_ALL",
        "C.UTF-8",
        "--setenv",
        "PYTHONDONTWRITEBYTECODE",
        "1",
        "--setenv",
        "PYTHONNOUSERSITE",
        "1",
        "--setenv",
        "CONDA_PREFIX",
        QHE_SANDBOX,
        "--unsetenv",
        "PYTHONPATH",
        "--unsetenv",
        "PYTHONHOME",
        "--unsetenv",
        "HISTFILE",
        "--unsetenv",
        "LD_PRELOAD",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
    ]
    if scratch_host is not None:
        scratch_host.mkdir(parents=True, exist_ok=True)
        argv.extend(["--bind", str(scratch_host.resolve()), "/tmp"])
    else:
        argv.extend(["--tmpfs", "/tmp"])
    argv.extend(
        [
            "--dir",
            "/home/agent",
            "--dir",
            "/root",
            "--ro-bind",
            "/usr",
            "/usr",
        ]
    )
    _symlink_or_bind(argv, "/bin", "/bin")
    _symlink_or_bind(argv, "/lib", "/lib")
    _symlink_or_bind(argv, "/lib64", "/lib64")
    _symlink_or_bind(argv, "/sbin", "/sbin")
    argv.extend(["--ro-bind-try", "/etc", "/etc"])
    argv.extend(["--ro-bind", env, QHE_SANDBOX])
    for overlay, dest in python_overlays():
        argv.extend(["--ro-bind", str(overlay), dest])
    argv.extend(
        [
            "--ro-bind",
            str(jail.resolve()),
            WORKSPACE_SANDBOX,
            "--chdir",
            WORKSPACE_SANDBOX,
            "--",
            "/bin/sh",
            "-c",
            command,
        ]
    )
    return argv


def sandbox_env() -> dict[str, str]:
    return {
        "HOME": "/home/agent",
        "PWD": WORKSPACE_SANDBOX,
        "PATH": f"{QHE_SANDBOX}/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "CONDA_PREFIX": QHE_SANDBOX,
    }


def run_sandboxed(
    command: str,
    *,
    jail: Path,
    timeout: float | None = None,
    max_bytes: int | None = None,
    scratch_host: Path | None = None,
) -> dict[str, Any]:
    timeout = config.REPL_TIMEOUT if timeout is None else timeout
    max_bytes = config.REPL_MAX_BYTES if max_bytes is None else max_bytes
    cmd = (command or "").strip()
    out: dict[str, Any] = {
        "ok": False,
        "blocked": False,
        "stdout": "",
        "stderr": "",
        "text": "",
        "exit_code": None,
        "reason": "",
        "sandboxed": True,
    }
    if not cmd:
        out["blocked"] = True
        out["reason"] = "empty command"
        out["text"] = "Shell blocked: empty command"
        return out
    argv = build_bwrap_argv(jail, cmd, scratch_host=scratch_host)
    assert_not_host_bind(argv, jail=jail)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            env=sandbox_env(),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"")[:max_bytes]
        stderr = (exc.stderr or b"")[: max_bytes // 2]
        out["reason"] = f"timeout {timeout}s"
        out["exit_code"] = -1
        out["stdout"] = _decode(stdout)
        out["stderr"] = _decode(stderr)
        out["text"] = _combine(out["stdout"], out["stderr"], out["reason"])[: max_bytes + 200]
        return out
    stdout = (proc.stdout or b"")[:max_bytes]
    stderr = (proc.stderr or b"")[: max_bytes // 2]
    out["stdout"] = _decode(stdout)
    out["stderr"] = _decode(stderr)
    out["exit_code"] = proc.returncode
    out["ok"] = proc.returncode == 0
    if not out["ok"]:
        out["reason"] = "nonzero exit"
    out["text"] = _combine(out["stdout"], out["stderr"], out["reason"] if not out["ok"] else "")[
        : max_bytes + 200
    ]
    return out


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _combine(stdout: str, stderr: str, reason: str) -> str:
    parts = []
    if stdout:
        parts.append(stdout.rstrip())
    if stderr:
        parts.append("stderr:\n" + stderr.rstrip())
    if reason:
        parts.append(f"status: {reason}")
    return "\n".join(parts)


def assert_not_host_bind(argv: list[str], *, jail: Path) -> None:
    """Refuse argv that bind dataset/sealed/repo root. The per-task jail is allowed."""
    repo = str(config.ROOT.resolve())
    jail_r = str(jail.resolve())
    overlay_r = str(config.EQPA_OVERLAY_ROOT.resolve())
    allowed_prefixes = (jail_r, overlay_r, str(config.QHE_ENV.resolve()))
    forbidden = (
        str(config.QHE_DATASET_DIR.resolve()),
        str(config.QHE_SEALED_DIR.resolve()),
        str(config.QHE_EVAL_DIR.resolve()),
        repo,
    )
    i = 0
    while i < len(argv) - 1:
        if argv[i] in {"--ro-bind", "--bind", "--ro-bind-try", "--bind-try", "--dev-bind"}:
            src = argv[i + 1]
            try:
                resolved = str(Path(src).resolve())
            except OSError:
                resolved = src
            if any(resolved == a or resolved.startswith(a + os.sep) for a in allowed_prefixes):
                i += 1
                continue
            if resolved == repo or any(
                resolved == f or resolved.startswith(f + os.sep) for f in forbidden
            ):
                raise SandboxError(f"refusing to bind repository into sandbox: {src}")
        i += 1


