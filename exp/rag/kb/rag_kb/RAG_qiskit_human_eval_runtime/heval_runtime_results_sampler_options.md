# HumanEval-Qiskit: PrimitiveResult, DataBin, SamplerOptions, reading counts

## Metadata
- Topics: `PrimitiveResult`, `DataBin`, `meas`, `SamplerOptions`, `seed_simulator`, `get_counts`, `get_bitstrings`

## Result object shape (runtime Sampler v2)
After `job = sampler.run([circuit], shots=100)`:
```python
    result = job.result()
    counts = result[0].data.meas.get_counts()
    bitstrings = result[0].data.meas.get_bitstrings()
```
- Index with `[0]` for the first pub/circuit.
- Use `.data.meas` for measured circuits; some tasks use classical register name `.data.c` when prompt pattern matches `StatevectorSampler` style — **follow the prompt imports and tests**.

## Common AttributeError fixes
- Wrong: `result.data` or `result.quasi_dists`
- Wrong: `PrimitiveResult` without `[0]` index
- Wrong: `result[0].data.meas` when measurement register is named differently — use `get_counts()` on the bin provided by the task canonical pattern

## Seeding (HumanEval tasks with seed 42)
Do **not** pass `seed=` to `Sampler()`. Use options:
```python
    from qiskit_ibm_runtime.options import SamplerOptions
    options = SamplerOptions()
    options.simulator.seed_simulator = 42
    sampler = Sampler(mode=AerSimulator(), options=options)
    job = sampler.run([qc])
    return job.result()[0].data.meas.get_counts()
```

## ValidationError on SamplerOptions
- Unexpected keyword `shots` on `SamplerOptions` — pass `shots=` to `sampler.run([qc], shots=1000)` instead.
- Unexpected keyword `seed` on constructor — use `options.simulator.seed_simulator`.

## Multiple circuits in one job
```python
    job = sampler.run((circuit_a, circuit_b))
    results = job.result()
    counts_list = [r.data.meas.get_counts() for r in results]
```

## Retrieval tags
result_api_schema, DataBin, meas, get_counts, get_bitstrings, SamplerOptions, seed_simulator, shots, HumanEval

## Questions this answers
- How to read counts from qiskit_ibm_runtime Sampler result?
- PrimitiveResult has no attribute data
- DataBin has no attribute meas
- Set Aer simulator seed for Sampler HumanEval task
