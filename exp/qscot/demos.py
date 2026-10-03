"""P21 Q-SCoT few-shot demonstrations — QSCOT_DEMOS_V1 (protocol-revised).

Status: HUMAN_REVIEW_REQUIRED before any formal 143-task run.
Source: manually constructed teaching tasks (NOT sampled from local_hard).
No local_hard requirements, reference solutions, or hidden tests were used.

Revision notes (pre-run protocol revision):
- QS_DEMO_02: Q-SCoT wording aligned with star-GHZ (common control q0).
- QS_DEMO_03: code restructured to Sequence(prep) → Branch(measure) → Sequence(return).
"""

from __future__ import annotations

from typing import Any, Dict, List

DEMOS_VERSION = "QSCOT_DEMOS_V1"
HUMAN_REVIEW_REQUIRED = True

# ---------------------------------------------------------------------------
# QS_DEMO_01 — Bell / Sequence  (unchanged theme/code)
# ---------------------------------------------------------------------------

QS_DEMO_01: Dict[str, Any] = {
    "id": "QS_DEMO_01",
    "theme": "Bell circuit with measurement (Sequence only)",
    "selection_rationale": (
        "Teaches basic quantum semantic chain: superposition → entanglement → "
        "measurement, with qubit→cbit mapping, using Sequence only."
    ),
    "requirement": (
        "Write a function `make_bell_measured() -> QuantumCircuit` that builds a "
        "2-qubit Bell (Φ+) preparation, measures both qubits into classical bits "
        "(q0→c0, q1→c1), and returns the complete QuantumCircuit. "
        "Do not take any arguments."
    ),
    "qscot": """Input / Output:
- Entrypoint: make_bell_measured() with no arguments.
- Return type: QuantumCircuit.
- Output constraint: the returned circuit must include Bell-state preparation
  and measurement of both qubits; do not return an unmeasured circuit.

Quantum Semantics:
- Resources: 2 qubits and 2 classical bits.
- Create superposition on q0 first.
- Then entangle q1 with q0: q0 is the control and q1 is the target.
- The entangling operation must follow the superposition operation.
- Measurement occurs only after state preparation is complete.
- Mapping: measure q0 into c0 and q1 into c1.
- Both qubits must be measured.

Program Structure:
Sequence:
1. Allocate the required quantum and classical resources.
2. Create superposition on the first qubit.
3. Create entanglement with the second qubit.
4. Measure both qubits with the required classical mapping.
5. Return the circuit.""",
    "code": '''from qiskit import QuantumCircuit


def make_bell_measured() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc
''',
}

# ---------------------------------------------------------------------------
# QS_DEMO_02 — GHZ / Sequence + Loop, unmeasured  (Q-SCoT wording fix only)
# ---------------------------------------------------------------------------

QS_DEMO_02: Dict[str, Any] = {
    "id": "QS_DEMO_02",
    "theme": "Parameterized GHZ preparation without measurement (Sequence + Loop)",
    "selection_rationale": (
        "Teaches input-dependent width, entanglement propagation via Loop, "
        "and the explicit constraint that measurement must not be added."
    ),
    "requirement": (
        "Write a function `build_ghz(n: int) -> QuantumCircuit` that prepares an "
        "n-qubit GHZ state and returns the QuantumCircuit without any measurement. "
        "Assume n >= 2. Do not add classical bits or measure operations."
    ),
    "qscot": """Input / Output:
- Entrypoint: build_ghz(n: int).
- Input: integer n with n >= 2 (number of qubits).
- Return type: QuantumCircuit.
- Output constraint: return an unmeasured circuit only; do not add classical
  registers or measurement.

Quantum Semantics:
- Resources: n qubits; no classical bits.
- Circuit width depends on the input n.
- First create superposition on q0.
- Use q0 as the control for each controlled operation.
- For each subsequent qubit i, use qubit i as the target.
- These controlled operations entangle all qubits into the required GHZ state.
- Do not measure; the caller must receive a pure state-preparation circuit.

Program Structure:
Sequence:
1. Create an n-qubit circuit with no classical register.
2. Prepare initial superposition on q0.
Loop:
3. For each i from 1 to n-1:
   entangle qubit i with q0 using q0 as the control.
Sequence:
4. Return the unmeasured circuit.""",
    "code": '''from qiskit import QuantumCircuit


def build_ghz(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(1, n):
        qc.cx(0, i)
    return qc
''',
}

# ---------------------------------------------------------------------------
# QS_DEMO_03 — optional measurement / Sequence + Branch  (code aligned to SCoT)
# ---------------------------------------------------------------------------

QS_DEMO_03: Dict[str, Any] = {
    "id": "QS_DEMO_03",
    "theme": "Fixed 2-qubit prep with optional measurement (Sequence + Branch)",
    "selection_rationale": (
        "Teaches measurement vs no-measurement semantics, quantum→classical "
        "mapping, Branch structure, and output-contract sensitivity to a flag."
    ),
    "requirement": (
        "Write a function `build_circuit(measure: bool) -> QuantumCircuit` that "
        "always prepares the same fixed 2-qubit state (Hadamard on q0, then CX "
        "from q0 to q1). If measure is True, allocate two classical bits and "
        "measure q0→c0 and q1→c1 before returning. If measure is False, return "
        "the unmeasured circuit with no classical register."
    ),
    "qscot": """Input / Output:
- Entrypoint: build_circuit(measure: bool).
- Input: boolean measure controlling whether measurement is included.
- Return type: QuantumCircuit.
- Output constraint: when measure is True, the circuit must include measurement
  with explicit classical mapping; when measure is False, the circuit must remain
  unmeasured (no classical bits, no measure ops).

Quantum Semantics:
- Always perform the same fixed state preparation on 2 qubits:
  superposition on q0, then entangle q1 controlled by q0.
- State preparation and measurement are separate stages.
- Measurement may be added only when the input requests it.
- If measurement is required: use 2 classical bits; map q0→c0 and q1→c1;
  measure only after preparation.
- If measurement is not required: do not introduce a classical register or
  measurement operations.

Program Structure:
Sequence:
1. Prepare the fixed 2-qubit quantum state.
Branch:
2. If measurement is required:
   Sequence:
   - Add classical measurement resources.
   - Apply the qubit-to-classical mapping.
   Else:
   Sequence:
   - Preserve the unmeasured circuit.
Sequence:
3. Return the circuit.""",
    "code": '''from qiskit import ClassicalRegister, QuantumCircuit


def build_circuit(measure: bool) -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    if measure:
        c = ClassicalRegister(2, "c")
        qc.add_register(c)
        qc.measure([0, 1], c)

    return qc
''',
}

DEMOS: List[Dict[str, Any]] = [QS_DEMO_01, QS_DEMO_02, QS_DEMO_03]
DEMO_ORDER = ["QS_DEMO_01", "QS_DEMO_02", "QS_DEMO_03"]


def get_demos() -> List[Dict[str, Any]]:
    by_id = {d["id"]: d for d in DEMOS}
    return [by_id[i] for i in DEMO_ORDER]
