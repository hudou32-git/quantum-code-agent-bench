from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_state_city


def plot_circuit_layout_bell():
    """Plot a city_state for a Bell circuit.

    Builds a Bell circuit (H on qubit 0 followed by CX(0, 1)),
    computes its statevector and returns the city plot of the
    resulting quantum state.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    state = Statevector(qc)
    return plot_state_city(state)
