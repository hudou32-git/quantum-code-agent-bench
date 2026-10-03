from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2


def noisy_bell():
    """Transpile a Bell circuit with optimization level 1, run it on the Aer
    simulator via the Qiskit Sampler primitive, and return the counts."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    backend = AerSimulator()
    transpiled = transpile(qc, backend=backend, optimization_level=1)

    sampler = SamplerV2(mode=backend)
    result = sampler.run([transpiled], shots=1024).result()

    return result[0].data.c.get_counts()
