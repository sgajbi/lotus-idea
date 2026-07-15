from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.application.manage_mandate_runtime_evidence import (  # noqa: E402
    MANAGE_MANDATE_REMAINING_BLOCKERS,
    MANAGE_MANDATE_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateManageMandateReadiness,
    build_blocked_manage_mandate_runtime_execution,
    build_manage_mandate_runtime_execution,
    evaluate_manage_mandate_readiness,
    manage_mandate_runtime_execution_is_valid,
)
from tests.support.manage_mandate_runtime_evidence import (  # noqa: E402
    AuthoritativeManageMandateSource,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = ROOT / "scripts" / "manage_mandate_runtime_evidence" / "generate_runtime_execution.py"
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "manage_mandate_live_proof.py",
    ROOT / "scripts" / "generate_manage_mandate_live_proof.py",
    ROOT / "scripts" / "manage_mandate_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_manage_mandate_live_proof.py",
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
FORBIDDEN_TEXT = {"PB_SG_GLOBAL_BAL_001", "tenant-a", "portfolio-a", "corr-manage"}
NOW = datetime(2026, 6, 28, 10, 10, tzinfo=UTC)


def validate_manage_mandate_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned Manage mandate runtime generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(f"retired Manage mandate path is prohibited: {path.relative_to(ROOT)}")
    command = _command()
    result = evaluate_manage_mandate_readiness(
        command,
        manage_source=AuthoritativeManageMandateSource(),
    )
    candidate = build_manage_mandate_runtime_execution(generated_at_utc=NOW, result=result)
    if not manage_mandate_runtime_execution_is_valid(candidate):
        errors.append("authoritative Manage mandate runtime fixture must validate")
    if candidate.get("aggregateBlockersSatisfied") != list(
        MANAGE_MANDATE_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the three Manage source blockers")
    if candidate.get("remainingCertificationBlockers") != list(MANAGE_MANDATE_REMAINING_BLOCKERS):
        errors.append("runtime evidence must preserve unrelated certification blockers")
    no_opportunity_result = evaluate_manage_mandate_readiness(
        command,
        manage_source=AuthoritativeManageMandateSource(workflow_count=0),
    )
    no_opportunity = build_manage_mandate_runtime_execution(
        generated_at_utc=NOW,
        result=no_opportunity_result,
    )
    if not manage_mandate_runtime_execution_is_valid(no_opportunity):
        errors.append("supported no-opportunity execution must validate")
    evidence = result.source_evaluation.evidence
    assert evidence is not None and evidence.action_register_runtime is not None
    missing_temporal_identity = build_manage_mandate_runtime_execution(
        generated_at_utc=NOW,
        result=replace(
            result,
            source_evaluation=replace(
                result.source_evaluation,
                evidence=replace(evidence, action_register_runtime=None),
            ),
        ),
    )
    if manage_mandate_runtime_execution_is_valid(missing_temporal_identity):
        errors.append("missing producer temporal identity must fail closed")
    tampered = deepcopy(candidate)
    tampered["execution"]["actionRegisterReceipt"]["workflowDecisionCount"] = 0
    if manage_mandate_runtime_execution_is_valid(tampered):
        errors.append("tampered action-register count must fail closed")
    blocked = build_blocked_manage_mandate_runtime_execution(
        generated_at_utc=NOW,
        command=command,
        error_code="manage_source_entitlement_denied",
    )
    if manage_mandate_runtime_execution_is_valid(blocked):
        errors.append("blocked Manage execution must not validate")
    for payload in (candidate, no_opportunity, missing_temporal_identity, tampered, blocked):
        validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _command() -> EvaluateManageMandateReadiness:
    return EvaluateManageMandateReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=date(2026, 6, 28),
        evaluated_at_utc=NOW,
        correlation_id="corr-manage",
        trace_id="trace-manage",
    )


def main() -> int:
    errors = validate_manage_mandate_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Manage mandate runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
