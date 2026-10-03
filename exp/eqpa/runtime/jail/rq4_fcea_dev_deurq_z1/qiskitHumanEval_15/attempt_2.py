from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit.primitives import BackendSamplerV2


def noisy_bell():
    """Create a Bell state circuit, transpile it with optimization level 1,
    run it on the Aer simulator via the Qiskit Sampler, and return counts."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    transpiled = pass_manager.run(qc)

    sampler = BackendSamplerV2(backend=backend)
    result = sampler.run([transpiled]).result()

    return result[0].data.meas.get_counts()
