"""FCEA prompts: system prompt lives in config (byte-shared across variants);
this module re-exports the shared workspace/probe-budget texts from the
Batch-EQPA branch so wording stays identical."""
from __future__ import annotations

from exp.evidence_eqpa.prompts import (  # noqa: F401 (re-exported)
    PROBE_BUDGET_NOTICE,
    workspace_block,
)
