from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


def conditional_two_qubit_circuit():
    q = QuantumRegister(1, 'q')
    c = ClassicalRegister(2, 'c')
    qc = QuantumCircuit(q, c)
    qc.h(0)
    qc.measure(0, 0)
    with qc.if_test((c[0], 1)):
        qc.x(0)
    return qc
