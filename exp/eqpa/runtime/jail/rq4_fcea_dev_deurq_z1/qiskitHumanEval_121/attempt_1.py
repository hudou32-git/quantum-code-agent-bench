from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def conditional_two_qubit_circuit():
    """Build a one-qubit circuit with two classical bits.

    The qubit is initialized in a random state via a Hadamard gate, then
    measured into the first classical bit. If the measurement outcome is 1,
    an X gate is applied to flip the qubit back to |0>.
    """
    q = QuantumRegister(1, 'q')
    c = ClassicalRegister(2, 'c')
    qc = QuantumCircuit(q, c)

    qc.h(0)
    qc.measure(0, 0)
    with qc.if_test((c[0], 1)):
        qc.x(0)

    return qc
