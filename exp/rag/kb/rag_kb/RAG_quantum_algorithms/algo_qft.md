# Quantum Fourier Transform (Qiskit)

## Goal
Implement the QFT unitary on n qubits (often n=3 in unit tests).

## Structure
1. For qubit `i` from 0..n-1:
   - Apply `h(i)`.
   - Controlled-phase rotations `cp(pi/2^k)` from higher qubits onto `i`.
2. Optional final qubit reversals (`swap`) depending on whether the task wants bit-reversed output.

## Endianness
Qiskit is little-endian in Statevector indexing. Confirm whether the prompt wants:
- standard textbook QFT with swaps, or
- Qiskit-convention QFT without final swaps.

## Common bugs
- Wrong rotation angles (`pi/2` vs `pi/4` vs `pi/8`).
- Missing or extra SWAPs → fails unitary-up-to-global-phase checks.
- Applying gates in reverse qubit order.
