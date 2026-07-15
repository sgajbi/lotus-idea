from __future__ import annotations

REQUIRED_CORE_RUNTIME_EVIDENCE_PATHS = {
    "scripts/repository_hygiene/core_runtime_evidence_paths.py",
    "scripts/core_benchmark_assignment_runtime_evidence/generate_runtime_execution.py",
    "scripts/core_portfolio_state_runtime_evidence/__init__.py",
    "scripts/core_portfolio_state_runtime_evidence/generate_runtime_execution.py",
    "scripts/core_portfolio_state_runtime_evidence/runtime_execution_contract_gate.py",
    "src/app/application/core_benchmark_assignment_runtime_evidence/contract.py",
    "src/app/application/core_benchmark_assignment_runtime_evidence/runtime_execution.py",
    "src/app/application/core_portfolio_state_runtime_evidence/__init__.py",
    "src/app/application/core_portfolio_state_runtime_evidence/contract.py",
    "src/app/application/core_portfolio_state_runtime_evidence/runtime_execution.py",
    "tests/support/core_portfolio_state_runtime_evidence.py",
    "tests/unit/core_portfolio_state_runtime_evidence/__init__.py",
    "tests/unit/core_portfolio_state_runtime_evidence/test_generator.py",
    "tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py",
}

PROHIBITED_CORE_RUNTIME_EVIDENCE_LEGACY_PATHS = {
    "scripts/core_benchmark_assignment_live_proof_contract_gate.py",
    "scripts/core_portfolio_state_live_proof_contract_gate.py",
    "scripts/generate_core_benchmark_assignment_live_proof.py",
    "scripts/generate_core_portfolio_state_live_proof.py",
    "src/app/application/core_benchmark_assignment_live_proof.py",
    "src/app/application/core_portfolio_state_live_proof.py",
    "tests/unit/test_core_benchmark_assignment_live_proof.py",
    "tests/unit/test_core_portfolio_state_live_proof.py",
}
