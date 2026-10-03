from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_circuit_layout
from qiskit.providers.fake_provider import GenericBackendV2


def plot_circuit_layout_bell():
    """Plot the circuit layout for a Bell circuit transpiled to a backend.

    Builds a 2-qubit Bell circuit, transpiles it for a generic backend and
    returns the matplotlib Figure produced by ``plot_circuit_layout``.
    """
    qc = QuantumCircuit(2, name="bell")
    qc.h(0)
    qc.cx(0, 1)

    backend = GenericBackendV2(num_qubits=5)
    transpiled = transpile(qc, backend)
    return plot_circuit_layout(transpiled, backend)
