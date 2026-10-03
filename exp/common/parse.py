"""Parse model output into a REPL snippet or a Python module."""

from __future__ import annotations

import re

from exp.common.grader_qhe import extract_python


def extract_repl(text: str) -> str | None:
    text = text or ""
    m = re.search(
        r"```(?:repl(?:[ \t]+python)?|[ \t]*\nrepl)\s*\n([\s\S]*?)```",
        text,
        re.I,
    )
    if m:
        return _strip_nested_fence(m.group(1))
    if "```repl" in text:
        parts = text.split("```")
        for i, part in enumerate(parts):
            head = part.strip().split("\n", 1)
            if head[0].strip().lower() in {"repl", "repl python"}:
                body = head[1] if len(head) > 1 else ""
                return _strip_nested_fence(body)
    m = re.search(r"<repl>\s*([\s\S]*?)\s*</repl>", text)
    if m:
        return _strip_nested_fence(m.group(1))
    return None


def _strip_nested_fence(body: str) -> str:
    body = (body or "").strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        if body.rstrip().endswith("```"):
            body = body.rstrip()[: -3]
    return body.strip()


def extract_module(text: str) -> str:
    code = extract_python(text)
    head = (code or "").lstrip()
    if head.startswith("from ") or head.startswith("import ") or head.startswith("def "):
        return code
    return ""


def recover_module(text: str) -> str:
    """Last resort when extract_module found nothing module-shaped.

    The v1 gate (from/import/def first line) discarded complete fenced modules
    whose first statement is try:/class/docstring (defensive-import style).
    Recover the last python-tagged fence body that contains code markers,
    including an unterminated trailing fence. Only ever called on v1-empty
    output, so it cannot change a previously extracted result.
    """
    text = (text or "").replace("\r\n", "\n")
    if "```" not in text:
        return ""
    parts = text.split("```")
    candidates: list[str] = []
    for i in range(1, len(parts), 2):
        p = parts[i]
        if not p.strip():
            continue
        first = p.split("\n", 1)[0].strip().lower()
        body = p.split("\n", 1)[1] if "\n" in p else ""
        if first in {"python", "py", "qiskit"}:
            candidates.append(body)
        elif not first and ("def " in p or "import " in p or "class " in p):
            candidates.append(p)
    if not candidates:
        m = re.search(r"```(?:python|py|qiskit)[ \t]*\n([\s\S]+)$", text, re.I)
        if m:
            candidates.append(m.group(1))
    for body in reversed(candidates):
        b = body.strip()
        if "def " in b or "import " in b or "class " in b:
            return b
    return ""


def extract_module_v2(text: str) -> str:
    """extract_module with the recovery fallback. Identical on v1 successes."""
    return extract_module(text) or recover_module(text)


def extraction_status(text: str) -> dict:
    """Diagnostic label for a model turn — never changes extraction behavior.

    Distinguishes infrastructure failures from capability failures in traces:
      ok          v1 gate accepted the extraction
      recovered   v1 returned empty, recover_module salvaged it (historical
                  xfix_20260915 pattern: docstring/try-first modules)
      empty       no module-shaped code found at all
    """
    if extract_module(text):
        return {"extraction_status": "ok", "extraction_recovery": False}
    if recover_module(text):
        return {"extraction_status": "recovered", "extraction_recovery": True}
    return {"extraction_status": "empty", "extraction_recovery": False}


def extract_module_last(text: str) -> str:
    """Last complete-looking fenced module. Forced-submit last resort only."""
    text = (text or "").replace("\r\n", "\n")
    if "```" not in text:
        return extract_module(text)
    found: list[str] = []
    parts = text.split("```")
    for part in parts:
        p = part.strip()
        if not p:
            continue
        first = p.split("\n", 1)[0].strip().lower()
        body = p.split("\n", 1)[1] if "\n" in p else ""
        if first in {"python", "py", "qiskit"}:
            chunk = body.strip()
        elif "def " in p or p.startswith("from ") or p.startswith("import "):
            chunk = p
        else:
            continue
        head = chunk.lstrip()
        if head.startswith("from ") or head.startswith("import ") or head.startswith("def "):
            found.append(chunk.strip())
    return found[-1] if found else extract_module(text)
