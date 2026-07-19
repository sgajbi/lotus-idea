# ruff: noqa: E402
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.low_income_cashflow_runtime_evidence import (  # noqa: E402
    LOW_INCOME_CASHFLOW_REMAINING_BLOCKERS,
    LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateLowIncomeCashflowReadiness,
    build_blocked_low_income_cashflow_runtime_execution,
    build_low_income_cashflow_runtime_execution,
    evaluate_low_income_cashflow_readiness,
    low_income_cashflow_runtime_execution_is_valid,
)
from tests.support.low_income_cashflow_runtime_evidence import (  # noqa: E402
    AuthoritativeCoreLowIncomeSource,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = (
    ROOT / "scripts" / "low_income_cashflow_runtime_evidence" / "generate_runtime_execution.py"
)
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "low_income_core_cashflow_live_proof.py",
    ROOT / "scripts" / "generate_low_income_core_cashflow_live_proof.py",
    ROOT / "scripts" / "low_income_core_cashflow_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_low_income_core_cashflow_live_proof.py",
)
FORBIDDEN_KEYS = {
    "accountId",
    "clientId",
    "correlationId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "tenantId",
    "traceId",
}
FORBIDDEN_TEXT = {"PB_SG_GLOBAL_BAL_001", "tenant-a", "portfolio-a", "corr-a"}
NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def validate_low_income_cashflow_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned low-income cashflow generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(
                f"retired low-income cashflow path is prohibited: {path.relative_to(ROOT)}"
            )
    command = _command()
    candidate = evaluate_low_income_cashflow_readiness(
        command,
        core_source=AuthoritativeCoreLowIncomeSource(),
    )
    payload = build_low_income_cashflow_runtime_execution(generated_at_utc=NOW, result=candidate)
    if not low_income_cashflow_runtime_execution_is_valid(payload):
        errors.append("authoritative low-income cashflow runtime fixture must validate")
    if payload.get("aggregateBlockersSatisfied") != list(
        LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the low-income Core source blocker")
    if payload.get("remainingCertificationBlockers") != list(
        LOW_INCOME_CASHFLOW_REMAINING_BLOCKERS
    ):
        errors.append("runtime evidence must preserve unrelated certification blockers")
    no_opportunity = evaluate_low_income_cashflow_readiness(
        command,
        core_source=AuthoritativeCoreLowIncomeSource(minimum_cashflow=Decimal("0")),
    )
    no_opportunity_payload = build_low_income_cashflow_runtime_execution(
        generated_at_utc=NOW,
        result=no_opportunity,
    )
    if not low_income_cashflow_runtime_execution_is_valid(no_opportunity_payload):
        errors.append("zero cashflow must validate as a completed no-opportunity execution")
    unknown_reconciliation = build_low_income_cashflow_runtime_execution(
        generated_at_utc=NOW,
        result=replace(
            candidate,
            evidence=replace(
                candidate.evidence,
                cashflow_projection_product=replace(
                    candidate.evidence.cashflow_projection_product,
                    runtime=replace(
                        candidate.evidence.cashflow_projection_product.runtime,
                        reconciliation_status="UNKNOWN",
                    ),
                ),
            ),
        ),
    )
    if low_income_cashflow_runtime_execution_is_valid(unknown_reconciliation):
        errors.append("unknown Core cashflow reconciliation must fail closed")
    blocked = build_blocked_low_income_cashflow_runtime_execution(
        generated_at_utc=NOW,
        command=command,
        error_code="core_source_entitlement_denied",
    )
    if low_income_cashflow_runtime_execution_is_valid(blocked):
        errors.append("blocked Core cashflow execution must not validate")
    for candidate_payload in (payload, no_opportunity_payload, unknown_reconciliation, blocked):
        validate_forbidden_content(candidate_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _command() -> EvaluateLowIncomeCashflowReadiness:
    return EvaluateLowIncomeCashflowReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=NOW,
        horizon_days=30,
        correlation_id="corr-a",
        trace_id="trace-a",
    )


def main() -> int:
    errors = validate_low_income_cashflow_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Low-income cashflow runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
