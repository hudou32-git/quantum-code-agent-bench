# Phase oracles and relative phase

## Goal
Mark target basis state(s) with a minus sign: `|t> → -|t>`, leave others unchanged.

## Patterns
- Multi-controlled Z on the all-ones (or target) pattern, using X wrappers to match the bitstring.
- Phase kickback through an ancilla in `|->`.

## Common bugs
- Flipping **amplitude support** (X gates) instead of phase.
- Global phase only (undetectable / irrelevant) vs **relative** phase (detectable by superposition probes).
- Correct computational-basis probs, wrong interference — classic L3 residual.
