# HumanEval-Qiskit: fake_provider machine names and generate_preset_pass_manager

## Metadata
- Topics: `fake_provider`, `FakeBelemV2`, `FakeCairoV2`, `transpile`, `generate_preset_pass_manager`, `CouplingMap`, `initial_layout`

## Rule: use only the Fake* class in the prompt
The prompt line `from qiskit_ibm_runtime.fake_provider import FakeCairoV2` means you must call `FakeCairoV2()` — not invent names.

## Forbidden (ImportError / AttributeError)
- `FakeProvider`, `FakeBackendV2`, `fake_provider.FakeProvider`
- `from qiskit.providers.fake_provider import ...` (wrong package for this benchmark)

## Dataset machine names (examples — always prefer current prompt)
`FakeBelemV2`, `FakeCairoV2`, `FakeSydneyV2`, `FakeTorontoV2`, `FakePerth`, `FakeOslo`, `FakeAuckland`, `FakeAthensV2`, `FakeAlgiers`, and other `Fake*` classes explicitly imported in the task.

## Transpile-only tasks (return QuantumCircuit)
```python
    backend = FakeCairoV2()
    coupling_map = CouplingMap(backend.configuration().coupling_map)
    pass_manager = generate_preset_pass_manager(
        optimization_level=1,
        backend=backend,
        coupling_map=coupling_map,
    )
    return pass_manager.run(circuit)
```

## Optional pass manager kwargs (read docstring)
- `optimization_level=0` for trivial layout checks
- `optimization_level=3` for heavy optimization
- `initial_layout=[2, 4, 6]` when specified
- `layout_method="dense"`, `scheduling_method="alap"` when specified

## Fake device + Aer noise + Sampler
```python
    device_backend = FakeBelemV2()
    simulator = AerSimulator.from_backend(device_backend)
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=simulator)
    isa = pass_manager.run(bell)
    sampler = Sampler(mode=simulator)
    counts = sampler.run([isa], shots=1000).result()[0].data.meas.get_counts()
```

## PassManager.run arguments
- `pass_manager.run(circuit)` returns a transpiled `QuantumCircuit`.
- Do not pass `backend=` to `StagedPassManager.run` — backend belongs in `generate_preset_pass_manager(..., backend=backend)`.

## Retrieval tags
fake_provider, FakeCairoV2, FakeBelemV2, transpile, pass_manager, coupling_map, initial_layout, optimization_level, HumanEval

## Questions this answers
- Transpile circuit for Fake Cairo V2 backend using pass manager
- FakeProvider has no attribute error fix
- Noisy bell FakeBelemV2 AerSimulator.from_backend
- Custom initial layout transpile Fake Perth
