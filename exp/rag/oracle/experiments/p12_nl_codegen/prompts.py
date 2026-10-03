"""Prompts for P12-NL generation arms. All optimized arms build on G1 contract."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SYSTEM = """You are an expert Qiskit programmer.
Generate a complete, executable Python program that solves the task.
Do not use hidden tests or reference solutions.
"""

GENERATION_CONTRACT = """Generation contract (fixed):
1. Implement exactly the required function name and arguments from the task.
2. Return one complete runnable Python module (necessary imports + full function).
3. Do not output markdown fences unless wrapping the whole program once.
4. Do not output explanations, analysis prose, or multiple alternative solutions.
5. Do not hard-code answers for individual test inputs.
6. Prefer a minimal correct implementation.
"""

PLAN_INSTRUCTION = """Before the code, write a short task-specific plan as Python comments only
(no prose outside comments), at most 80 words, using exactly:

# Requirement summary:
# Key quantum/API choices:
# Implementation plan:
# Risks:

Then output the complete program. Do not put non-comment analysis outside the code.
"""

CHECKLIST = """Generic generation checklist:
- implement the required entrypoint name and arguments;
- include necessary imports;
- use valid Qiskit 2.x APIs;
- check qubit and classical-bit indices;
- check measurement mapping and return type;
- return one complete executable program.
"""


def format_kb_docs(docs: List[Dict[str, Any]]) -> str:
    if not docs:
        return (
            "<retrieved_knowledge>\n"
            "(no documents injected)\n"
            "</retrieved_knowledge>\n"
        )
    parts = [
        "<retrieved_knowledge>",
        "General Qiskit knowledge-base excerpts (not task solutions):",
    ]
    for i, d in enumerate(docs, 1):
        eid = d.get("doc_id") or d.get("record_id") or f"doc{i}"
        title = d.get("title") or eid
        src = d.get("source_dir") or ""
        snip = (d.get("snippet") or "")[:900]
        score = d.get("score")
        sc = f"{float(score):.3f}" if score is not None else "n/a"
        parts.append(f'<document id="{eid}" source_dir="{src}" score="{sc}">')
        parts.append(f"<title>{title}</title>")
        parts.append(f"<content>\n{snip}\n</content>")
        parts.append("</document>")
    parts.append("</retrieved_knowledge>")
    return "\n".join(parts) + "\n"


def _build_qscot_fs_prompt(task: dict, *, retrieved: Optional[List[dict]] = None) -> str:
    """P21 few-shot Q-SCoT (+ optional RAG block). Used by FSE2027 QHE arms."""
    from experiments.p12_nl_codegen.p21_qscot_fewshot.prompts_fewshot import (
        QSCOT_FS_PREAMBLE,
        format_demo_qscot_fs,
    )
    from experiments.p12_nl_codegen.p21_qscot_fewshot.demonstrations.qscot_demos_v1 import (
        get_demos,
    )

    nl = (task.get("prompt") or "").strip()
    entry = task.get("entry_point") or ""
    out: List[str] = [GENERATION_CONTRACT + "\n", QSCOT_FS_PREAMBLE + "\n"]
    for i, d in enumerate(get_demos(), 1):
        out.append(format_demo_qscot_fs(d, i) + "\n")
    if retrieved is not None:
        out.append(format_kb_docs(retrieved) + "\n")
    out.append("=== Target Task ===\n\n")
    out.append(f"Requirement:\n{nl}\n\n")
    out.append(f"Required entrypoint name: `{entry}`\n\n")
    out.append(
        "First construct a concise Q-SCoT for the target task following "
        "the demonstrated pattern.\n\n"
        "Then write one complete runnable Python program satisfying "
        "the Generation Contract.\n\n"
        "Q-SCoT:\n"
    )
    return "".join(out)


def build_user_prompt(
    arm: str,
    task: dict,
    *,
    retrieved: Optional[List[dict]] = None,
    prior_code: Optional[str] = None,
    feedback: Optional[str] = None,
    round_idx: int = 1,
) -> str:
    nl = task["prompt"]
    entry = task.get("entry_point") or ""
    parts: List[str] = []

    if round_idx == 1 and prior_code is None:
        # Few-shot Q-SCoT arms (P21 / FSE2027)
        if arm == "G2_QSCOT_FS":
            return _build_qscot_fs_prompt(task, retrieved=None)
        if arm == "G4_RAG_QSCOT_FS":
            return _build_qscot_fs_prompt(task, retrieved=retrieved or [])

        parts.append("Task (natural language):\n")
        parts.append(nl.strip() + "\n\n")
        parts.append(f"Required entrypoint name: `{entry}`\n\n")

        if arm != "G0_RAW":
            parts.append(GENERATION_CONTRACT + "\n")

        if arm == "C2_CHECKLIST":
            parts.append(CHECKLIST + "\n")

        if arm in {"G2_PLAN", "G4_RAG_PLAN"}:
            parts.append(PLAN_INSTRUCTION + "\n")

        if arm in {"G2_ZS", "G2_COT"}:
            from experiments.p12_nl_codegen.p20_ps_scot.prompts_ps_scot import (
                ZS_INSTRUCTION,
            )

            parts.append(ZS_INSTRUCTION.rstrip() + "\n\n")

        if arm in {"G3_RAG", "G4_RAG_PLAN", "C1_SHUFFLED_RAG", "G4_RAG_QSCOT_FS"}:
            parts.append(format_kb_docs(retrieved or []) + "\n")

        if arm == "G0_RAW":
            parts.append(
                "Output one complete Python program only "
                "(imports + the required function).\n"
            )
        else:
            parts.append("Output one complete Python program satisfying the contract.\n")
        return "".join(parts)

    # Iterative rounds: revise frozen parent code with feedback
    parts.append("Revise the program using public execution feedback only.\n")
    parts.append(f"Required entrypoint name: `{entry}`\n\n")
    parts.append(GENERATION_CONTRACT + "\n")
    parts.append(f"Original task:\n{nl.strip()}\n\n")
    parts.append(f"Current program:\n```python\n{(prior_code or '').strip()}\n```\n\n")
    parts.append(f"Public execution feedback:\n{(feedback or '').strip()}\n\n")
    parts.append(f"Rounds already used: {round_idx - 1} (max 3).\n\n")

    plan_arms = {"I1_PLAN_EF_B3", "I3_RAG_PLAN_EF_B3", "E1_PLAN_EF", "E3_RAG_PLAN_EF"}
    rag_arms = {
        "I2_RAG_EF_B3",
        "I3_RAG_PLAN_EF_B3",
        "E2_RAG_EF",
        "E3_RAG_PLAN_EF",
        "E_RAG_QSCOT_EF",
    }
    if arm in plan_arms:
        parts.append(PLAN_INSTRUCTION + "\n")
    if arm in {"E_QSCOT_EF", "E_RAG_QSCOT_EF"}:
        parts.append(
            "Before the corrected code, write a brief Q-SCoT "
            "(Input/Output, Quantum Semantics, Program Structure).\n\n"
        )
    if arm in rag_arms:
        parts.append(format_kb_docs(retrieved or []) + "\n")

    parts.append("Output one complete corrected Python program only.\n")
    return "".join(parts)
