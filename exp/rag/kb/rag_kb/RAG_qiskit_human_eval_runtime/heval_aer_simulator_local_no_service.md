# HumanEval-Qiskit: local AerSimulator execution without IBM Quantum account

## Metadata
- Topics: `AerSimulator`, `local_eval`, `AccountNotFoundError`, `no_runtime_service`, `HumanEval`

## Evaluation environment
HumanEval-Qiskit runs in an **isolated sandbox without IBM Quantum credentials**. Code that loads cloud accounts fails even if it would work on a developer laptop.

## Default local path
```python
    from qiskit_aer import AerSimulator
    backend = AerSimulator()
```

## Do not introduce unless the prompt already imports it
- `QiskitRuntimeService`, `service.backend()`, `least_busy()`, `IBMBackend` submission to real hardware
- `load_account()`, `IBMProvider`

## When docstring mentions "device" or "backend"
Use **prompt-specified** `Fake*` or `AerSimulator()`, not cloud service discovery.

## AerSimulator.from_backend(fake_device)
Use when the task pairs a fake IBM device model with a noisy simulator:
```python
    simulator = AerSimulator.from_backend(FakeBelemV2())
```

## Never use legacy Aer import
- Wrong: `from qiskit import Aer`
- Wrong: `Aer.get_backend('qasm_simulator')`

## Retrieval tags
AerSimulator, qiskit_aer, local_eval, account_not_found, no_runtime_service, HumanEval, backend

## Questions this answers
- HumanEval Qiskit without IBM Quantum account
- AccountNotFoundError QiskitRuntimeService avoid
- Aer simulator backend for Sampler mode=
