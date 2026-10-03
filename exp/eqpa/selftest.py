"""No-LLM isolation regression suite for EQPA. Synthetic commands only."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

MYAGENT = Path(__file__).resolve().parents[1]
if str(MYAGENT) not in sys.path:
    sys.path.insert(0, str(MYAGENT))

from exp import config
from exp.eqpa.bwrap import require_bwrap
from exp.common.canary import (
    canary_values,
    ensure_canaries,
    host_canary_path,
    scan_text,
)
from exp.eqpa.jail import ensure_jail
from exp.eqpa.tools import EQPA_TOOLS, run_eval, run_shell, run_write

_OBS: list[str] = []


class Failed(AssertionError):
    pass


def _shell(session, command: str) -> dict[str, Any]:
    obs = run_shell(command, session=session)
    _OBS.append(obs.get("text") or "")
    if obs.get("raw_leaked"):
        raise Failed(f"canary leaked into raw stdout for: {command!r}")
    return obs


def _py(session, src: str) -> dict[str, Any]:
    return _shell(session, f"python - <<'ISO_SNIP'\n{src.rstrip()}\nISO_SNIP")


def _no_canary(text: str, *, label: str) -> None:
    hits = scan_text(text)
    if hits:
        raise Failed(f"{label}: canary in output")


def _no_repo(text: str, *, label: str) -> None:
    if "llm_code" in (text or ""):
        raise Failed(f"{label}: repo path string in output: {text[:400]!r}")


def test_tools_schema() -> None:
    names = [t["function"]["name"] for t in EQPA_TOOLS]
    if names != ["Shell", "Write", "Eval"]:
        raise Failed(f"tools={names}")
    require_bwrap()


def test_qiskit_and_fake(session) -> None:
    obs = _shell(
        session,
        "python -c 'import qiskit,inspect,qiskit_ibm_runtime.fake_provider as fp; "
        "from qiskit_ibm_runtime.fake_provider import FakeOslo; "
        "print(qiskit.__version__); print(hasattr(fp,\"FakeOslo\")); "
        "print(inspect.getfile(FakeOslo))'",
    )
    text = obs.get("text") or ""
    if "2.4.1" not in text:
        raise Failed(f"qiskit version missing: {text[:500]}")
    if "True" not in text:
        raise Failed(f"FakeOslo hasattr failed: {text[:500]}")
    _no_canary(text, label="qiskit")


def test_cirq(session) -> None:
    """e8 (QB+_cirq): the jailed interpreter must expose cirq (and its
    simulator) so EQPA's Inspect can ground cirq API facts."""
    obs = _shell(
        session,
        "python -c 'import cirq,inspect; "
        "q=cirq.LineQubit(0); c=cirq.Circuit(cirq.H(q), cirq.measure(q, key=\"result\")); "
        "r=cirq.Simulator().run(c, repetitions=10); "
        "print(cirq.__version__); print(sorted(r.measurements.keys())); "
        "print(inspect.getfile(cirq))'",
    )
    text = obs.get("text") or ""
    if "1.5.0" not in text:
        raise Failed(f"cirq version missing: {text[:500]}")
    if "result" not in text:
        raise Failed(f"cirq measurement key missing: {text[:500]}")
    _no_canary(text, label="cirq")


def test_pennylane(session) -> None:
    """e9 (QB+_pennylane): the jailed interpreter must expose pennylane with a
    working default.qubit + qml.sample pipeline (the QB+ return contract) so
    EQPA's Inspect can ground pennylane API facts."""
    obs = _shell(
        session,
        "python -c 'import pennylane as qml,inspect; "
        "d=qml.device(\"default.qubit\", wires=2, shots=1000); "
        "f=qml.qnode(d)(lambda: (qml.PauliX(1), qml.sample(wires=[0,1]))[1]); "
        "s=f(); print(qml.__version__); print(s.shape, str(s.dtype)); "
        "print(inspect.getfile(qml))'",
    )
    text = obs.get("text") or ""
    if "0.38.0" not in text:
        raise Failed(f"pennylane version missing: {text[:500]}")
    if "(1000, 2)" not in text:
        raise Failed(f"qml.sample shape missing: {text[:500]}")
    _no_canary(text, label="pennylane")


def test_direct_escape(session) -> None:
    cmds = [
        "ls /root/cyy/llm_code",
        "ls ../..",
        "python -c 'import os; os.chdir(\"/\"); print(os.listdir(\".\"))'",
        "python -c 'print(open(\"/root/cyy/llm_code/qiskit-human-eval/dataset/"
        "dataset_qiskit_test_human_eval_local_hard.json\").read()[:80])'",
        f"python -c 'print(open({str(host_canary_path())!r}).read())'",
    ]
    for cmd in cmds:
        obs = _shell(session, cmd)
        text = obs.get("text") or ""
        _no_canary(text, label=cmd)
        if "canonical_solution" in text or "def check(" in text:
            raise Failed(f"gold/test in output: {cmd}")


def test_indirect_listdir(session) -> None:
    obs = _shell(
        session,
        'python -c \'print(getattr(__import__("os"), "listdir")("/"))\'',
    )
    text = obs.get("text") or ""
    _no_canary(text, label="getattr listdir")
    if "cyy" in text or "llm_code" in text or "dataset" in text:
        raise Failed(f"host names in / : {text[:500]}")
    if "workspace" not in text or "opt" not in text:
        raise Failed(f"sandbox root missing expected mounts: {text[:500]}")


def test_file_apis(session) -> None:
    src = r"""
import os, io, glob, pathlib, mmap
root = "/"
print("os.open", end=" ")
try:
    os.open("/root/cyy/llm_code", os.O_RDONLY)
    print("opened")
except OSError as e:
    print(type(e).__name__)
print("io.open", end=" ")
try:
    io.open("/root/cyy/llm_code/submit/bench/qhe/dataset", "r")
    print("opened")
except OSError as e:
    print(type(e).__name__)
print("pathlib", list(pathlib.Path("/").iterdir()))
print("glob", glob.glob("/root/*"))
print("scandir", [e.name for e in os.scandir("/")])
"""
    obs = _py(session, src)
    text = obs.get("text") or ""
    _no_canary(text, label="file apis")
    if "llm_code" in text or "dataset_qiskit" in text:
        raise Failed(text[:800])


def test_subprocess_find(session) -> None:
    src = r"""
import subprocess
try:
    r = subprocess.run(["find", "/", "-type", "f"], capture_output=True, text=True, timeout=8)
    out = (r.stdout or "") + (r.stderr or "")
    print("find_exit", r.returncode)
    print("n_files", out.count("\n"))
except subprocess.TimeoutExpired as e:
    out = ((e.stdout or "") if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace"))
    print("find_timeout")
    print("n_files", out.count("\n"))
print("has_canary", "SECRET_CANARY_" in out)
print("has_sealed", "problems_full.json" in out or "canonical_solution" in out)
print("has_dataset_json", "dataset_qiskit_test" in out)
"""
    obs = _py(session, src)
    text = obs.get("text") or ""
    _no_canary(text, label="find /")
    if "has_canary True" in text or "has_sealed True" in text or "has_dataset_json True" in text:
        raise Failed(f"find saw host private files: {text[:800]}")


def test_proc(session) -> None:
    src = r"""
import os
print("self_root", os.listdir("/proc/self/root"))
print("has_host_repo", os.path.exists("/proc/self/root/root/cyy/llm_code"))
print("pid1", os.path.exists("/proc/1"))
try:
    print("pid1_cwd", os.readlink("/proc/1/cwd"))
except OSError as e:
    print("pid1_cwd", type(e).__name__)
print("fd", os.listdir("/proc/self/fd"))
"""
    obs = _py(session, src)
    text = obs.get("text") or ""
    _no_canary(text, label="proc")
    if "llm_code" in text:
        raise Failed(text[:500])
    if "has_host_repo True" in text:
        raise Failed("proc/self/root sees host repo")


def test_symlink_to_host(session) -> None:
    host = str(host_canary_path("sealed"))
    src = (
        "import os\n"
        "print('exists', os.path.exists('/tmp/x'))\n"
        "print('link', os.readlink('/tmp/x'))\n"
        "try:\n"
        "    print(open('/tmp/x').read())\n"
        "except Exception as e:\n"
        "    print(type(e).__name__, e)\n"
    )
    _shell(session, f"ln -s {host} /tmp/x")
    obs = _py(session, src)
    text = obs.get("text") or ""
    _no_canary(text, label="symlink")
    if "SECRET_CANARY_" in text:
        raise Failed("symlink followed to canary content")


def test_environment(session) -> None:
    src = r"""
import os, sys, site
print("HOME", os.environ.get("HOME"))
print("PWD", os.environ.get("PWD"))
print("PYTHONPATH", os.environ.get("PYTHONPATH", "<unset>"))
print("CWD", os.getcwd())
print("PATH_HAS_REPO", any("llm_code" in p for p in sys.path))
print("SYS_PATH", sys.path)
print("SITE", site.getsitepackages())
print("ENV_REPO", any("llm_code" in (v or "") for v in os.environ.values()))
"""
    obs = _py(session, src)
    text = obs.get("text") or ""
    _no_canary(text, label="env")
    _no_repo(text, label="env")
    if "HOME /home/agent" not in text:
        raise Failed(text[:400])
    if "PWD /workspace" not in text and "CWD /workspace" not in text:
        raise Failed(text[:400])
    if "PATH_HAS_REPO True" in text:
        raise Failed("sys.path contains repo")
    if "ENV_REPO True" in text:
        raise Failed("environ contains repo")


def test_workspace_ro_tmp_rw(session) -> None:
    obs = _shell(session, "echo scratch > /tmp/test.py && cat /tmp/test.py && echo hack >> /workspace/prompt.txt")
    text = obs.get("text") or ""
    if "scratch" not in text:
        raise Failed(f"/tmp not writable: {text[:400]}")
    if obs.get("ok"):
        raise Failed("writing /workspace/prompt.txt should fail")
    cat = _shell(session, "cat /workspace/prompt.txt")
    if "hack" in (cat.get("text") or ""):
        raise Failed("workspace was mutated via Shell")


def test_cross_task(session_a, session_b) -> None:
    obs = _shell(session_b, "cat /workspace/prompt.txt; ls /workspace; python -c 'import os; print(os.listdir(\"/\"))'")
    text = obs.get("text") or ""
    if "TASK_A_ONLY" in text:
        raise Failed("task B saw task A prompt")
    if session_a.host_dir.name in text:
        raise Failed("task B saw task A jail name")
    _no_canary(text, label="cross-task")


def test_write_escape(session) -> None:
    for bad in ("../x.py", "/tmp/x.py", "attempt_1.py/../x.py", "attempt_4.py", "/workspace/attempt_1.py"):
        wr = run_write(path=bad, contents="x=1\n", session=session)
        if wr.get("ok") or not wr.get("blocked"):
            raise Failed(f"Write should block {bad!r}: {wr}")


def test_write_symlink(session) -> None:
    target = session.host_dir / "attempt_1.py"
    if target.exists() or target.is_symlink():
        target.unlink()
    os.symlink("/etc/passwd", target)
    wr = run_write(path="attempt_1.py", contents="def f():\n    return 1\n", session=session)
    if wr.get("ok") or not wr.get("blocked"):
        raise Failed(f"Write followed symlink: {wr}")
    if target.is_symlink():
        target.unlink()
    wr_ok = run_write(path="attempt_1.py", contents="def f():\n    return 1\n", session=session)
    if not wr_ok.get("ok"):
        raise Failed(wr_ok)
    seen = _shell(session, "cat /workspace/attempt_1.py")
    if "def f()" not in (seen.get("text") or ""):
        raise Failed("sandbox cannot read written attempt")
    mutate = _shell(session, "echo pwned >> /workspace/attempt_1.py")
    if mutate.get("ok"):
        raise Failed("sandbox mutated attempt via Shell")


def test_eval_before_write(session) -> None:
    session.last_write_name = None
    session.written.clear()
    ev = run_eval(session=session)
    text = (ev.get("text") or "") + (ev.get("error") or "")
    if ev.get("official_eval"):
        raise Failed("Eval before Write must not count as official eval")
    if "no successful Write" not in text:
        raise Failed(ev)
    _no_canary(text, label="eval-before-write")
    if "sealed" in text or "eval_blind" in text or "llm_code" in text:
        raise Failed(f"Eval error leaked paths: {text}")


def test_eval_synthetic_no_paths(session) -> None:
    wr = run_write(path="attempt_2.py", contents="def g():\n    return 2\n", session=session)
    if not wr.get("ok"):
        raise Failed(wr)
    ev = run_eval(session=session)
    text = (ev.get("text") or "") + (ev.get("error") or "")
    _no_canary(text, label="eval-synthetic")
    if str(config.QHE_SEALED_DIR) in text or "problems_full" in text:
        raise Failed(text)


def test_host_canaries_exist(tokens: dict[str, str]) -> None:
    for name in ("dataset", "sealed", "grader"):
        path = host_canary_path(name)
        if not path.is_file():
            raise Failed(f"missing canary file {path}")
        body = path.read_text(encoding="utf-8").strip()
        if body != tokens[name]:
            raise Failed(f"canary mismatch {name}")
        if not body.startswith("SECRET_CANARY_"):
            raise Failed(name)


def main() -> int:
    _OBS.clear()
    require_bwrap()
    tokens = ensure_canaries()
    session_a = ensure_jail("iso_selftest/task_a", prompt="TASK_A_ONLY prompt\n")
    session_b = ensure_jail("iso_selftest/task_b", prompt="TASK_B_ONLY prompt\n")
    tests: list[tuple[str, Callable[[], None]]] = [
        ("tools_schema", test_tools_schema),
        ("host_canaries", lambda: test_host_canaries_exist(tokens)),
        ("qiskit_and_fake", lambda: test_qiskit_and_fake(session_a)),
        ("cirq_import_and_sim", lambda: test_cirq(session_a)),
        ("pennylane_import_and_sample", lambda: test_pennylane(session_a)),
        ("direct_escape", lambda: test_direct_escape(session_a)),
        ("indirect_listdir", lambda: test_indirect_listdir(session_a)),
        ("file_apis", lambda: test_file_apis(session_a)),
        ("subprocess_find", lambda: test_subprocess_find(session_a)),
        ("proc", lambda: test_proc(session_a)),
        ("symlink_to_host", lambda: test_symlink_to_host(session_a)),
        ("environment", lambda: test_environment(session_a)),
        ("workspace_ro_tmp_rw", lambda: test_workspace_ro_tmp_rw(session_a)),
        ("cross_task", lambda: test_cross_task(session_a, session_b)),
        ("write_escape", lambda: test_write_escape(session_a)),
        ("write_symlink", lambda: test_write_symlink(session_a)),
        ("eval_before_write", lambda: test_eval_before_write(session_a)),
        ("eval_synthetic", lambda: test_eval_synthetic_no_paths(session_a)),
    ]
    results = []
    failed = 0
    for name, fn in tests:
        row = {"name": name, "ok": False, "error": ""}
        try:
            fn()
            row["ok"] = True
        except Exception as exc:
            failed += 1
            row["error"] = f"{type(exc).__name__}: {exc}"
        results.append(row)
        status = "PASS" if row["ok"] else "FAIL"
        print(f"{status}  {name}" + (f"  {row['error']}" if row["error"] else ""))

    joined = "\n".join(_OBS)
    canary_hits = scan_text(joined)
    summary = {
        "ok": failed == 0 and not canary_hits,
        "failed": failed,
        "n_tests": len(results),
        "canary_hits_in_observations": len(canary_hits),
        "n_observations": len(_OBS),
        "results": results,
    }
    print(json.dumps({k: summary[k] for k in summary if k != "results"}, indent=2))
    if canary_hits:
        print("FAIL  canary scan of all tool observations")
        return 1
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
