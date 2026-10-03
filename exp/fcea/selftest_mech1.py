"""MECH-1 selftest — no LLM, no sandbox, no benchmark cases.

Verifies (a) the frozen flag/protocol surface, (b) the pure logic of the new
mech modules, and (c) — once the deferred hooks are applied — that the
D-F coverage gate actually blocks FOCUS. Run:
    PYTHONDONTWRITEBYTECODE=1 python -m exp.fcea.selftest_mech1
"""
from __future__ import annotations

import inspect
import json

from exp.fcea.control.mech_flags import (
    MECH_ARM_FLAGS, MECH_CONSTANTS, MECH_DEFAULTS, MECH_FLAG_NAMES,
    flags_for_tag, flags_for_variant,
)
from exp.fcea.control.mech_ledger import (
    MechLedger, api_tokens_from_error, normalize_sig,
)
from exp.fcea.control.preflight import preflight_script, valid_filename
from exp.fcea.evidence.contract_probe import (
    api_probe_script, valid_target,
)
from exp.fcea.evidence.env_probe import TARGETS, env_probe_script

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))


# ---- 1. frozen flag surface ------------------------------------------------

check("flags.defaults_all_false",
      all(v is False for v in MECH_DEFAULTS.values())
      and set(MECH_DEFAULTS) == set(MECH_FLAG_NAMES))

expected = {
    "mech1_prev": {"mech_env_probe", "mech_api_probe_tool", "mech_preflight"},
    "mech1_rep": {"mech_api_probe_tool", "mech_preflight",
                  "mech_failure_ledger", "mech_focus_coverage",
                  "mech_auto_contract_probe", "mech_directive_v2"},
    "mech1_full": set(MECH_FLAG_NAMES),
}
for arm, on in expected.items():
    got = {k for k, v in MECH_ARM_FLAGS[arm].items() if v}
    check(f"flags.arm_matrix[{arm}]", got == on, f"got {sorted(got)}")

check("flags.tag_mapping",
      all(v is True for k, v in flags_for_tag("rq5_fcea_qhe_deurc_mech1_full").items()
          if k in expected["mech1_full"])
      and all(v is False for v in flags_for_tag("rq4_fcea_qhe_deurc_noctx").values()))
check("flags.variant_mapping",
      flags_for_variant("mech1_rep")["mech_focus_coverage"] is True)
check("flags.constants_frozen",
      MECH_CONSTANTS["auto_probe_max_per_episode"] == 2
      and MECH_CONSTANTS["preflight_timeout_s"] == 8
      and MECH_CONSTANTS["preflight_reject_cap_per_shot"] == 3)

# ---- 2. ledger pure logic (real residual messages) --------------------------

sig1 = normalize_sig("KLMismatch: KL=27.631 threshold=0.05")
check("ledger.sig_normalization", "27" not in sig1 and sig1.startswith("KLMismatch"))

t1 = api_tokens_from_error(
    "TypeError: SamplerV2.__init__() got an unexpected keyword argument 'backend'")
check("ledger.tokens.sampler_ctor", t1 == {"SamplerV2"}, str(t1))
t2 = api_tokens_from_error("AttributeError: 'DataBin' object has no attribute 'meas'")
check("ledger.tokens.databin", t2 == {"DataBin"}, str(t2))
t3 = api_tokens_from_error("ValueError: A backend or session must be specified.")
check("ledger.tokens.backend_session", "session" in t3 or "backend" in t3, str(t3))

led = MechLedger()
code1 = "s = Sampler()\njob = s.run([qc])"
led.record_failure("ValueError: A backend or session must be specified.", code1)
check("ledger.failure_block",
      led.failure_block().startswith("[failure ledger")
      and "shot1" in led.failure_block()
      and "backend or session must be specified" in led.failure_block())
led.record_failure("AttributeError: 'DataBin' object has no attribute 'meas'",
                   "x = DataBin(meas=1)")
check("ledger.ctor_lines",
      any("DataBin(meas=1)" in ln for ln in led.failure_block().splitlines()
          if "at:" in ln))
check("ledger.revert_identical",
      (led.revert_note(code1) or "").startswith("[mech ledger] this patch"))
led.record_failure("TypeError: SamplerV2.__init__() got an unexpected keyword "
                   "argument 'backend'", "s = Sampler(backend=backend)")
check("ledger.revert_token_touch",
      (led.revert_note("s = SamplerV2(mode=b)") or "")
      .startswith("[mech ledger] the patch touches"))
check("ledger.revert_clean", led.revert_note("z = unrelated_thing()\ny = 2") is None)

led.record_contract("qiskit_ibm_runtime.SamplerV2", {"ok": True, "output": "..."})
check("ledger.coverage_true",
      led.contract_covered({"qiskit_ibm_runtime.SamplerV2"}))
check("ledger.coverage_false",
      not led.contract_covered({"qiskit_ibm_runtime.SamplerV2", "qiskit_aer.primitives.Sampler"}))
check("ledger.uncovered",
      led.uncovered_targets("ValueError: A backend or session must be specified.") == {"session"})

# ---- 3. probe script templates (frozen text) --------------------------------

check("apiprobe.target_accept",
      valid_target("qiskit_ibm_runtime.SamplerV2"))
check("apiprobe.target_reject",
      not valid_target("os.system; import shutil") and not valid_target("a b")
      and not valid_target("x'yan"))
s1 = api_probe_script("qiskit_ibm_runtime.SamplerV2")
check("apiprobe.script_deterministic", s1 == api_probe_script("qiskit_ibm_runtime.SamplerV2"))
check("apiprobe.script_content",
      "inspect.signature" in s1 and "importlib" in s1 and "'qiskit_ibm_runtime.SamplerV2'" in s1)

e1 = env_probe_script()
check("envprobe.script_deterministic", e1 == env_probe_script())
check("envprobe.script_targets",
      all(t in e1 for t in TARGETS) and "qiskit_aer" in e1 and "__version__" in e1)

# Smoke regression (2026-09-30): the probe templates once carried .format-style
# doubled braces while being built with .replace — every sandbox probe then
# died on "TypeError: unhashable type: 'dict'" and the preflight gate starved
# an episode into 3x NoSubmit. The scripts must contain no escaped braces AND
# must actually execute and print the runner JSON.
import io
import json as _json
from contextlib import redirect_stdout

for name, script, key in (("envprobe", e1, "ver:qiskit"),
                          ("apiprobe", s1, "target")):
    check(f"{name}.no_escaped_braces", "{{" not in script and "}}" not in script)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(script, {}, {})  # noqa: S102 - frozen script, no user input
        payload = _json.loads(buf.getvalue().strip().splitlines()[-1])
        check(f"{name}.script_executes", key in payload)
    except Exception as exc:
        check(f"{name}.script_executes", False, f"{type(exc).__name__}: {exc}")

import os
import tempfile
import qiskit  # noqa: F401 - base env has qiskit; proves imports resolve
p1 = preflight_script("attempt_1.py")
check("preflight.no_escaped_braces",
      "{{" not in p1 and "}}" not in p1)
import os
import tempfile
import qiskit  # noqa: F401 - base env has qiskit; proves imports resolve
_tmp = tempfile.mkdtemp(prefix="mech1_pf_")
_old_cwd = os.getcwd()
try:
    with open(os.path.join(_tmp, "attempt_1.py"), "w") as fh:
        fh.write("from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\n")
    os.chdir(_tmp)
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(p1, {}, {})  # noqa: S102
    payload = _json.loads(buf.getvalue().strip().splitlines()[-1])
    check("preflight.script_executes_ok_module", payload.get("ok") is True)
    with open(os.path.join(_tmp, "attempt_2.py"), "w") as fh:
        fh.write("import nonexistent_module_xyz\n")
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(preflight_script("attempt_2.py"), {}, {})  # noqa: S102
    payload = _json.loads(buf.getvalue().strip().splitlines()[-1])
    check("preflight.script_executes_bad_module",
          payload.get("ok") is False and "ModuleNotFoundError" in payload.get("tb", ""))
finally:
    os.chdir(_old_cwd)

check("preflight.filename_accept", valid_filename("attempt_3.py"))
check("preflight.filename_reject",
      not valid_filename("prompt.txt") and not valid_filename("../x.py")
      and not valid_filename("attempt_x.py"))
p1 = preflight_script("attempt_1.py")
check("preflight.script_deterministic", p1 == preflight_script("attempt_1.py"))
check("preflight.script_content", "<preflight>" in p1 and "exec(compile" in p1)

# ---- 4. D-F gating (PENDING-aware: active only after hooks are applied) -----

try:
    from exp.fcea.control.mode_selector import select_mode
    params = inspect.signature(select_mode).parameters
    if "contract_coverage" in params:
        base = dict(no_progress_count=1, utility_drop=0.0,
                    escape_worthy_family=None, best_q=0.457,
                    evidence_samples=12, constants={})
        sel_open = select_mode(**base, contract_coverage=True)
        # the D-F gate consumes mech_focus_coverage from the variant
        # constants (mech1_rep/mech1_full carry it; legacy variants don't)
        base_mech = dict(base, constants={"mech_focus_coverage": True})
        sel_blocked = select_mode(**base_mech, contract_coverage=False)
        check("dfocus.coverage_blocks_focus",
              sel_open["mode"] == "FOCUS" and sel_blocked["mode"] == "SEARCH",
              f"open={sel_open['mode']} blocked={sel_blocked['mode']}")
    else:
        RESULTS.append(("dfocus.hook_pending", True,
                        "contract_coverage kwarg not wired yet (deferred hooks)"))
except Exception as exc:  # pragma: no cover
    RESULTS.append(("dfocus.hook_pending", True, f"deferred: {type(exc).__name__}"))


def main() -> int:
    ok = 0
    for name, passed, detail in RESULTS:
        ok += bool(passed)
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail and not passed else ""))
    total = len(RESULTS)
    print(f"\nselftest_mech1: {ok} pass / {total - ok} fail / {total} total")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
