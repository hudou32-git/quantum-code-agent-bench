"""ESCAPE-ablation selector (Phase 2.2 Experiment 1, variant deurc_noescape).

SINGLE override, per the ablation freeze rules: when the frozen rule selects
ESCAPE, re-select WITHOUT the escape signal (escape_worthy_family=None).
The mode then falls through to FOCUS when the focus gate holds, else to
SEARCH — the "previous safe mode". RCI, thresholds, FOCUS, evidence gate,
context gate and the evidence branch state are untouched.

The wrapper reports what the frozen DEU-RC rule WOULD have done:
  original_mode  mode selected by the frozen rule (ESCAPE when blocked)
  escape_blocked True iff the frozen rule chose ESCAPE and it was replaced
"""
from __future__ import annotations

from exp.fcea.control import mode_selector as ms


def select_mode_noescape(*, constants=None, **kwargs) -> dict:
    sel = ms.select_mode(**kwargs, constants=constants)
    if sel["mode"] != ms.ESCAPE:
        sel["original_mode"] = sel["mode"]
        sel["escape_blocked"] = False
        return sel
    kwargs = dict(kwargs)
    kwargs["escape_worthy_family"] = None      # the ablation: no escape signal
    fallback = ms.select_mode(**kwargs, constants=constants)
    return {"mode": fallback["mode"],
            "reason": "ESCAPE ablated: " + fallback["reason"],
            "original_mode": ms.ESCAPE,
            "escape_blocked": True}
