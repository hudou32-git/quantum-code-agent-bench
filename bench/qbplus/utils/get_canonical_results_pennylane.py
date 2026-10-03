"""QuanBench+ pennylane handlers: GLOBAL_INPUTS + get_handler + sample->probs.

Pennylane-side counterpart of utils/get_canonical_results.py (qiskit) and
utils/get_canonical_results_cirq.py. Semantics are frozen to the upstream
quanbench-plus pennylane pipeline (snapshot:
bench/qbplus/dataset/eval_pennylane/, 2026-09-21):

- task 06 input is the only framework-shaped object: a QNode returning
  qml.state() (upstream feedback_loop.pennylane_handlers.task_6_input_pennylane);
  every other GLOBAL_INPUTS entry (04/29/39/40/41/42) is framework-neutral
  Python data.
- a completion returns a qml.sample() numpy array with the shot count declared
  inside the model code's device spec (the prompts fix 1000 shots) — unlike
  qiskit/cirq, the grader never samples on its own.
- get_probs_pennylane replicates upstream
  pass_at_k_pipeline/pennylane_pip/save_pennylane_responses.get_probs verbatim,
  including the TypeError raised on 1-D float arrays: that failure mode is part
  of the official grading contract, not a bug to fix.
- sample rows decode with first wire = MSB (binary_array_to_decimal), so the
  shared canonical_output vectors apply unchanged.

This module is imported only by the pennylane grading worker; the qiskit and
cirq paths never touch it.
"""

from __future__ import annotations

import numpy as np

TASK4_GRAPH = [[0, 3], [0, 4], [1, 3], [1, 4], [2, 3], [2, 4]]

# Framework-neutral inputs are copied verbatim from
# bench/qbplus/utils/get_canonical_results.py GLOBAL_INPUTS; only "06" is
# pennylane-shaped (upstream:
# pass_at_k_pipeline/pennylane_pip/get_pennylane_results.py
# GLOBAL_INPUTS["06"] = task_6_input()).
GLOBAL_INPUTS: dict = {
    "04": None,  # filled below (networkx graph + angles)
    "06": None,  # filled below (QNode returning qml.state())
    "29": [1, 0],
    "39": [((25 * np.pi) / 54), ((25 * np.pi) / 54)],
    "40": [((25 * np.pi) / 54) for _ in range(8)],
    "41": [((25 * np.pi) / 54) for _ in range(8)],
    "42": [((25 * np.pi) / 54), ((25 * np.pi) / 54), ((25 * np.pi) / 54)],
}


def task_6_input_pennylane():
    """Upstream feedback_loop/pennylane_handlers.py task_6_input_pennylane, verbatim."""
    import pennylane as qml

    dev = qml.device("default.qubit", wires=1)

    @qml.qnode(dev)
    def circuit():
        qml.Hadamard(wires=0)
        qml.RZ((25 * np.pi) / 54, wires=0)
        return qml.state()

    return circuit


def _build_inputs() -> None:
    import networkx as nx

    g = nx.Graph()
    g.add_edges_from(TASK4_GRAPH)
    angles5 = [((25 * np.pi) / 54) for _ in range(5)]
    GLOBAL_INPUTS["04"] = [g, angles5, list(angles5)]
    GLOBAL_INPUTS["06"] = task_6_input_pennylane()


_build_inputs()


def execute_code_with_args(code: str, entry_point: str, *args):
    ns: dict = {}
    exec(code, ns, ns)  # noqa: S102 - sandboxed grading worker, upstream contract
    func = ns.get(entry_point)
    if not callable(func):
        raise RuntimeError(f"Entry point '{entry_point}' not found or not callable.")
    return func(*args)


def get_handler(x, code: str, entry_point: str, inputs: dict):
    """Mirrors utils/get_canonical_results.py get_handler dispatch table."""
    handlers = {
        "04": lambda: execute_code_with_args(
            code, entry_point, inputs[x][0], inputs[x][1], inputs[x][2]
        ),
        "06": lambda: execute_code_with_args(code, entry_point, inputs[x]),
        "29": lambda: execute_code_with_args(
            code, entry_point, inputs[x][0], inputs[x][1]
        ),
        "39": lambda: execute_code_with_args(code, entry_point, inputs[x]),
        "40": lambda: execute_code_with_args(code, entry_point, inputs[x]),
        "41": lambda: execute_code_with_args(code, entry_point, inputs[x]),
        "42": lambda: execute_code_with_args(
            code, entry_point, inputs[x][0], inputs[x][1], inputs[x][2]
        ),
    }
    func = handlers.get(str(x).zfill(2), lambda: execute_code_with_args(code, entry_point))
    return func()


def binary_array_to_decimal(bits):
    """
    bits: list like [1, 0, 1] representing the binary number 101
    returns: decimal integer (here, 5)

    Upstream save_pennylane_responses.binary_array_to_decimal, verbatim
    (first wire = MSB; strict 0/1 validation raises ValueError).
    """
    value = 0
    for b in bits:
        # optional: basic validation
        if b not in (0, 1):
            raise ValueError("All elements must be 0 or 1")
        value = value * 2 + b
    return value


def get_probs_pennylane(task_id, solution, entry_point, shots, inputs) -> np.ndarray:
    """Upstream save_pennylane_responses.get_probs, verbatim semantics.

    Branches on the completion's qml.sample() array:
    - 2-D (rows = bit-string samples): count rows by first-wire-MSB decimal,
      normalize by the number of samples;
    - 1-D float: upstream raises TypeError (wrong return type) — kept as the
      official contract;
    - other 1-D numeric: binary classification [P(<=0), P(>0)];
    - non-ndarray: TypeError.
    `shots` is accepted for upstream signature fidelity and ignored there:
    the sample count lives in the model code's device spec.
    """
    circuit_or_counts = get_handler(task_id, solution, entry_point, inputs)
    if isinstance(circuit_or_counts, np.ndarray):
        batta = circuit_or_counts.tolist()
        if type(batta[0]) is list:
            counts = [0] * (2 ** len(batta[0]))
            for sample in batta:
                counts[binary_array_to_decimal(sample)] += 1
            for j in range(len(counts)):
                counts[j] /= len(batta)
        elif type(batta[0]) is float:
            raise TypeError(
                "Model return expected value or sampled on a specified basis, wrong return type"
            )
        else:
            counts = [0, 0]
            for i in range(len(batta)):
                if batta[i] > 0:
                    counts[1] += 1
                else:
                    counts[0] += 1
            counts[0] /= len(batta)
            counts[1] /= len(batta)

    else:
        raise TypeError(f"Expected numpy array, got {type(circuit_or_counts)} instead.")
    return np.array(counts)
