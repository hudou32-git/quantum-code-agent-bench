from qiskit.circuit.library import QFT
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import (
    FakeOsaka,
    FakeSherbrooke,
    FakeBrisbane,
)


def _instruction_cost(circuit):
    cost = 0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in ("ecr", "cx", "cz", "cy", "swap", "rxx", "ryy", "rzz", "rzx"):
            cost += 5
        elif name == "rz":
            cost += 1
        else:
            cost += 2
    return cost


def backend_with_highest_complexity():
    qft = QFT(4)
    backends = [FakeOsaka(), FakeSherbrooke(), FakeBrisbane()]
    highest = None
    for backend in backends:
        pm = generate_preset_pass_manager(
            optimization_level=3,
            seed_transpiler=1234,
            backend=backend,
        )
        transpiled = pm.run(qft)
        cost = _instruction_cost(transpiled)
        if highest is None or cost > highest:
            highest = cost
    return highest
