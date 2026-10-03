from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import Sampler


def noisy_bell():
    """Transpile a Bell circuit (optimization level 1) and run it on the Aer
    simulator via the Qiskit Sampler, returning the execution counts."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(
        optimization_level=1, backend=backend
    )
    transpiled = pass_manager.run(qc)

    sampler = Sampler()
    result = sampler.run(transpiled).result()
    quasi_dists = result.quasi_dists[0]

    counts = {format(key, "b").zfill(2): value for key, value in quasi_dists.items()}
    return counts
