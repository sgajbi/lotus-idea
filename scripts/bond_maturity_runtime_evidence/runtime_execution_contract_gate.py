from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.application.bond_maturity_runtime_evidence import (  # noqa: E402
    BOND_MATURITY_REMAINING_BLOCKERS,
    BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateBondMaturityReadiness,
    bond_maturity_runtime_execution_is_valid,
    build_blocked_bond_maturity_runtime_execution,
    build_bond_maturity_runtime_execution,
    evaluate_bond_maturity_readiness,
)
from tests.support.bond_maturity_runtime_evidence import (  # noqa: E402
    AuthoritativeCoreBondMaturitySource,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = ROOT / "scripts" / "bond_maturity_runtime_evidence" / "generate_runtime_execution.py"
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "bond_maturity_live_proof.py",
    ROOT / "scripts" / "generate_bond_maturity_live_proof.py",
    ROOT / "scripts" / "bond_maturity_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_bond_maturity_live_proof.py",
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


def validate_bond_maturity_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned bond-maturity generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(f"retired bond-maturity path is prohibited: {path.relative_to(ROOT)}")

    command = _command()
    result = evaluate_bond_maturity_readiness(
        command,
        core_source=AuthoritativeCoreBondMaturitySource(),
    )
    payload = build_bond_maturity_runtime_execution(generated_at_utc=NOW, result=result)
    if not bond_maturity_runtime_execution_is_valid(payload):
        errors.append("authoritative Core bond-maturity runtime fixture must validate")
    if payload.get("aggregateBlockersSatisfied") != list(
        BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the bond-maturity Core source blocker")
    if payload.get("remainingCertificationBlockers") != list(BOND_MATURITY_REMAINING_BLOCKERS):
        errors.append("runtime evidence must preserve unrelated certification blockers")

    no_opportunity = evaluate_bond_maturity_readiness(
        command,
        core_source=AuthoritativeCoreBondMaturitySource(opportunity_detected=False),
    )
    no_opportunity_payload = build_bond_maturity_runtime_execution(
        generated_at_utc=NOW,
        result=no_opportunity,
    )
    if not bond_maturity_runtime_execution_is_valid(no_opportunity_payload):
        errors.append("supported empty maturity window must validate without a false opportunity")

    unknown_reconciliation = build_bond_maturity_runtime_execution(
        generated_at_utc=NOW,
        result=replace(
            result,
            evidence=replace(result.evidence, reconciliation_status="UNKNOWN"),
        ),
    )
    if bond_maturity_runtime_execution_is_valid(unknown_reconciliation):
        errors.append("unknown Core maturity reconciliation must fail closed")

    blocked = build_blocked_bond_maturity_runtime_execution(
        generated_at_utc=NOW,
        command=command,
        error_code="core_source_entitlement_denied",
    )
    if bond_maturity_runtime_execution_is_valid(blocked):
        errors.append("blocked Core bond-maturity execution must not validate")
    for candidate in (payload, no_opportunity_payload, unknown_reconciliation, blocked):
        validate_forbidden_content(candidate, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _command() -> EvaluateBondMaturityReadiness:
    return EvaluateBondMaturityReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=NOW,
        maturity_window_days=30,
        correlation_id="corr-a",
        trace_id="trace-a",
    )


def main() -> int:
    errors = validate_bond_maturity_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Bond-maturity runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
