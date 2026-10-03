"""Plot a circuit layout for a Bell circuit on a fake backend."""

from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_circuit_layout
from qiskit.providers.fake_provider import Fake5QV1


def plot_circuit_layout_bell():
    """Create a Bell circuit, transpile it for a fake backend and plot its layout.

    Returns:
        matplotlib.figure.Figure: The figure produced by
        :func:`qiskit.visualization.plot_circuit_layout`.
    """
    # Build a Bell circuit.
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    # A small fake backend to transpile against.
    backend = Fake5QV1()

    # Transpile so the circuit has a layout for the backend.
    transpiled = transpile(qc, backend)

    # Plot the circuit layout.
    return plot_circuit_layout(transpiled, backend)
