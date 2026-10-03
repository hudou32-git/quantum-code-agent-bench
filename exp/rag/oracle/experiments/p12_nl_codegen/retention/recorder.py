"""High-level retention recorder for one logical LLM completion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from experiments.p12_nl_codegen.config import (
    DISABLE_THINKING,
    MAX_TOKENS,
    MODEL,
    PKG_ROOT,
    PROTOCOL_ID,
    TEMPERATURE,
)
from experiments.p12_nl_codegen.retention.hashutil import sha256_file
from experiments.p12_nl_codegen.retention.ids import make_completion_id
from experiments.p12_nl_codegen.retention.store import (
    RawLayout,
    append_jsonl,
    utc_now,
    write_json_immutable,
    write_text_immutable,
)

EXTRACTOR_PATH = PKG_ROOT / "extract.py"
RECORDS = PKG_ROOT / "records"


def calls_path(block: str) -> Path:
    return RECORDS / f"{block}_calls.jsonl"


def attempts_path(block: str) -> Path:
    return RECORDS / f"{block}_attempts.jsonl"


class RetentionRecorder:
    def __init__(self, block: str) -> None:
        self.block = block
        self.layout = RawLayout(PKG_ROOT, block)
        self.layout.ensure()
        self.extractor_hash = sha256_file(EXTRACTOR_PATH) if EXTRACTOR_PATH.exists() else ""

    def completion_id(self, arm: str, task_id: str, round_idx: int) -> str:
        return make_completion_id(
            protocol_id=PROTOCOL_ID,
            block=self.block,
            arm=arm,
            task_id=task_id,
            round_idx=round_idx,
        )

    def save_prompt(
        self,
        *,
        completion_id: str,
        rendered_prompt: str,
        meta: Dict[str, Any],
    ) -> Dict[str, str]:
        txt = self.layout.prompts / f"{completion_id}.txt"
        js = self.layout.prompts / f"{completion_id}.json"
        ph = write_text_immutable(txt, rendered_prompt, label=str(txt))
        meta = {
            **meta,
            "completion_id": completion_id,
            "protocol_id": PROTOCOL_ID,
            "block": self.block,
            "rendered_prompt_hash": ph,
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "disable_thinking": DISABLE_THINKING,
            "created_at_utc": meta.get("created_at_utc") or utc_now(),
        }
        write_json_immutable(js, meta, label=str(js))
        return {"raw_prompt_path": str(txt), "prompt_meta_path": str(js), "rendered_prompt_hash": ph}

    def save_response(
        self,
        *,
        completion_id: str,
        raw_text: str,
        meta: Dict[str, Any],
    ) -> Dict[str, str]:
        txt = self.layout.responses / f"{completion_id}.txt"
        js = self.layout.responses / f"{completion_id}.json"
        rh = write_text_immutable(txt, raw_text, label=str(txt))
        meta = {**meta, "completion_id": completion_id, "raw_response_hash": rh}
        write_json_immutable(js, meta, label=str(js))
        return {"raw_response_path": str(txt), "response_meta_path": str(js), "raw_response_hash": rh}

    def save_code(
        self,
        *,
        completion_id: str,
        code: str,
        meta: Dict[str, Any],
    ) -> Dict[str, str]:
        py = self.layout.extracted / f"{completion_id}.py"
        js = self.layout.extracted / f"{completion_id}.json"
        ch = write_text_immutable(py, code or "", label=str(py))
        meta = {
            **meta,
            "completion_id": completion_id,
            "extractor_file_hash": self.extractor_hash,
            "extracted_code_hash": ch,
            "extracted_code_chars": len(code or ""),
            "extracted_code_lines": len((code or "").splitlines()),
        }
        write_json_immutable(js, meta, label=str(js))
        return {"code_path": str(py), "code_meta_path": str(js), "extracted_code_hash": ch}

    def save_retrieval(self, *, completion_id: str, payload: Dict[str, Any]) -> str:
        path = self.layout.retrieval / f"{completion_id}.json"
        write_json_immutable(path, {"completion_id": completion_id, **payload}, label=str(path))
        return str(path)

    def save_feedback(
        self,
        *,
        completion_id: str,
        feedback_text: str,
        meta: Dict[str, Any],
    ) -> Dict[str, str]:
        txt = self.layout.feedback / f"{completion_id}.txt"
        js = self.layout.feedback / f"{completion_id}.json"
        fh = write_text_immutable(txt, feedback_text or "", label=str(txt))
        meta = {**meta, "completion_id": completion_id, "feedback_text_hash": fh}
        write_json_immutable(js, meta, label=str(js))
        return {"feedback_path": str(txt), "feedback_meta_path": str(js), "feedback_hash": fh}

    def save_eval(
        self,
        *,
        completion_id: str,
        stdout: str,
        stderr: str,
        meta: Dict[str, Any],
    ) -> Dict[str, str]:
        so = self.layout.eval_stdout / f"{completion_id}.txt"
        se = self.layout.eval_stderr / f"{completion_id}.txt"
        jm = self.layout.eval_meta / f"{completion_id}.json"
        sh = write_text_immutable(so, stdout or "", label=str(so))
        eh = write_text_immutable(se, stderr or "", label=str(se))
        meta = {**meta, "completion_id": completion_id, "stdout_hash": sh, "stderr_hash": eh}
        write_json_immutable(jm, meta, label=str(jm))
        return {
            "stdout_path": str(so),
            "stderr_path": str(se),
            "eval_meta_path": str(jm),
            "stdout_hash": sh,
            "stderr_hash": eh,
        }

    def log_attempt(self, row: Dict[str, Any]) -> None:
        append_jsonl(attempts_path(self.block), row)
        cid = row.get("completion_id") or "unknown"
        append_jsonl(self.layout.api_attempts / f"{cid}.jsonl", row)

    def log_call(self, row: Dict[str, Any]) -> None:
        append_jsonl(calls_path(self.block), row)

    def exists_completion(self, completion_id: str) -> bool:
        return (self.layout.prompts / f"{completion_id}.txt").exists()
