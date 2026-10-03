from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeOslo


def transpile_circuit_dense():
    """Transpile and map a Bell circuit for FakeOslo using dense layout.

    Uses a preset pass manager with optimization_level=1 and the dense
    layout method.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    backend = FakeOslo()
    pass_manager = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
        layout_method="dense",
    )
    return pass_manager.run(qc)
