# W state preparation (Qiskit)

## Goal
Equal superposition of Hamming-weight-1 basis states.
3-qubit: `(|001>+|010>+|100>)/sqrt(3)`.
4-qubit: four weight-1 terms / 2.

## Construction ideas
- Use a cascade of controlled rotations / Ry angles derived from `arccos(sqrt(k/n))`.
- Alternative: recursive embedding of smaller W states with controlled swaps.

## Common bugs
- Preparing GHZ instead of W (support `{000,111}` vs weight-1).
- Unequal amplitudes (wrong rotation angles).
- Wrong endian labeling of which qubit is the '1'.
- Leaving ancillas entangled (if any were used).
