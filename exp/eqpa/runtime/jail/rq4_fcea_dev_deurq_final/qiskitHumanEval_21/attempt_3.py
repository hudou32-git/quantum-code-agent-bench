from qiskit import QuantumCircuit
from qiskit.transpiler import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import level_1_pass_manager
from qiskit_ibm_runtime.fake_provider import FakeOslo


def transpile_circuit_dense():
    """Transpile a Bell circuit for FakeOslo using optimization level 1
    and the dense layout method.

    Returns the transpiled circuit.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)

    backend = FakeOslo()
    config = PassManagerConfig.from_backend(backend, layout_method="dense")
    pass_manager = level_1_pass_manager(config)

    return pass_manager.run(qc)
