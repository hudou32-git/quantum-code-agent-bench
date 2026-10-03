"""Host-side per-task jail for EQPA. Sandbox binds this directory read-only."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from exp import config
from exp.eqpa.config import EQPA_TAG

ALLOWED_ATTEMPTS = ("attempt_1.py", "attempt_2.py", "attempt_3.py")


@dataclass
class IsoSession:
    task_id: str
    host_dir: Path
    last_write_name: str | None = None
    written: set[str] = field(default_factory=set)
    written_tmp: set[str] = field(default_factory=set)
    last_tmp_name: str | None = None
    slot_written: set[str] = field(default_factory=set)
    inspect_handles: dict[str, dict] = field(default_factory=dict)
    inspect_seq: int = 0
    diag_last: dict | None = None

    def attempt_path(self, name: str) -> Path:
        if name not in ALLOWED_ATTEMPTS:
            raise ValueError(name)
        return self.host_dir / name

    def scratch_dir(self) -> Path:
        d = self.host_dir / "_scratch"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def tmp_path(self, name: str) -> Path:
        base = Path(name).name
        if base != name or not base.endswith(".py") or base.startswith("."):
            raise ValueError(name)
        return self.scratch_dir() / base


def task_safe(task_id: str) -> str:
    return task_id.replace("/", "_")


def jail_dir(tag: str, task_id: str) -> Path:
    return config.EQPA_JAIL_ROOT / tag / task_safe(task_id)


def ensure_jail(task_id: str, *, tag: str | None = None, prompt: str = "") -> IsoSession:
    tag = tag or EQPA_TAG
    host = jail_dir(tag, task_id)
    host.mkdir(parents=True, exist_ok=True)
    prompt_path = host / "prompt.txt"
    if prompt or not prompt_path.is_file():
        prompt_path.write_text(prompt or f"synthetic isolation task {task_id}\n", encoding="utf-8")
    return IsoSession(task_id=task_id, host_dir=host)
