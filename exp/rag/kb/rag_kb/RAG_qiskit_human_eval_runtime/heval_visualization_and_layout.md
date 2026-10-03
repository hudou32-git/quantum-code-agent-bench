# HumanEval-Qiskit: plot_histogram and plot_circuit_layout

## Metadata
- Topics: `plot_histogram`, `plot_circuit_layout`, `matplotlib`, `FakeAthensV2`, `transpile`

## plot_histogram (Bell / counts comparison)
Prompt often imports `from qiskit.visualization import plot_histogram` and `from matplotlib.figure import Figure`.
```python
    fig = plot_histogram([counts_a, counts_b], legend=["|Φ+⟩ Count", "|Φ-⟩ Count"])
    return fig
```
Run circuits with `Sampler(mode=AerSimulator())` and `sampler.run([qc], shots=1000)` separately per state, then extract counts via `result[0].data.meas.get_counts()`.

## plot_circuit_layout
Requires **transpiled circuit** and **backend** used for layout:
```python
    backend = FakeAthensV2()
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    transpiled = pass_manager.run(bell)
    return plot_circuit_layout(transpiled, backend)
```
- `plot_circuit_layout(circuit, backend)` — both arguments required (missing backend causes TypeError).

## Retrieval tags
plot_histogram, plot_circuit_layout, visualization, FakeAthensV2, Figure, HumanEval

## Questions this answers
- Visualize bell states histogram return Figure
- Plot circuit layout Fake Athens V2 transpiled bell
