from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

try:
    from qiskit_ibm_runtime.fake_provider import FakeOslo
except ImportError:  # pragma: no cover
    from qiskit.providers.fake_provider import FakeOslo


def transpile_circuit_dense():
    """Transpile a Bell circuit for FakeOslo using optimization level 1 and dense layout."""
    backend = FakeOslo()

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    pass_manager = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
        layout_method="dense",
    )

    return pass_manager.run(qc)
