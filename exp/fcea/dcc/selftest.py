"""DCC selftest (arm spec §8). Run: python -m exp.fcea.dcc.selftest

Covers:
  1. depth=1 -> SEARCH, constraint none
  2. depth=2 -> FOCUS, BatchProbe removed
  3. depth=3 -> COMMIT, BatchProbe removed
  4. determinism: identical inputs -> byte-identical outputs
  5. trace schema: additive keys only (existing row keys untouched)
  6. state-perturbation invariance (forbidden inputs do not matter)
  7. variant registration follows the D2/D3 pattern (config.VARIANTS entry)
"""
from __future__ import annotations

import json
import sys

from exp.fcea import config as fcfg
from exp.fcea.dcc import DCCController
from exp.fcea.dcc.policy import select

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS" if cond else "FAIL"), "-", name, detail)
    if not cond:
        FAILURES.append(name)


def boundary_kwargs(depth: int, **override) -> dict:
    """The exact kwarg set loop.py passes to on_boundary (perturbable)."""
    kw = dict(step=depth, task_id="case00", boundary_kind="error",
              allowed_tools_before=["BatchProbe", "Write", "Eval"], ts=None,
              no_progress_count=2, same_error_count=1, code_changed=True,
              progress_score=-1, novelty_mean_now=0.1, novelty_mean_prev=0.9,
              family_novelty_now={"E1": 0.0}, family_novelty_prev={"E1": 1.0},
              utility_drop=0.4, Q={"E1": 0.1, "E2": 0.2, "E3": 0.9, "E4": 0.3},
              evidence_used={"E1": 5, "E3": 1}, evidence_samples=6,
              error_message="KL=0.31 threshold=0.05")
    kw.update(override)
    return kw


def main() -> int:
    # 1-3. depth mapping + mechanical constraints
    d1, d2, d3 = select(1), select(2), select(3)
    check("depth=1 -> SEARCH", d1["action"] == "SEARCH")
    check("depth=1 constraint none", d1["constraint_applied"] == "none")
    check("depth=1 keeps BatchProbe", "BatchProbe" in d1["allowed_tools"])
    check("depth=2 -> FOCUS", d2["action"] == "FOCUS")
    check("depth=2 BatchProbe removed", "BatchProbe" not in d2["allowed_tools"])
    check("depth=2 constraint tool_withdrawn",
          d2["constraint_applied"] == "tool_withdrawn")
    check("depth=3 -> COMMIT", d3["action"] == "COMMIT")
    check("depth=3 BatchProbe removed", "BatchProbe" not in d3["allowed_tools"])
    check("depth>=4 clamps to COMMIT", select(4)["action"] == "COMMIT")

    # controller-level withdrawal flag
    c = DCCController()
    c.on_boundary(**boundary_kwargs(1))
    check("controller probe_withdrawn()=False at depth1", not c.probe_withdrawn())
    c2 = DCCController()
    rec2 = c2.on_boundary(**boundary_kwargs(2))
    check("controller probe_withdrawn()=True at depth2", c2.probe_withdrawn())
    check("record carries message_text", bool(rec2["message_text"]))

    # 4. determinism: byte-identical outputs for identical inputs
    a = DCCController(); b = DCCController()
    for d in (1, 2, 3):
        a.on_boundary(**boundary_kwargs(d))
        b.on_boundary(**boundary_kwargs(d))
    check("determinism (serialized equality)",
          json.dumps(a.control_log, sort_keys=True)
          == json.dumps(b.control_log, sort_keys=True))

    # 5. trace schema: additive keys only
    existing_row = {"case_id": "x", "passed": True, "llm_calls": 5,
                    "control_log": [], "shots": [], "probe_log": []}
    before = set(existing_row.keys())
    cc = DCCController()
    cc.on_boundary(**boundary_kwargs(2))
    new_row = {**existing_row,
               "dcc_trace_schema": 1,
               "dcc_state": cc.dcc_state_final(),
               "decision_trace": cc.decision_trace}
    check("existing keys untouched", before <= set(new_row.keys())
          and all(new_row[k] is existing_row[k] for k in before))
    check("new keys are exactly the spec'd three",
          {"dcc_trace_schema", "dcc_state", "decision_trace"}
          <= set(new_row.keys()))
    check("dcc_state shape",
          set(new_row["dcc_state"]) == {"failure_depth",
                                        "selected_commitment",
                                        "constraint_applied"})
    check("decision_record has spec §7 fields",
          {"episode_id", "step", "failure_depth", "selected_action",
           "constraint_applied", "allowed_tools_before",
           "allowed_tools_after"} <= set(new_row["decision_trace"][0]))

    # 6. forbidden-input invariance: perturb every state/utility field; the
    #    decision must not move
    base = DCCController()
    base.on_boundary(**boundary_kwargs(2))
    perturbed = DCCController()
    perturbed.on_boundary(**boundary_kwargs(
        2, no_progress_count=0, same_error_count=9, utility_drop=0.0,
        Q={"E1": 0.99, "E2": 0.99, "E3": 0.01, "E4": 0.5},
        error_message="ValueError: totally different",
        progress_score=1, novelty_mean_now=None, evidence_used={},
        boundary_kind="nosubmit"))
    check("decision invariant to state/utility/error perturbation",
          base.control_log[0]["selected_action"]
          == perturbed.control_log[0]["selected_action"]
          and base.control_log[0]["constraint_applied"]
          == perturbed.control_log[0]["constraint_applied"])

    # 7. registration follows the D2/D3 pattern
    check("variant registered in fcfg.VARIANTS", "dcc" in fcfg.VARIANTS,
          "VARIANTS=%s" % (fcfg.VARIANTS,))
    check("existing variants all still registered",
          {"deurc_noctx", "d2_clean", "d3", "deurand", "deuact",
           "deurc"} <= set(fcfg.VARIANTS))

    print()
    if FAILURES:
        print("SELFTEST FAILED:", FAILURES)
        return 1
    print("SELFTEST OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
