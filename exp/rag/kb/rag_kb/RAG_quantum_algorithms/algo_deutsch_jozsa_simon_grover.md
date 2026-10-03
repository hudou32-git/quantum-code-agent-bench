# DJ / Simon / Grover (short reference)

## Deutsch–Jozsa
Constant vs balanced oracle; one query with Hadamards around the oracle.

## Simon
Find hidden period `s` of `f(x)=f(y) <=> x⊕y in {0,s}`; use linear equations on measurement outcomes.

## Grover
Oracle marks solutions; diffuser inverts about mean. Iteration count ~ `pi/4 * sqrt(N/M)`.

## Shared pitfalls
- Oracle implemented as classical if/else in Python instead of unitary circuit.
- Diffuser on wrong qubit subset.
- Missing ancilla uncompute after marking.
