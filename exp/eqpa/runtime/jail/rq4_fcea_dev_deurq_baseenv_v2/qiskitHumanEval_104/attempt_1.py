from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import (
    FakeOsaka,
    FakeSherbrooke,
    FakeBrisbane,
)


def _cost(circuit):
    """Compute the cost of the instructions of a transpiled circuit."""
    two_qubit_gates = {"cx", "ecr", "cz", "cy", "swap", "iswap", "rxx", "ryy", "rzz"}
    total = 0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in two_qubit_gates:
            total += 5
        elif name == "rz":
            total += 1
        else:
            total += 2
    return total


def backend_with_highest_complexity():
    """Transpile the 4-qubit QFT on several fake backends and return the
    highest instruction cost among them."""
    qft_circuit = QFT(4)

    backends = [FakeOsaka(), FakeSherbrooke(), FakeBrisbane()]

    costs = []
    for backend in backends:
        pass_manager = generate_preset_pass_manager(
            optimization_level=3,
            backend=backend,
            seed_transpiler=1234,
        )
        transpiled = pass_manager.run(qft_circuit)
        costs.append(_cost(transpiled))

    return max(costs)
