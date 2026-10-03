"""v6 controlled baseline: five tool-free arms, no system prompt, .env-driven model.

v6 protocol window (user directive, 2026-09-17): decoding temperature 0.6
package-wide (exp.config.TEMPERATURE) and pass@3 for the four single-turn
arms — k independent samples per problem, any-pass counts, no feedback
between samples. v5 rows (T=0, single shot) stay frozen under e4_base_v5_*.
"""

from __future__ import annotations

from exp import config
from exp.common.llm import resolve_model

# Model identity comes from .env DEEPSEEK_MODEL (single source of truth).
# Channel gating removed (user directive, 2026-09-16): the endpoint in .env
# (official or DMX proxy) is used as-is and recorded in protocol.json.
MODEL = resolve_model()
MODEL_FAMILY = MODEL
LLM_PROVIDER = "deepseek"
MAX_OFFICIAL = 3
ARMS = ("oneshot", "cot", "qscot", "rag", "loop", "loop_cot", "loop_qscot", "loop_rag")
SINGLE_TURN = frozenset({"oneshot", "cot", "qscot", "rag"})
# v6 loop family: adaptive EF×3 schedule. loop_X arms change ONLY the first
# shot's prompt — byte-identical to arm X's first shot — while rounds 2-3 use
# the standard typed-error feedback rounds unchanged (user directive, 2026-09-17).
LOOP_FAMILY = frozenset({"loop", "loop_cot", "loop_qscot", "loop_rag"})
FIRST_SHOT_OF = {"loop_cot": "cot", "loop_qscot": "qscot", "loop_rag": "rag"}
# v6: single-turn arms sample PASS_K independent solutions per problem
# (pass@k: any sample passing the official eval makes the problem pass).
PASSK_ARMS = frozenset({"oneshot", "cot", "qscot", "rag"})
PASS_K = 3
# v7 (user directive, 2026-09-20): unified e7 protocol — T=0.6, max_tokens=40960,
# thinking disabled, conda-qhe grading (conda_qhe_spawn). v6 rows ran at 4096
# under the legacy grader env and are frozen under e4_base_v6_*.
# v7 addendum (user directive, 2026-09-21): loop-family feedback rounds use the
# official QuanBench+ feedback template verbatim (attempt framing + stage label
# + repair instruction + previous-code echo; source: quanbench-plus
# feedback_loop/feedback_prompt.py) — superseding both the v4/v5/v6 typed
# templates and the interim bare-error design. The error gate remains our
# official KL grading (not the official in-process trial).
PROTO_VERSION = "v8"
# Must equal exp.config.TEMPERATURE; asserted in the selftest so the pin
# cannot drift silently. Frozen per tag in protocol.json.
DECODING_TEMPERATURE = config.TEMPERATURE
PROTOCOL_DOC = "docs/protocols/e4_baseline_grid_plan.md"

LOCKED_TAGS = frozenset({"e3"})


def normalize_arm(arm: str) -> str:
    a = (arm or "").strip().lower()
    if a in {"q-scot", "scot"}:
        a = "qscot"
    if a not in ARMS:
        raise ValueError(f"unknown baseline arm {arm!r}; use one of {ARMS}")
    return a


def normalize_bench(bench: str) -> str:
    b = (bench or "qhe").strip().lower()
    if b in {"qbplus_qiskit", "quanbench+", "quanbench_plus"}:
        b = "qbplus"
    if b not in {"qhe", "qbplus"}:
        raise ValueError(f"unknown bench {bench!r}")
    return b


def default_tag(arm: str, *, bench: str = "qhe", dev: bool = False, pass_k: int | None = None) -> str:
    a = normalize_arm(arm)
    b = normalize_bench(bench)
    # v6: passk arms always carry the sample count in the tag
    # (e4_base_v6_passk3_<arm>); loop is e4_base_v6_loop (decoding bumped
    # from v5 by the 0.6 temperature pin). Historical families:
    # e4_base_v5_* = T0 single shot, e4_base_v4_* = system-prompt era — both locked.
    if a in PASSK_ARMS:
        k = PASS_K if pass_k is None else int(pass_k)
        tag = f"e4_base_{PROTO_VERSION}_passk{k}_{a}"
    else:
        tag = f"e4_base_{PROTO_VERSION}_{a}"
    if b == "qbplus":
        tag = f"{tag}_qbplus"
    if dev and not tag.endswith("_dev"):
        tag = f"{tag}_dev"
    return tag


def refuse_locked_tag(tag: str) -> None:
    t = (tag or "").strip()
    if (
        t in LOCKED_TAGS
        or t.startswith("e4_iso")
        or t.startswith("e4_qhe_ef_loop")
        or t.startswith("e4_base_v4_")
        or t.startswith("e4_base_v5_")
        or t.startswith("e4_base_v6_")  # frozen 2026-09-20: v6 ran 4096 + legacy grader env
        or t.startswith("e4_mini_v1")  # mini_v1 archived 2026-09-17: docs/results/e4_mini_v1_archive_20260917.md
    ):
        raise ValueError(
            f"refusing to write locked tag {t}; use e4_base_v8_* "
            "(T=0.6, max_tokens=40960, thinking disabled, conda-qhe grading)"
        )


def require_model(model: str) -> str:
    """No channel/model gating: accept the configured model id as-is."""
    m = (model or "").strip()
    if not m:
        raise RuntimeError("REFUSE: empty model id")
    return m
