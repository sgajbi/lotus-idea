from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.application.advise_missing_risk_profile_runtime_evidence import (  # noqa: E402
    ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS,
    ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateAdviseMissingRiskProfile,
    advise_missing_risk_profile_runtime_execution_is_valid,
    build_advise_missing_risk_profile_runtime_execution,
    evaluate_advise_missing_risk_profile,
)
from tests.support.advise_missing_risk_profile_runtime_evidence import (  # noqa: E402
    AuthoritativeAdviseMissingRiskProfileSource,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = (
    ROOT
    / "scripts"
    / "advise_missing_risk_profile_runtime_evidence"
    / "generate_runtime_execution.py"
)
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "missing_risk_profile_live_proof.py",
    ROOT / "scripts" / "generate_missing_risk_profile_live_proof.py",
    ROOT / "scripts" / "missing_risk_profile_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_missing_risk_profile_live_proof.py",
)
FORBIDDEN_KEYS = {
    "bookId",
    "clientId",
    "correlationId",
    "evaluationId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "tenantId",
    "traceId",
}
FORBIDDEN_TEXT = {
    "tenant-a",
    "book-a",
    "portfolio-a",
    "client-a",
    "evaluation-a",
    "corr-advise",
    "trace-advise",
}
NOW = datetime(2026, 7, 16, 11, 10, tzinfo=UTC)


def validate_advise_missing_risk_profile_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned Advise missing-risk-profile generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(
                f"retired missing-risk-profile evidence path is prohibited: {path.relative_to(ROOT)}"
            )

    command = _command()
    result = evaluate_advise_missing_risk_profile(
        command,
        advise_source=AuthoritativeAdviseMissingRiskProfileSource(),
    )
    candidate = build_advise_missing_risk_profile_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )
    if not advise_missing_risk_profile_runtime_execution_is_valid(candidate):
        errors.append("authoritative Advise missing-risk-profile fixture must validate")
    if candidate.get("aggregateBlockersSatisfied") != list(
        ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the live Advise source blocker")
    if candidate.get("remainingCertificationBlockers") != list(
        ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS
    ):
        errors.append("runtime evidence must preserve unrelated certification blockers")

    no_opportunity = build_advise_missing_risk_profile_runtime_execution(
        generated_at_utc=NOW,
        result=evaluate_advise_missing_risk_profile(
            command,
            advise_source=AuthoritativeAdviseMissingRiskProfileSource(
                diagnostic="risk_profile_current"
            ),
        ),
    )
    if not advise_missing_risk_profile_runtime_execution_is_valid(no_opportunity):
        errors.append("truthful current-profile no-opportunity execution must validate")

    evidence = result.source_evaluation.evidence
    assert evidence is not None and evidence.workflow_runtime is not None
    missing_scope = build_advise_missing_risk_profile_runtime_execution(
        generated_at_utc=NOW,
        result=replace(
            result,
            source_evaluation=replace(
                result.source_evaluation,
                evidence=replace(
                    evidence,
                    workflow_runtime=replace(evidence.workflow_runtime, tenant_scope_hash=None),
                ),
            ),
        ),
    )
    if advise_missing_risk_profile_runtime_execution_is_valid(missing_scope):
        errors.append("missing producer tenant scope must fail closed")

    tampered = deepcopy(candidate)
    tampered["execution"]["evaluationReceipt"]["riskProfilePosture"] = "CURRENT"
    if advise_missing_risk_profile_runtime_execution_is_valid(tampered):
        errors.append("tampered risk-profile evaluation receipt must fail closed")

    for payload in (candidate, no_opportunity, missing_scope, tampered):
        validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _command() -> EvaluateAdviseMissingRiskProfile:
    return EvaluateAdviseMissingRiskProfile(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
        evaluation_id="evaluation-a",
        as_of_date=date(2026, 7, 16),
        evaluated_at_utc=NOW,
        correlation_id="corr-advise",
        trace_id="trace-advise",
    )


def main() -> int:
    errors = validate_advise_missing_risk_profile_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Advise missing-risk-profile runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
