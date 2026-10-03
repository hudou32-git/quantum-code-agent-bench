from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_circuit_layout
from qiskit.providers.fake_provider import GenericBackendV2


def plot_circuit_layout_bell():
    """Plot the circuit layout for a Bell circuit.

    Builds a 2-qubit Bell circuit, transpiles it for a generic backend and
    returns the matplotlib Figure produced by ``plot_circuit_layout``.
    """
    bell = QuantumCircuit(2, 2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure(range(2), range(2))

    backend = GenericBackendV2(num_qubits=5)
    new_circ_lv3 = transpile(bell, backend=backend, optimization_level=3)
    return plot_circuit_layout(new_circ_lv3, backend)
