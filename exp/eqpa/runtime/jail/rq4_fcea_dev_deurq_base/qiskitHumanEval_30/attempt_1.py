from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_state_city


def plot_circuit_layout_bell():
    """Plot the city state (density matrix) of a Bell circuit.

    Builds a 2-qubit Bell state circuit, computes its statevector,
    and returns a city-state plot of the corresponding density matrix.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    state = Statevector(qc)
    return plot_state_city(state)
