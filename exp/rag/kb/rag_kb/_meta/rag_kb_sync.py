#!/usr/bin/env python3
"""
Compare op/ Markdown knowledge files with a RAGFlow dataset (read-only by default).

Usage (from repo root or op/):
  python op/rag_kb_sync.py diff
  python op/rag_kb_sync.py diff --tier l2
  RAGFLOW_UPLOAD_DRY_RUN=1 python op/rag_kb_sync.py plan-l2

Sync is manual via rag_txt.ipynb + RAGFlow UI delete; use `download` to snapshot remote files.

  python op/rag_kb_sync.py download --out op/ragflow_export
  python op/rag_kb_sync.py sync --dry-run
  python op/rag_kb_sync.py sync --tier all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
from contextlib import ExitStack
from pathlib import Path

import requests

OP_DIR = Path(__file__).resolve().parent
REPO_ROOT = OP_DIR.parent

# Not part of retrieval KB
SKIP_REL_PREFIXES = ("test/", "ragflow_export/", "kb_upload_staging/")
SKIP_REL_NAMES = {
    "RAG_KB_CONTENT_SCOPE.md",
    "RAG_L1_L2_MODIFICATION_PLAN.md",
    "KB_HUMANEVAL_RISK_INVENTORY.md",
}
SKIP_SUFFIX = "/INGESTION.md"

# Pairs: deprecated basename -> keep basename (repo merge target; see KB_HUMANEVAL_RISK_INVENTORY.md)
DEPRECATED_BASENAME_PAIRS = [
    ("heval_runtime_sampler_estimator_mode.md", "heval_runtime_sampler_estimator.md"),
    ("heval_runtime_results_options.md", "heval_runtime_results_sampler_options.md"),
    ("heval_primitives_vs_runtime.md", "heval_primitives_vs_runtime_import_rules.md"),
    ("heval_aer_local_no_cloud.md", "heval_aer_simulator_local_no_service.md"),
    ("heval_fake_provider_transpile.md", "heval_fake_provider_transpile_pass_manager.md"),
]


def load_env() -> None:
    """与 vllm_common / optimization_common 一致：优先 cwd，其次仓库内，再 workspace 根（与 qiskit-human-eval 同级）。"""
    candidates = (
        Path.cwd() / ".env",
        REPO_ROOT / ".env",
        REPO_ROOT.parent / ".env",
    )
    env_file = next((p for p in candidates if p.is_file()), None)
    if env_file is None:
        tried = ", ".join(str(p) for p in candidates)
        raise FileNotFoundError(f"Missing .env (已尝试: {tried})")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def ragflow_host() -> str:
    address = os.getenv("RAGFLOW_ADDRESS", "").strip()
    if address:
        return address
    url = os.getenv("RAGFLOW_RETRIEVAL_URL", "").strip().strip('"').strip("'")
    m = re.match(r"https?://([^/]+)", url)
    if not m:
        raise RuntimeError("Set RAGFLOW_ADDRESS or RAGFLOW_RETRIEVAL_URL in .env")
    return m.group(1)


def list_remote_documents(host: str, dataset_id: str, api_key: str) -> list[dict]:
    url = f"http://{host}/api/v1/datasets/{dataset_id}/documents"
    headers = {"Authorization": f"Bearer {api_key}"}
    out: list[dict] = []
    page = 1
    while page <= 200:
        resp = requests.get(
            url,
            headers=headers,
            params={"page": page, "page_size": 100},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message") or data)
        docs = (data.get("data") or {}).get("docs") or []
        if not docs:
            break
        out.extend(docs)
        if len(docs) < 100:
            break
        page += 1
    return out


def load_manifest_basenames(subdir: str) -> set[str]:
    mf = OP_DIR / subdir / "MANIFEST.json"
    if not mf.is_file():
        return set()
    j = json.loads(mf.read_text(encoding="utf-8"))
    names: set[str] = set()
    for key in ("files", "p0_files", "p1_files"):
        for name in j.get(key) or []:
            names.add(name)
    return names


def tier_l2_relpaths() -> set[str]:
    """HumanEval L2 scope: runtime + topics + recipes MANIFEST + ingest note."""
    rels: set[str] = set()
    for sub in (
        "RAG_qiskit_human_eval_runtime",
        "RAG_qiskit_human_eval_topics",
        "RAG_qiskit_recipes",
    ):
        for base in load_manifest_basenames(sub):
            rels.add(f"{sub}/{base}")
    # Updated canonical pages not yet in MANIFEST.json
    rels.add("RAG_qiskit_human_eval_runtime/heval_runtime_sampler_estimator.md")
    rels.add("RAG_qiskit_human_eval_runtime/heval_quantum_circuit_patterns.md")
    rels.add("RAG_qiskit_human_eval_runtime/heval_pass_manager_workflows.md")
    rels.add("RAG_qiskit_api/HUMANEVAL_RAG_INGEST_NOTE.md")
    return rels


def iter_local_md(tier: str) -> list[Path]:
    l2 = tier_l2_relpaths()
    paths: list[Path] = []
    for p in sorted(OP_DIR.rglob("*.md")):
        rel = p.relative_to(OP_DIR).as_posix()
        if rel.startswith(SKIP_REL_PREFIXES) or rel in SKIP_REL_NAMES:
            continue
        if SKIP_SUFFIX in rel:
            continue
        if rel.endswith("HUMANEVAL_API_DOC_AUDIT.md"):
            continue
        if tier == "l2" and rel not in l2:
            continue
        if tier == "api" and not rel.startswith("RAG_qiskit_api/"):
            continue
        paths.append(p)
    return paths


def norm_duplicate_basename(name: str) -> str:
    return re.sub(r"\(\d+\)(?=\.md$)", "", name)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ragflow_api_json(
    method: str,
    url: str,
    api_key: str,
    *,
    expect_code_zero: bool = True,
    **kwargs,
) -> dict:
    headers = kwargs.pop("headers", {})
    headers.setdefault("Authorization", f"Bearer {api_key}")
    resp = requests.request(method, url, timeout=300, headers=headers, **kwargs)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Non-JSON response from {url}: {resp.text[:500]}") from e
    if expect_code_zero and data.get("code") != 0:
        raise RuntimeError(
            f"RAGFlow error: code={data.get('code')} message={data.get('message')}"
        )
    return data


def group_remote_by_canonical_basename(remote: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for doc in remote:
        name = doc.get("name") or ""
        if not name:
            continue
        key = norm_duplicate_basename(name) if name.lower().endswith(".md") else name
        groups.setdefault(key, []).append(doc)
    return groups


def remote_doc_bytes(
    host: str,
    dataset_id: str,
    api_key: str,
    doc: dict,
    export_flat: Path | None,
) -> bytes:
    name = doc.get("name") or ""
    size = int(doc.get("size") or 0)
    if export_flat is not None:
        cached = export_flat / name
        if cached.is_file() and cached.stat().st_size == size:
            return cached.read_bytes()
    return download_document_content(host, dataset_id, api_key, doc["id"])


def needs_sync_for_local(
    local_path: Path,
    remotes: list[dict],
    host: str,
    dataset_id: str,
    api_key: str,
    export_flat: Path | None,
) -> tuple[bool, list[str], str]:
    """
    Returns (should_sync, document_ids_to_delete, reason).
    """
    base = local_path.name
    local_hash = sha256_file(local_path)
    if not remotes:
        return True, [], "missing_on_remote"

    delete_ids = [d["id"] for d in remotes if d.get("id")]
    canonical = [d for d in remotes if d.get("name") == base]
    extras = [d for d in remotes if d.get("name") != base]

    if len(remotes) == 1 and remotes[0].get("name") == base:
        body = remote_doc_bytes(host, dataset_id, api_key, remotes[0], export_flat)
        if sha256_bytes(body) == local_hash:
            return False, [], "unchanged"

    if len(canonical) == 1 and not extras:
        body = remote_doc_bytes(host, dataset_id, api_key, canonical[0], export_flat)
        if sha256_bytes(body) == local_hash:
            return False, [], "unchanged"

    if extras:
        return True, delete_ids, f"duplicate_remote_names({len(remotes)})"

    if canonical:
        body = remote_doc_bytes(host, dataset_id, api_key, canonical[0], export_flat)
        if sha256_bytes(body) != local_hash:
            return True, delete_ids, "content_changed"

    return True, delete_ids, "reconcile_remote_set"


def delete_documents(
    host: str, dataset_id: str, api_key: str, document_ids: list[str]
) -> None:
    if not document_ids:
        return
    url = f"http://{host}/api/v1/datasets/{dataset_id}/documents"
    headers = {"Content-Type": "application/json"}
    last_err: Exception | None = None
    for payload in ({"ids": document_ids}, {"document_ids": document_ids}):
        try:
            ragflow_api_json(
                "DELETE",
                url,
                api_key,
                headers=headers,
                json=payload,
            )
            return
        except Exception as e:
            last_err = e
    raise RuntimeError(f"delete_documents failed: {last_err}")


def upload_local_files(
    host: str, dataset_id: str, api_key: str, paths: list[Path]
) -> list[str]:
    if not paths:
        return []
    url = f"http://{host}/api/v1/datasets/{dataset_id}/documents"
    headers = {"Authorization": f"Bearer {api_key}"}
    with ExitStack() as stack:
        files = []
        for path in paths:
            fo = stack.enter_context(open(path, "rb"))
            mime = mimetypes.guess_type(path.name)[0] or "text/markdown"
            files.append(("file", (path.name, fo, mime)))
        resp = requests.post(
            url, headers=headers, files=files, params={"type": "local"}, timeout=300
        )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(data.get("message") or data)
    doc_ids: list[str] = []
    for doc in data.get("data") or []:
        if doc.get("id"):
            doc_ids.append(doc["id"])
    if len(doc_ids) != len(paths):
        raise RuntimeError(
            f"upload returned {len(doc_ids)} ids for {len(paths)} files"
        )
    return doc_ids


def parse_documents(host: str, dataset_id: str, api_key: str, document_ids: list[str]) -> None:
    if not document_ids:
        return
    url = f"http://{host}/api/v1/datasets/{dataset_id}/chunks"
    ragflow_api_json(
        "POST",
        url,
        api_key,
        headers={"Content-Type": "application/json"},
        json={"document_ids": document_ids},
    )


def cmd_sync(tier: str, dry_run: bool, batch_size: int, sleep_s: float) -> int:
    load_env()
    host = ragflow_host()
    dataset_id = os.getenv("RAGFLOW_DATASET_ID", "").strip()
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip()
    if not dataset_id or not api_key:
        print("RAGFLOW_DATASET_ID / RAGFLOW_API_KEY required", file=sys.stderr)
        return 1

    export_flat = OP_DIR / "ragflow_export" / "files"
    if not export_flat.is_dir():
        export_flat = None
        print("note: no op/ragflow_export/files cache; will download remote bytes for hash checks")

    remote = list_remote_documents(host, dataset_id, api_key)
    grouped = group_remote_by_canonical_basename(remote)
    local_paths = iter_local_md(tier)

    to_sync: list[tuple[Path, list[str], str]] = []
    skipped = 0
    for path in local_paths:
        remotes = grouped.get(path.name, [])
        sync, delete_ids, reason = needs_sync_for_local(
            path, remotes, host, dataset_id, api_key, export_flat
        )
        if sync:
            to_sync.append((path, delete_ids, reason))
        else:
            skipped += 1

    print(f"sync tier={tier} local={len(local_paths)} skip={skipped} update={len(to_sync)}")
    for path, delete_ids, reason in to_sync:
        rel = path.relative_to(OP_DIR).as_posix()
        print(f"  {rel}  delete={len(delete_ids)}  reason={reason}")

    if dry_run:
        print("dry-run: no delete/upload/parse")
        return 0

    upload_queue: list[Path] = []
    for path, delete_ids, reason in to_sync:
        if delete_ids:
            delete_documents(host, dataset_id, api_key, delete_ids)
            time.sleep(0.3)
        upload_queue.append(path)

    for start in range(0, len(upload_queue), batch_size):
        batch = upload_queue[start : start + batch_size]
        print(f"upload batch {start + 1}-{start + len(batch)} / {len(upload_queue)}")
        doc_ids = upload_local_files(host, dataset_id, api_key, batch)
        parse_documents(host, dataset_id, api_key, doc_ids)
        time.sleep(sleep_s)

    print("sync complete; RAGFlow chunk embedding jobs submitted.")
    return 0


def cmd_diff(tier: str) -> int:
    load_env()
    host = ragflow_host()
    dataset_id = os.getenv("RAGFLOW_DATASET_ID", "").strip()
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip()
    if not dataset_id or not api_key:
        print("RAGFLOW_DATASET_ID / RAGFLOW_API_KEY required", file=sys.stderr)
        return 1

    remote = list_remote_documents(host, dataset_id, api_key)
    by_name = {d["name"]: d for d in remote if d.get("name")}

    local_paths = iter_local_md(tier)
    missing: list[str] = []
    stale: list[tuple[str, int, int]] = []
    ok: list[str] = []

    for p in local_paths:
        rel = p.relative_to(OP_DIR).as_posix()
        base = p.name
        loc_size = p.stat().st_size
        doc = by_name.get(base)
        if not doc:
            missing.append(rel)
            continue
        rem_size = int(doc.get("size") or 0)
        if rem_size != loc_size:
            stale.append((rel, loc_size, rem_size))
        else:
            ok.append(rel)

    dup_remote: list[str] = []
    for name in sorted(by_name):
        if name.endswith(".md") and re.search(r"\(\d+\)\.md$", name):
            dup_remote.append(name)

    meta_on_remote = [
        n
        for n in by_name
        if n in SKIP_REL_NAMES or n.endswith("MANIFEST.json") or n.endswith("MANIFEST(1).json")
    ]

    print(f"tier={tier} local_files={len(local_paths)} remote_docs_total={len(remote)}")
    print(f"  ok_size_match={len(ok)} missing={len(missing)} stale_size={len(stale)}")
    print(f"  remote_duplicate_suffix_md={len(dup_remote)} meta_or_audit_on_remote={len(meta_on_remote)}")

    if missing:
        print("\n## Missing on RAGFlow (upload these basenames)")
        for rel in missing:
            print(f"  {rel}")

    if stale:
        print("\n## Stale on RAGFlow (size != op/; re-upload after delete old doc)")
        for rel, loc, rem in sorted(stale, key=lambda x: -abs(x[1] - x[2])):
            print(f"  {rel}  local={loc}  remote={rem}")

    if dup_remote:
        print("\n## Remote (N) duplicates (delete after canonical doc is refreshed)")
        for name in dup_remote:
            canon = norm_duplicate_basename(name)
            print(f"  {name}  -> canonical basename {canon}")

    if meta_on_remote:
        print("\n## Non-retrieval docs on dataset (consider removing from RAGFlow)")
        for n in meta_on_remote:
            print(f"  {n}")

    # deprecated still on disk
    deprecated_present = []
    for old in load_deprecated_old_basenames():
        if (OP_DIR / "RAG_qiskit_human_eval_runtime" / old).is_file():
            canonical = None
            mf = OP_DIR / "RAG_qiskit_human_eval_runtime" / "MANIFEST.json"
            if mf.is_file():
                dep = json.loads(mf.read_text()).get("deprecated_merge_before_reingest") or {}
                canonical = dep.get(old)
            deprecated_present.append((old, canonical or "?"))
    if deprecated_present:
        print("\n## op/ deprecated runtime pairs (merge in git, then delete remote old names)")
        for old, new in deprecated_present:
            on_r = old in by_name or new in by_name
            print(f"  keep {new}, retire {old}  (remote has basename: {on_r})")

    return 0


def cmd_stage_l2() -> int:
    staging = OP_DIR / "kb_upload_staging"
    staging.mkdir(parents=True, exist_ok=True)
    for rel in sorted(tier_l2_relpaths()):
        src = OP_DIR / rel
        if not src.is_file():
            print(f"skip missing {rel}")
            continue
        dst = staging / src.name
        dst.write_bytes(src.read_bytes())
        print(f"staged {src.name}")
    print(f"done -> {staging.resolve()} ({len(list(staging.glob('*.md')))} files)")
    return 0


def download_document_content(
    host: str, dataset_id: str, api_key: str, document_id: str
) -> bytes:
    """GET raw file bytes for a dataset document."""
    url = f"http://{host}/api/v1/datasets/{dataset_id}/documents/{document_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, timeout=300)
    resp.raise_for_status()
    ctype = (resp.headers.get("content-type") or "").lower()
    if "json" in ctype:
        try:
            payload = resp.json()
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get("code") not in (None, 0):
            raise RuntimeError(
                f"download failed for {document_id}: {payload.get('message') or payload}"
            )
    return resp.content


def op_relpath_by_basename() -> dict[str, str]:
    """Map basename -> first matching op/ relative path (for --layout op)."""
    mapping: dict[str, str] = {}
    for p in OP_DIR.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(OP_DIR).as_posix()
        if rel.startswith(SKIP_REL_PREFIXES):
            continue
        mapping.setdefault(p.name, rel)
    return mapping


def safe_filename(name: str) -> str:
    """Avoid path traversal; keep RAGFlow names like foo(1).md."""
    name = name.replace("\\", "/").split("/")[-1]
    if not name or name in (".", ".."):
        raise ValueError(f"invalid document name: {name!r}")
    return name


def cmd_download(out_dir: Path, layout: str, limit: int | None) -> int:
    load_env()
    host = ragflow_host()
    dataset_id = os.getenv("RAGFLOW_DATASET_ID", "").strip()
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip()
    if not dataset_id or not api_key:
        print("RAGFLOW_DATASET_ID / RAGFLOW_API_KEY required", file=sys.stderr)
        return 1

    out_dir = out_dir.resolve()
    flat_dir = out_dir / "files"
    flat_dir.mkdir(parents=True, exist_ok=True)
    op_map = op_relpath_by_basename() if layout in ("op", "both") else {}

    remote = list_remote_documents(host, dataset_id, api_key)
    if limit is not None:
        remote = remote[:limit]

    index: list[dict] = []
    errors: list[str] = []

    for i, doc in enumerate(remote, 1):
        doc_id = doc.get("id") or ""
        name = safe_filename(doc.get("name") or doc_id)
        try:
            body = download_document_content(host, dataset_id, api_key, doc_id)
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

        flat_path = flat_dir / name
        if flat_path.exists() and flat_path.stat().st_size != len(body):
            flat_path = flat_dir / f"{doc_id}_{name}"

        flat_path.write_bytes(body)

        rel_op = op_map.get(name)
        op_path = None
        if layout in ("op", "both") and rel_op:
            dest = out_dir / "by_op_layout" / rel_op
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            op_path = str(dest.relative_to(out_dir))

        index.append(
            {
                "id": doc_id,
                "name": name,
                "size": doc.get("size"),
                "downloaded_bytes": len(body),
                "run": doc.get("run"),
                "chunk_count": doc.get("chunk_count"),
                "path_flat": str(flat_path.relative_to(out_dir)),
                "path_op_layout": op_path,
            }
        )
        if i % 50 == 0 or i == len(remote):
            print(f"downloaded {i}/{len(remote)}", flush=True)

    meta = {
        "dataset_id": dataset_id,
        "host": host,
        "document_count": len(index),
        "layout": layout,
        "errors": errors,
        "documents": index,
    }
    (out_dir / "index.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {out_dir / 'index.json'} ({len(index)} ok, {len(errors)} errors)")
    if errors:
        for line in errors[:20]:
            print("  error:", line)
        if len(errors) > 20:
            print(f"  ... {len(errors) - 20} more")
    return 0 if not errors else 2


def load_deprecated_old_basenames() -> set[str]:
    mf = OP_DIR / "RAG_qiskit_human_eval_runtime" / "MANIFEST.json"
    if mf.is_file():
        dep = json.loads(mf.read_text(encoding="utf-8")).get(
            "deprecated_merge_before_reingest"
        ) or {}
        if dep:
            return set(dep.keys())
    return {old for old, _ in DEPRECATED_BASENAME_PAIRS}


def update_runtime_manifest_remove_deprecated() -> list[str]:
    """Drop retired basenames from MANIFEST.json files list; return removed names."""
    mf = OP_DIR / "RAG_qiskit_human_eval_runtime" / "MANIFEST.json"
    if not mf.is_file():
        return []
    data = json.loads(mf.read_text(encoding="utf-8"))
    retired = load_deprecated_old_basenames()
    files = data.get("files") or []
    new_files = [f for f in files if f not in retired]
    removed = [f for f in files if f in retired]
    if new_files != files:
        data["files"] = new_files
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return removed


def cmd_retire_deprecated(dry_run: bool, run_sync: bool) -> int:
    """Remove deprecated runtime .md from op/ and RAGFlow; optionally re-sync L2 canon."""
    load_env()
    host = ragflow_host()
    dataset_id = os.getenv("RAGFLOW_DATASET_ID", "").strip()
    api_key = os.getenv("RAGFLOW_API_KEY", "").strip()
    if not dataset_id or not api_key:
        print("RAGFLOW_DATASET_ID / RAGFLOW_API_KEY required", file=sys.stderr)
        return 1

    retired = load_deprecated_old_basenames()
    runtime_dir = OP_DIR / "RAG_qiskit_human_eval_runtime"

    print(f"deprecated basenames to retire ({len(retired)}):")
    for name in sorted(retired):
        print(f"  {name}")

    for name in sorted(retired):
        path = runtime_dir / name
        if path.is_file():
            print(f"op/ delete: {path.relative_to(OP_DIR)}")
            if not dry_run:
                path.unlink()

    if not dry_run:
        removed = update_runtime_manifest_remove_deprecated()
        if removed:
            print(f"MANIFEST.json removed: {removed}")

    remote = list_remote_documents(host, dataset_id, api_key)
    delete_ids: list[str] = []
    for doc in remote:
        name = doc.get("name") or ""
        if name in retired:
            delete_ids.append(doc["id"])
            print(f"ragflow delete: {name} id={doc['id']}")

    if delete_ids:
        if dry_run:
            print(f"dry-run: would delete {len(delete_ids)} remote document(s)")
        else:
            delete_documents(host, dataset_id, api_key, delete_ids)
            print(f"deleted {len(delete_ids)} remote document(s)")
    else:
        print("no deprecated documents on RAGFlow")

    if dry_run:
        if run_sync:
            print("dry-run: would run sync --tier l2 after retire")
        return 0

    if run_sync:
        return cmd_sync("l2", dry_run=False, batch_size=10, sleep_s=2.0)
    return 0


def cmd_plan_l2() -> int:
    """Print env vars for refreshing L2 via rag_txt.ipynb staging."""
    rels = sorted(tier_l2_relpaths())
    staging = OP_DIR / "kb_upload_staging"
    print("# L2 refresh plan (no writes)")
    print(f"# 1. Merge deprecated runtime pairs in op/ (see DEPRECATED_BASENAME_PAIRS in {Path(__file__).name})")
    print("# 2. In RAGFlow UI: delete stale basenames + (1) duplicates listed by `diff --tier l2`")
    print(f"# 3. Copy {len(rels)} files to {staging}/ then upload once per basename")
    print("# 4. Re-parse chunks; run user_rag + --production-eval")
    print("\nexport RAGFLOW_UPLOAD_DIR=./kb_upload_staging")
    print("unset RAGFLOW_UPLOAD_DRY_RUN")
    print("\n# files:")
    for rel in rels:
        print(rel)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="op/ vs RAGFlow KB inventory")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_diff = sub.add_parser("diff", help="Compare local md with remote document list")
    p_diff.add_argument(
        "--tier",
        choices=("l2", "all", "api"),
        default="all",
        help="l2=HumanEval runtime/topics/recipes; api=RAG_qiskit_api only; all=entire op kb",
    )
    sub.add_parser("plan-l2", help="Print L2 file list and upload env hints")
    sub.add_parser("stage-l2", help="Copy L2 manifest files to op/kb_upload_staging/")
    p_dl = sub.add_parser("download", help="Download all documents from RAGFlow dataset")
    p_dl.add_argument(
        "--out",
        type=Path,
        default=OP_DIR / "ragflow_export",
        help="Output directory (default: op/ragflow_export)",
    )
    p_dl.add_argument(
        "--layout",
        choices=("flat", "op", "both"),
        default="both",
        help="flat=files/ by remote name; op=by_op_layout/ mirroring op/ paths when basename matches",
    )
    p_dl.add_argument("--limit", type=int, default=None, help="Download first N documents only")
    p_sync = sub.add_parser(
        "sync",
        help="Delete changed/missing remote docs and re-upload from op/ (+ parse/vectorize)",
    )
    p_sync.add_argument(
        "--tier",
        choices=("l2", "all", "api"),
        default="all",
        help="Which op/ files to reconcile (default: all KB markdown)",
    )
    p_sync.add_argument("--dry-run", action="store_true", help="Only print planned changes")
    p_sync.add_argument("--batch-size", type=int, default=10)
    p_sync.add_argument("--sleep", type=float, default=2.0, help="Seconds between upload batches")
    p_retire = sub.add_parser(
        "retire-deprecated",
        help="Delete deprecated runtime basenames from op/ and RAGFlow, then sync L2",
    )
    p_retire.add_argument("--dry-run", action="store_true")
    p_retire.add_argument(
        "--no-sync",
        action="store_true",
        help="Only delete; do not run sync --tier l2 afterward",
    )
    args = parser.parse_args()
    if args.cmd == "diff":
        return cmd_diff(args.tier)
    if args.cmd == "plan-l2":
        return cmd_plan_l2()
    if args.cmd == "stage-l2":
        return cmd_stage_l2()
    if args.cmd == "download":
        return cmd_download(args.out, args.layout, args.limit)
    if args.cmd == "sync":
        return cmd_sync(args.tier, args.dry_run, args.batch_size, args.sleep)
    if args.cmd == "retire-deprecated":
        return cmd_retire_deprecated(args.dry_run, run_sync=not args.no_sync)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
