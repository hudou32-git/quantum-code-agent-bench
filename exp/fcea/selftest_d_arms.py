"""D-ladder (E3−Z2 / E4−Z2) arm selftests — stub client, zero API calls.

Covers the 2026-10-03 Z2-ablation variants (user-directed deepseek-flash
follow-up to the E0-E3 ladder):
  D2  deurq_baseenv_noz2 = E3 − Z2: mech1_rep Z3 set present, Z2 absent
      (no deu_state / no notice / FSM disabled), Z0 exec guards on
  D3  deurq_final_noz2 = E4 − Z2: D2 + acceptance pipeline (z3 gates) +
      Z4 armed-lifecycle wiring active
  INV frozen-dict byte-identity: every pre-existing variant constant dict is
      unchanged by the D-ladder additions; NOZ2 dicts carry no Z2 keys
  REG FSM registry: no cross-arm leakage (mirrors selftest_arms test D)

Run: python3 -m exp.fcea.selftest_d_arms
"""
from __future__ import annotations

from exp.fcea import config as fcfg
from exp.fcea.control.mech_flags import flags_for_variant
from exp.fcea.loop import run_fcea
from exp.fcea.utility import commitment_state as fsm_mod
from exp.fcea.selftest_arms import (CASE, ScriptClient, GOOD_CODE,
                                    _batch_call, _probe_queries)

_PASS = 0


def check(name: str, cond: bool) -> None:
    global _PASS
    if not cond:
        raise AssertionError(f"selftest_d_arms FAILED: {name}")
    _PASS += 1
    print(f"  ok  {name}")


# ---------------------------------------------------------------- INV: dicts
def test_frozen_dicts() -> None:
    print("A. frozen-dict invariants (existing arms byte-identical)")
    z1 = {**fcfg.DEURC_NOCTX_CONSTANTS,
          "exec_retry_corrective": True, "exec_length_fuse_cap": 2,
          "exec_artifact_gate": True, "exec_slot_salvage": True,
          "exec_probe_budget": True}
    check("INV: DEURQ_Z1_CONSTANTS unchanged", fcfg.DEURQ_Z1_CONSTANTS == z1)

    from exp.fcea.control.mech_flags import MECH_ARM_FLAGS
    mech = {k: True for k, v in MECH_ARM_FLAGS["mech1_rep"].items() if v}
    check("INV: DEURQ_BASEENV_CONSTANTS = BASE + mech1_rep",
          fcfg.DEURQ_BASEENV_CONSTANTS == {**fcfg.DEURQ_BASE_CONSTANTS, **mech})
    check("INV: DEURQ_FINAL_CONSTANTS = BASEENV_V2 + z4 flags",
          fcfg.DEURQ_FINAL_CONSTANTS == {**fcfg.DEURQ_BASEENV_V2_CONSTANTS,
                                         "z4_trace_gate": True,
                                         "z4_arm_defer_when_z3": True})

    check("INV: BASEENV_NOZ2 = Z1 + mech1_rep (exactly)",
          fcfg.DEURQ_BASEENV_NOZ2_CONSTANTS == {**z1, **mech})
    check("INV: FINAL_NOZ2 = BASEENV_NOZ2 + z3 gates + z4 flags",
          fcfg.DEURQ_FINAL_NOZ2_CONSTANTS == {
              **fcfg.DEURQ_BASEENV_NOZ2_CONSTANTS,
              "z3_gate_salvage": True, "z3_fallback_gate": True,
              "z4_trace_gate": True, "z4_arm_defer_when_z3": True})
    # Dict-level Z2 marker = the FSM guard keys only (the controller constants
    # like focus_min_evidence are shared by the whole deurc stack incl. E1 by
    # design — inert there because deu_state is None and the notice gate is
    # closed; Z2 removal is behavioral at those two sites + the FSM registry).
    fsm_keys = ("fsm_g1_terminate", "fsm_g2_chain", "fsm_g3_evidence_guard",
                "fsm_g4_hysteresis", "fsm_g5_best_q")
    check("INV: NOZ2 dicts carry no FSM (Z2) keys",
          not (set(fsm_keys) & set(fcfg.DEURQ_BASEENV_NOZ2_CONSTANTS))
          and not (set(fsm_keys) & set(fcfg.DEURQ_FINAL_NOZ2_CONSTANTS)))

    for v in ("deurq_baseenv_noz2", "deurq_final_noz2"):
        check(f"INV: flags_for_variant({v!r}) = mech1_rep map",
              flags_for_variant(v) == {**{k: False for k in (
                  "mech_env_probe", "mech_api_probe_tool", "mech_preflight",
                  "mech_failure_ledger", "mech_focus_coverage",
                  "mech_auto_contract_probe", "mech_directive_v2")}, **mech})


# --------------------------------------------------------- D2: E3 − Z2 episode
def test_d2() -> None:
    print("B. D2 (deurq_baseenv_noz2): Z3 present, Z2 absent")
    script = [("tool", _batch_call(_probe_queries(1))),
              (GOOD_CODE, "stop")]
    with _variant("deurq_baseenv_noz2"):
        row = run_fcea(CASE, ScriptClient(script),
                       tag="rq4_fcea_darms_d2", bench="qhe")
    check("D2: variant tagged", row["variant"] == "deurq_baseenv_noz2")
    check("D2: reaches a real grade", row.get("passed") is not None)
    check("D2: Z2 state absent (deu_trace empty, deu_state_final None)",
          not (row.get("deu_trace") or [])
          and row.get("deu_state_final") is None)
    check("D2: Z2 notice absent (zero priority injections)",
          not row.get("priority_injections"))
    check("D2: FSM registry cleared after episode", fsm_mod.fsm_active() == [])
    mf = row.get("mech_flags") or {}
    check("D2: Z3 mech1_rep set active in-row",
          all(mf.get(k) for k in ("mech_api_probe_tool", "mech_preflight",
                                  "mech_failure_ledger", "mech_focus_coverage",
                                  "mech_auto_contract_probe",
                                  "mech_directive_v2")))
    check("D2: Z4 inactive (no rq4b_trace lifecycle)",
          not (row.get("rq4b_trace") or {}))


# --------------------------------------------------------- D3: E4 − Z2 episode
def test_d3() -> None:
    print("C. D3 (deurq_final_noz2): D2 + acceptance pipeline + Z4 wiring")
    script = [("tool", _batch_call(_probe_queries(1))),
              (GOOD_CODE, "stop")]
    with _variant("deurq_final_noz2"):
        row = run_fcea(CASE, ScriptClient(script),
                       tag="rq4_fcea_darms_d3", bench="qhe")
    check("D3: variant tagged", row["variant"] == "deurq_final_noz2")
    check("D3: reaches a real grade", row.get("passed") is not None)
    check("D3: Z2 state absent (deu_trace empty, deu_state_final None)",
          not (row.get("deu_trace") or [])
          and row.get("deu_state_final") is None)
    check("D3: Z2 notice absent", not row.get("priority_injections"))
    check("D3: FSM registry cleared after episode", fsm_mod.fsm_active() == [])
    check("D3: Z4 armed-lifecycle accounting present (rq4b_trace)",
          isinstance(row.get("rq4b_trace"), dict)
          and "armed_count" in (row.get("rq4b_trace") or {})
          and "z4_armed" in row)


# ------------------------------------------------------------- registry leak
def _variant(name):
    class _V:
        def __init__(self, n):
            self.name, self.prev = n, fcfg.VARIANT

        def __enter__(self):
            fcfg.set_variant(self.name)

        def __exit__(self, *a):
            fcfg.set_variant(self.prev)
    return _V(name)


def test_registry_no_leak() -> None:
    print("D. FSM registry: no cross-arm leakage with the D arms")
    with _variant("deurq_final"):
        run_fcea(CASE, ScriptClient([("tool", _batch_call(_probe_queries(1))),
                                     (GOOD_CODE, "stop")]),
                 tag="rq4_fcea_darms_leak1", bench="qhe")
    check("after E4 episode the registry is G1-G5",
          fsm_mod.fsm_active() == ["G1", "G2", "G3", "G4", "G5"])
    with _variant("deurq_final_noz2"):
        run_fcea(CASE, ScriptClient([("tool", _batch_call(_probe_queries(1))),
                                     (GOOD_CODE, "stop")]),
                 tag="rq4_fcea_darms_leak2", bench="qhe")
    check("after D3 episode in the SAME process the registry is cleared",
          fsm_mod.fsm_active() == [])


def main() -> None:
    test_frozen_dicts()
    test_d2()
    test_d3()
    test_registry_no_leak()
    print(f"selftest_d_arms: {_PASS} checks passed")


if __name__ == "__main__":
    main()
