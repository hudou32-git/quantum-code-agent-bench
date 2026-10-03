from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFT
from qiskit_ibm_runtime.fake_provider import (
    FakeOsaka,
    FakeSherbrooke,
    FakeBrisbane,
)


def _cost(circuit):
    total = 0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in ("ecr", "cx", "cz", "cy", "swap", "rzz", "rzx", "rxx", "ryy"):
            total += 5
        elif name == "rz":
            total += 1
        else:
            total += 2
    return total


def backend_with_highest_complexity():
    qft = QFT(4)
    costs = []
    for backend in (FakeOsaka(), FakeSherbrooke(), FakeBrisbane()):
        transpiled = transpile(
            qft,
            backend=backend,
            optimization_level=3,
            seed_transpiler=1234,
        )
        costs.append(_cost(transpiled))
    return max(costs)
