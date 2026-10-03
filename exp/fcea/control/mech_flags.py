"""MECH-1 flag registry (实验MECH-1, protocol frozen 2026-09-30).

Every flag defaults to False so that, with no overrides, every existing
variant (incl. deurc_noctx_full42 / deurq_fix) behaves byte-identically.
The per-arm matrices below are the frozen arm definitions; the runner wires
them into the variant constants at config level (deferred hook, see
docs/实验MECH-1_协议.md 附录 B). This module is additive: nothing in the
frozen code paths imports it.
"""
from __future__ import annotations

MECH_FLAG_NAMES = (
    "mech_env_probe",            # E: episode-start environment probe
    "mech_api_probe_tool",       # A: ApiProbe tool (resolved contract)
    "mech_preflight",            # B: L1 preflight gate before Eval (non-official)
    "mech_failure_ledger",       # C: failed-signature ledger in feedback
    "mech_focus_coverage",       # D-F: FOCUS eligibility requires contract coverage
    "mech_auto_contract_probe",  # D1: boundary auto targeted contract probe
    "mech_directive_v2",         # FOCUS/ESCAPE directive wording (v2)
)

MECH_DEFAULTS: dict[str, bool] = {name: False for name in MECH_FLAG_NAMES}

# Frozen arm matrices (docs/实验MECH-1_协议.md §3)
MECH_ARM_FLAGS: dict[str, dict[str, bool]] = {
    "mech1_prev": {
        "mech_env_probe": True, "mech_api_probe_tool": True,
        "mech_preflight": True,
    },
    "mech1_rep": {
        "mech_api_probe_tool": True, "mech_preflight": True,
        "mech_failure_ledger": True, "mech_focus_coverage": True,
        "mech_auto_contract_probe": True, "mech_directive_v2": True,
    },
    "mech1_full": {name: True for name in MECH_FLAG_NAMES},
}

# Frozen engineering constants (protocol §3/§8; change = protocol amendment)
MECH_CONSTANTS = {
    "auto_probe_max_per_episode": 2,
    "auto_probe_max_per_boundary": 1,
    "preflight_timeout_s": 8,
    "preflight_reject_cap_per_shot": 3,
    "api_probe_target_max_len": 120,
}

_ARM_ALIASES = {
    "rq5_fcea_qhe_deurc_mech1_prev": "mech1_prev",
    "rq5_fcea_qhe_deurc_mech1_rep": "mech1_rep",
    "rq5_fcea_qhe_deurc_mech1_full": "mech1_full",
}


def is_mech_tag(tag: str | None) -> bool:
    return bool(tag) and tag in _ARM_ALIASES


def flags_for_tag(tag: str | None) -> dict[str, bool]:
    """Frozen flags for a MECH-1 arm tag; all-False for anything else."""
    arm = _ARM_ALIASES.get(tag or "")
    return {**MECH_DEFAULTS, **(MECH_ARM_FLAGS[arm] if arm else {})}


def flags_for_variant(variant: str | None) -> dict[str, bool]:
    """Variant-name access (for config-level wiring): 'mech1_prev' etc.

    Ladder-experiment variants (E0-E3, docs/book/实验.md v3) MUST be wired
    explicitly in EXPERIMENTAL_ARM_FLAGS — an experimental variant registered
    in fcfg.VARIANTS but missing here fails fast instead of silently
    degrading to all-False (which would mislabel an arm). Legacy variants
    keep the historical .get() fallback untouched.
    """
    v = variant or ""
    if v in EXPERIMENTAL_VARIANTS:
        if v not in EXPERIMENTAL_ARM_FLAGS:
            raise ValueError(
                f"experimental variant {v!r} lacks explicit MECH wiring; "
                "register it in EXPERIMENTAL_ARM_FLAGS (may be {} for none)")
        src = EXPERIMENTAL_ARM_FLAGS[v]
        flags = MECH_ARM_FLAGS[src] if isinstance(src, str) else src
        return {**MECH_DEFAULTS, **flags}
    return {**MECH_DEFAULTS, **MECH_ARM_FLAGS.get(v, {})}


# Ladder experiment (2026-10-01): E1/E2 carry no MECH mechanisms (explicitly
# empty); E3 = deurq_baseenv carries the frozen mech1_rep set by alias.
# E3-new / E4 (docs/E3_E4_ACCEPTANCE_PIPELINE.md, 2026-10-01 freeze):
#   deurq_baseenv_v2 = E2 + Z3_complete (mech1_rep + gate-bound salvage +
#                      submission-path coverage; supersedes deurq_baseenv,
#                      which is LEGACY — kept byte-identical, audit-only)
#   deurq_final      = E3-new + Z4 (semantic alignment gate, acceptance.py)
EXPERIMENTAL_VARIANTS = ("deurq_z1", "deurq_base", "deurq_baseenv",
                         "deurq_baseenv_v2", "deurq_final",
                         "deurq_baseenv_noz2", "deurq_final_noz2")
# Legacy marker: era-1 E3 arm. Analysis scripts must not mix it into the
# E3-new/E4 ladder (supersession reason: implementation contract did not
# fully match intended Z3 intervention semantics — gate-unbound salvage
# path and uncovered submission paths; NOT an empirical failure).
LEGACY_SUPERSEDED_VARIANTS = ("deurq_baseenv",)
EXPERIMENTAL_ARM_FLAGS = {
    "deurq_z1": {},                    # E1: no Z3 mechanisms
    "deurq_base": {},                  # E2: no Z3 mechanisms
    "deurq_baseenv": "mech1_rep",      # E3 (LEGACY, era-1): Z3 = mech1_rep
    "deurq_baseenv_v2": "mech1_rep",   # E3-new: same frozen Z3 mechanism set
    "deurq_final": "mech1_rep",        # E4: Z3 unchanged + Z4 (acceptance.py)
    # D-ladder (2026-10-03): E3−Z2 / E4−Z2. Same frozen Z3 set; Z2 removal is
    # structural (loop deu_state tuple / FSM lists / notice gate), so the MECH
    # wiring is identical to the parent arms.
    "deurq_baseenv_noz2": "mech1_rep",  # D2 = E3 − Z2
    "deurq_final_noz2": "mech1_rep",    # D3 = E4 − Z2
}
assert set(EXPERIMENTAL_VARIANTS) <= set(EXPERIMENTAL_ARM_FLAGS)
