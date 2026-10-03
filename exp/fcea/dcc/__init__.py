"""DCC arm namespace: Depth-Conditioned Commitment Controller (2026-09-29).

Variant "dcc" on the unchanged deurc-noctx stack; the decision layer is the
frozen depth schedule in policy.py. See exp/fcea/dcc/policy.py docstring for
provenance and docs/analysis/stage0_f1_control_census_20260929.md for the
supporting census.
"""
from exp.fcea.dcc.controller import DEFAULT_CONSTANTS, DCCController
from exp.fcea.dcc.policy import COMMIT, FOCUS, SEARCH, select

__all__ = ["DCCController", "DEFAULT_CONSTANTS", "select",
           "SEARCH", "FOCUS", "COMMIT"]
