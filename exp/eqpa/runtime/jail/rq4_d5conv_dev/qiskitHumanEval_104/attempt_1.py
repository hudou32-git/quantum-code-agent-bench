from qiskit import transpile
from qiskit.circuit.library import QFT
from qiskit_ibm_runtime.fake_provider import FakeOsaka, FakeSherbrooke, FakeBrisbane


def backend_with_highest_complexity():
    """Transpile a 4-qubit QFT on three fake backends and return the max cost."""
    qc = QFT(4)
    backends = [FakeOsaka(), FakeSherbrooke(), FakeBrisbane()]

    costs = []
    for backend in backends:
        transpiled = transpile(
            qc, backend=backend, optimization_level=3, seed_transpiler=1234
        )
        cost = 0
        for instruction in transpiled.data:
            if len(instruction.qubits) == 2:
                cost += 5
            elif instruction.operation.name == "rz":
                cost += 1
            else:
                cost += 2
        costs.append(cost)

    return max(costs)
