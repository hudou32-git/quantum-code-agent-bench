# HumanEval-Qiskit Topic: runtime Sampler, transpile, bitstrings and counts

## Metadata
- Kind: `human_eval_topic_recipe`
- Topics: `Sampler`, `AerSimulator`, `generate_preset_pass_manager`, `bell_each_shot`, `get_bitstrings`, `get_counts`, `HumanEval`

## Imports (typical)
`from qiskit import QuantumCircuit`  
`from qiskit_aer import AerSimulator`  
`from qiskit_ibm_runtime import Sampler`  
`from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager`

## End-to-end pattern
```python
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()
    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa_circuit = pass_manager.run(bell)
    sampler = Sampler(mode=backend)
    result = sampler.run([isa_circuit], shots=100).result()
    memory = result[0].data.meas.get_bitstrings()
    return memory
```

## Critical API
- `Sampler(mode=backend)` — never `Sampler(backend=...)`.
- `sampler.run([isa_circuit], shots=N)` — list wrapper required.
- Counts: `result[0].data.meas.get_counts()`.

## Retrieval tags
bell_each_shot, run_bell_state_simulator, Sampler mode, AerSimulator, transpile optimization level 1, get_bitstrings, get_counts, HumanEval runtime

## Questions this answers
- Run phi plus Bell circuit Qiskit Sampler Aer simulator transpile pass manager optimization level 1
- Return measurement results for each shot get_bitstrings HumanEval
