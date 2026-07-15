from scripts.risk_drawdown_runtime_evidence.runtime_execution_contract_gate import (
    validate_risk_drawdown_runtime_execution_contract,
)


def test_runtime_execution_contract_gate_passes() -> None:
    assert validate_risk_drawdown_runtime_execution_contract() == []
