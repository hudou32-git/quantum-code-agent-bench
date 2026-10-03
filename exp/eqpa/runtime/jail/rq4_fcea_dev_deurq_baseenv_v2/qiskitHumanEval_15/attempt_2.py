from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import Optimize1qGates
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import Sampler


def noisy_bell():
    """Transpile a Bell circuit with a pass manager (optimization level 1),
    run it on the Aer simulator via the Qiskit Sampler, and return counts."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    # Pass manager with optimization level 1 (light optimization).
    pm = PassManager([Optimize1qGates()])
    transpiled = pm.run(qc)

    backend = AerSimulator()
    sampler = Sampler(backend_options={"method": "statevector"})
    result = sampler.run(transpiled, shots=1024).result()
    quasi_dists = result.quasi_dists[0]

    counts = {}
    for state, prob in quasi_dists.items():
        counts[format(state, "02b")] = int(round(prob * 1024))
    return counts
