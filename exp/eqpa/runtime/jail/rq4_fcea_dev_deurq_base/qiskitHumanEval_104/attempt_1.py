from qiskit.circuit.library import QFT
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import (
    FakeOsaka,
    FakeSherbrooke,
    FakeBrisbane,
)


def backend_with_highest_complexity():
    """Transpile a 4-qubit QFT on three fake backends and return the highest cost.

    Cost rules: two-qubit gates cost 5, rz gates cost 1, all other gates cost 2.
    """
    backends = [FakeOsaka(), FakeSherbrooke(), FakeBrisbane()]

    highest_cost = 0
    for backend in backends:
        pm = generate_preset_pass_manager(
            optimization_level=3,
            backend=backend,
            seed_transpiler=1234,
        )
        transpiled = pm.run(QFT(4))

        cost = 0
        for instruction in transpiled.data:
            operation = instruction.operation
            if operation.num_qubits == 2:
                cost += 5
            elif operation.name == "rz":
                cost += 1
            else:
                cost += 2

        if cost > highest_cost:
            highest_cost = cost

    return highest_cost
