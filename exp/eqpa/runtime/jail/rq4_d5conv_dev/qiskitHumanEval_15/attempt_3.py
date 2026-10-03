from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2


def noisy_bell():
    """Transpile a Bell circuit with optimization level 1, run it on the Aer
    simulator via the Qiskit Sampler primitive, and return the execution counts."""
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    backend = AerSimulator()
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    transpiled = pm.run(qc)

    sampler = SamplerV2()
    result = sampler.run([transpiled]).result()
    return result[0].data.c.get_counts()
