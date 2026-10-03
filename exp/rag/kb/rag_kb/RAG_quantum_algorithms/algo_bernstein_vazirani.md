# Bernstein–Vazirani oracle / full algorithm

## Goal
Hidden bitstring `s`; oracle implements `f(x)=s·x mod 2` as phase or bit oracle.

## Phase-oracle pattern (common in unit tests)
- Start from |+...+>|-> (or apply H on data, X/H on ancilla).
- For each bit of `s` that is 1, apply CNOT from that data qubit onto the phase ancilla
  (or `cz`/`z` equivalents on phase kickback layouts).

## Common bugs
- Implementing the **bit** oracle when the task asks for **phase** kickback.
- Wrong bit significance (endian): `s='011'` mapped to wrong qubits.
- Forgetting ancilla uncomputation when a clean ancilla is required.
