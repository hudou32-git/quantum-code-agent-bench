from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_circuit_layout
from qiskit.providers.fake_provider import GenericBackendV2


def plot_circuit_layout_bell():
    """Plot the circuit layout for a Bell circuit transpiled to a backend."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    backend = GenericBackendV2(num_qubits=5)
    transpiled = transpile(qc, backend)
    return plot_circuit_layout(transpiled, backend)
