from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def conditional_two_qubit_circuit():
    """Create a one-qubit, two-classical-bit circuit.

    The qubit is put into a superposition with a Hadamard gate, then
    measured.  If the measurement outcome is 1, an X gate is applied
    (conditioned on the first classical bit) to flip the qubit back to
    |0>.  A second measurement records the final state.

    The classical register is named 'c' as required.
    """
    qr = QuantumRegister(1, 'q')
    cr = ClassicalRegister(2, 'c')
    qc = QuantumCircuit(qr, cr)

    # Randomize the qubit's initial state.
    qc.h(qr[0])

    # Measure into the first classical bit.
    qc.measure(qr[0], cr[0])

    # If the outcome is 1, flip the qubit back to |0>.
    with qc.if_test((cr[0], 1)):
        qc.x(qr[0])

    # Record the final state in the second classical bit.
    qc.measure(qr[0], cr[1])

    return qc
