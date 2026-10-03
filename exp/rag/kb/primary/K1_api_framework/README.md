# K1 — API / Framework (primary, core only)

- **framework_version:** 2.4.1
- **Primary documents:** 79
- **Non-core (moved, not deleted):** `../../extended/K1_api_non_core/` (399 files)
- Cull log: `../../../manifests/qiskit_k1_core_cull.csv`

## Keep policy
- `QuantumCircuit` high-frequency methods (compose/append/measure/gates/params/draw/depth/…)
- Parameters / ControlledGate helpers / AncillaRegister
- `transpile`, PassManager, Target, CouplingMap, Layout
- `Operator` / `SparsePauliOp` / `Pauli` / Clifford / fidelity helpers
- OpenQASM2/3 dump·load

## Intentionally not in primary
- Rare/multi-control gates, niche library ansatzes, nested path slices (`library_*`, `state_preparation_*`)
- No clean standalone `Statevector` class page existed in the historical API slice set (K2 covers usage)
- QFT/GroverOperator top-level library class pages were absent as clean slices here
