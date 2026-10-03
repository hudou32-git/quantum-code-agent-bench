from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit.primitives import BackendSampler


def noisy_bell():
    """Transpile a Bell circuit with optimization level 1, run it on the Aer
    simulator via the Qiskit Sampler primitive, and return the counts."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    backend = AerSimulator()
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    transpiled = pm.run(qc)

    sampler = BackendSampler(backend=backend)
    result = sampler.run(transpiled).result()
    quasi_dists = result.quasi_dists[0]

    shots = result.metadata[0].get("shots", 1024)
    counts = {}
    for state, prob in quasi_dists.items():
        counts[format(state, "02b")] = round(prob * shots)

    return counts
