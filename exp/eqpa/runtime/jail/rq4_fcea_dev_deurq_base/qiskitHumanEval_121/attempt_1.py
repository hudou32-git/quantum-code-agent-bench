from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def conditional_two_qubit_circuit():
    """Build a one-qubit circuit with two classical bits.

    The qubit starts in a randomized state (Hadamard), is measured into
    classical bit ``c[0]``, and is flipped back to |0> with an X gate when
    the measurement outcome is 1.
    """
    q = QuantumRegister(1, 'q')
    c = ClassicalRegister(2, 'c')
    qc = QuantumCircuit(q, c)

    qc.h(0)
    qc.measure(0, c[0])

    with qc.if_test((c, 1)):
        qc.x(0)

    return qc
