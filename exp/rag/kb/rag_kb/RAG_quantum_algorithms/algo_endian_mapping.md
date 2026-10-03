# Endianness and reversible bit mapping

## Goal
Map bitstrings with reversed qubit order, or implement reversible wiring that matches little-endian Qiskit indices.

## Rules of thumb
- Qiskit `Statevector` index bit 0 is qubit 0 (little-endian).
- Textbook algorithms often write MSB on the left; translate carefully.
- For reverse mapping on n qubits: swap `i` with `n-1-i` (or equivalent CX network).

## Common bugs
- Off-by-one in swap pairs.
- Reversing only classical print order, not the quantum register.
- Mixing big-endian oracle wiring with little-endian preparation.
