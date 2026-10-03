from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def conditional_two_qubit_circuit():
    """Create a one-qubit circuit with two classical bits.

    The qubit's state is randomized with a Hadamard gate, then measured into
    the first classical bit.  If the measurement outcome is 1, an X gate is
    applied (conditioned on the classical register) to flip the qubit back to
    |0>.  The classical register is named 'c'.
    """
    q = QuantumRegister(1, 'q')
    c = ClassicalRegister(2, 'c')
    qc = QuantumCircuit(q, c)

    # Randomize the qubit's initial state.
    qc.h(0)

    # Measure the qubit into the first classical bit.
    qc.measure(0, 0)

    # If the measurement outcome is 1, flip the qubit back to |0>.
    with qc.if_test((c, 1)):
        qc.x(0)

    return qc
