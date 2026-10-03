# GHZ state preparation (Qiskit)

## Goal
Prepare the n-qubit GHZ⁺ state:
`(|0...0> + |1...1>) / sqrt(2)`.

## Canonical circuit (little-endian register order)
1. `qc.h(0)` — create superposition on the first qubit.
2. For `i in 1..n-1`: `qc.cx(0, i)` — fan-out entanglement from qubit 0.
3. Do **not** insert relative phases (no `z`/`s`/`sdg` on the chain) unless the task asks for GHZ⁻.

## Common bugs
- **GHZ⁻**: extra `z` on one qubit → relative minus sign; basis probs still look like 000/111.
- **Wrong CNOT direction**: `cx(i, 0)` breaks the star topology.
- **Classical mixture**: measuring mid-circuit or resetting destroys coherence while keeping 50/50 populations.
- **Missing H**: only |0...0> remains.

## Check without leaking answers
Public tests often only check support `{000,111}`; semantic probes / fidelity catch phase errors.
