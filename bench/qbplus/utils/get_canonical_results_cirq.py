"""QuanBench+ cirq handlers: GLOBAL_INPUTS + get_handler + cirq probability helpers.

Cirq-side counterpart of utils/get_canonical_results.py (qiskit). Semantics are
frozen to the upstream quanbench-plus cirq pipeline (snapshot:
bench/qbplus/dataset/eval_cirq/, 2026-09-21):

- task 06 input is the only framework-shaped object (cirq.Circuit); every other
  GLOBAL_INPUTS entry (04/29/39/40/41/42) is framework-neutral Python data.
- a completion returns either a cirq.Circuit (measured with key='result', the
  convention stated in every cirq prompt) or a dict of counts/probabilities.
- counts -> probability vector uses natural binary indexing
  (format(i, "0{nb}b")), the same orientation as the qiskit worker's primary
  probs, so the shared canonical_output vectors apply unchanged.

This module is imported only by the cirq grading worker; the qiskit path never
touches it.
"""

from __future__ import annotations

import numpy as np

TASK4_GRAPH = [[0, 3], [0, 4], [1, 3], [1, 4], [2, 3], [2, 4]]

# Framework-neutral inputs are copied verbatim from
# bench/qbplus/utils/get_canonical_results.py GLOBAL_INPUTS; only "06" is
# cirq-shaped (upstream: pass_at_k_pipeline/cirq_pip/get_cirq_results.py
# GLOBAL_INPUTS["06"] = task_6_input()).
GLOBAL_INPUTS: dict = {
    "04": None,  # filled below (networkx graph + angles)
    "06": None,  # filled below (cirq.Circuit)
    "29": [1, 0],
    "39": [((25 * np.pi) / 54), ((25 * np.pi) / 54)],
    "40": [((25 * np.pi) / 54) for _ in range(8)],
    "41": [((25 * np.pi) / 54) for _ in range(8)],
    "42": [((25 * np.pi) / 54), ((25 * np.pi) / 54), ((25 * np.pi) / 54)],
}


def _build_inputs() -> None:
    import networkx as nx

    import cirq

    g = nx.Graph()
    g.add_edges_from(TASK4_GRAPH)
    angles5 = [((25 * np.pi) / 54) for _ in range(5)]
    GLOBAL_INPUTS["04"] = [g, angles5, list(angles5)]

    q = cirq.LineQubit(0)
    GLOBAL_INPUTS["06"] = cirq.Circuit(
        cirq.H(q),
        cirq.rz((25 * np.pi) / 54)(q),
    )


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


def get_probs_dictionnary_cirq(circuit, shots: int) -> dict:
    """Upstream cirq_pip.save_cirq_responses.get_probs_dictionnary, verbatim semantics."""
    import cirq

    sim = cirq.Simulator()
    result = sim.run(circuit, repetitions=int(shots))
    data = result.measurements["result"]
    bitstrings = ["".join(str(bit) for bit in row) for row in data]
    unique, counts = np.unique(bitstrings, return_counts=True)
    return {u: c / int(shots) for u, c in zip(unique, counts)}


def counts_to_array_cirq(counts, outcomes=None, normalize: bool = True) -> np.ndarray:
    """Upstream cirq_pip save_cirq_responses.counts_to_array, verbatim semantics."""
    if isinstance(counts, list):
        counts = counts[0]
    if not isinstance(counts, dict):
        raise TypeError(f"Expected dict or list of dicts, got {type(counts)} instead.")
    counts = {"".join(k.split()): v for k, v in counts.items()}
    if outcomes is None:
        outcomes = sorted(counts.keys())
    if not outcomes:
        raise ValueError("empty counts table")
    n_bits = len(outcomes[0])
    all_outcomes = [format(i, f"0{n_bits}b") for i in range(2**n_bits)]
    arr = np.array([counts.get(k, 0) for k in all_outcomes], dtype=float)
    if normalize:
        total = arr.sum()
        if total > 0:
            arr /= total
    return arr
