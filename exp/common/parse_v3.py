"""v3 extractor prototype: candidate enumeration -> ast validation -> semantic ranking.

NOT wired into any arm. Production paths keep extract_module_v2 until the next
protocol bump; this module exists so the next-generation parser can be tested
against historical traces (docs/results/xfix_20260915) without touching v5.

Design (review directives, 2026-09-17):
  1. Collect candidates from ALL fenced blocks; python/py/python3/qiskit tags
     rank first, unknown/absent tags stay in the pool instead of being dropped.
  2. Bare text is only a candidate when no fence exists — and never because it
     merely contains "def " (kills the v1 prose-trap).
  3. Whether a candidate is Python is decided by ast.parse, not by first-word
     whitelists.
  4. Rank parseable candidates: defines entry point > defines def/class/import >
     plain valid module; full modules outrank bare call examples.
  5. If the entry point is known, "defines it" is the strongest signal.
  6. If nothing parses, return code="" with diagnostics instead of a guessed
     string.

Run the regression harness: python3 -m exp.common.parse_regress
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

_FENCE_TAGS = {"python", "py", "python3", "qiskit"}


@dataclass
class ExtractionResult:
    code: str
    source: str = ""  # "fenced_tagged" | "fenced_untagged" | "fenced_unknown_tag" | "bare"
    candidate_index: int = -1
    parse_ok: bool = False
    defines_entry_point: bool = False
    defines_defs: bool = False  # any FunctionDef/AsyncFunctionDef/ClassDef/Import
    is_call_example: bool = False
    recovery_used: bool = False  # v3 is not a fallback layer; always False
    diagnostics: list = field(default_factory=list)


def _ast_facts(tree: ast.AST | None, entry: str) -> tuple[bool, bool, bool]:
    """(defines_entry, defines_defs, is_call_example) from a parsed tree."""
    defines_entry = False
    defines_defs = False
    calls_or_exprs_only = True
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defines_defs = True
            if entry and node.name == entry:
                defines_entry = True
            calls_or_exprs_only = False
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            defines_defs = True
            calls_or_exprs_only = False
        elif isinstance(node, ast.Assign):
            calls_or_exprs_only = False
    if entry and not defines_entry:
        # entry point may be defined via dynamic assignment; cheap second look
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == entry:
                        defines_entry = True
    return defines_entry, defines_defs, calls_or_exprs_only


def _candidates(text: str) -> list[tuple[str, str]]:
    """[(kind, code)] in document order. kind ∈ fenced_tagged/untagged/unknown_tag."""
    t = (text or "").replace("\r\n", "\n")
    out: list[tuple[str, str]] = []
    if "```" in t:
        parts = t.split("```")
        for i in range(1, len(parts), 2):
            p = parts[i]
            if not p.strip():
                continue
            first = p.split("\n", 1)[0].strip().lower()
            body = p.split("\n", 1)[1] if "\n" in p else ""
            if first.split(" ")[0] in _FENCE_TAGS or first in _FENCE_TAGS:
                out.append(("fenced_tagged", body.strip()))
            elif first:
                # unknown language tag: keep in the pool, ranked lower
                out.append(("fenced_unknown_tag", body.strip()))
            else:
                out.append(("fenced_untagged", p.strip()))
        # unterminated trailing fence: ```python ...\n<EOF>
        if len(parts) % 2 == 1:
            m = re.search(r"```(?:python|py|python3|qiskit)[ \t]*\n([\s\S]+)$", t, re.I)
            if m and m.group(1).strip():
                out.append(("fenced_tagged", m.group(1).strip()))
    else:
        out.append(("bare", t.strip()))
    return out


def extract_module_v3(text: str, entry_point: str | None = None) -> ExtractionResult:
    entry = (entry_point or "").strip()
    diags: list[str] = []
    best: ExtractionResult | None = None
    best_key: tuple | None = None
    for idx, (kind, code) in enumerate(_candidates(text)):
        if not code:
            continue
        try:
            tree = ast.parse(code)
            parses = True
        except SyntaxError as exc:
            parses = False
            diags.append(
                f"candidate[{idx}] {kind}: SyntaxError: {exc.msg} (line {exc.lineno})"
            )
        if parses:
            defines_entry, defines_defs, call_example = _ast_facts(tree, entry)
            # Bare text must at least define something to count as a module
            # (expression-only bare answers are prose/REPL, not gradeable code).
            eligible = kind != "bare" or defines_defs
            if not eligible:
                diags.append(
                    f"candidate[{idx}] bare: parses but defines no def/class/import (prose?)"
                )
        else:
            defines_entry = defines_defs = call_example = False
            # Fenced blocks stay eligible even when unparseable (truncated
            # fence -> SyntaxError feedback is more informative than an empty
            # extraction); bare text never does — that resurrects the v1
            # prose-trap.
            eligible = kind != "bare"
            if kind == "bare":
                diags.append(f"candidate[{idx}] bare: SyntaxError without any fence (prose)")
        if not eligible:
            continue
        key = (
            1 if parses else 0,                      # parseable beats garbage
            1 if defines_entry else 0,               # entry-point signal: strongest
            1 if kind == "fenced_tagged" else 0,     # tagged fence over unknown/untagged
            0 if call_example else 1,                # full module over call example
            1 if defines_defs else 0,                # defines something over comments-only
            -idx,                                    # earlier candidate wins ties
        )
        if best_key is None or key > best_key:
            best_key = key
            best = ExtractionResult(
                code=code,
                source=kind,
                candidate_index=idx,
                parse_ok=parses,
                defines_entry_point=defines_entry,
                defines_defs=defines_defs,
                is_call_example=call_example,
                diagnostics=diags,
            )
    if best is None:
        return ExtractionResult(code="", diagnostics=diags or ["no candidates found"])
    return best
