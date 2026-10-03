from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import Sampler


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

    sampler = Sampler()
    result = sampler.run([transpiled]).result()
    quasi_dists = result.quasi_dists[0]

    counts = {}
    for state, prob in quasi_dists.items():
        bitstring = format(state, "02b")
        counts[bitstring] = round(prob * 1024)

    return counts
