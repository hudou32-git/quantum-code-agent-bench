from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.visualization import plot_circuit_layout


def plot_circuit_layout_bell():
    """Plot the circuit layout of a Bell circuit.

    Builds a 2-qubit Bell circuit, transpiles it for a small fake backend,
    and returns the matplotlib Figure produced by ``plot_circuit_layout``.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    backend = GenericBackendV2(num_qubits=5)
    transpiled = transpile(qc, backend=backend, optimization_level=1)

    return plot_circuit_layout(transpiled, backend)
