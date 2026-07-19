# ruff: noqa: E402
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.advise_mandate_restriction_runtime_evidence import (  # noqa: E402
    ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateAdviseMandateRestriction,
    advise_mandate_restriction_runtime_execution_is_valid,
    build_advise_mandate_restriction_runtime_execution,
    evaluate_advise_mandate_restriction,
)
from tests.support.advise_mandate_restriction_runtime_evidence import (  # noqa: E402
    AuthoritativeAdviseMandateRestrictionSource,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = (
    ROOT
    / "scripts"
    / "advise_mandate_restriction_runtime_evidence"
    / "generate_runtime_execution.py"
)
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "mandate_restriction_live_proof.py",
    ROOT / "scripts" / "generate_mandate_restriction_live_proof.py",
    ROOT / "scripts" / "mandate_restriction_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_mandate_restriction_live_proof.py",
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
NOW = datetime(2026, 7, 15, 10, 10, tzinfo=UTC)


def validate_advise_mandate_restriction_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned Advise mandate-restriction generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(
                f"retired mandate-restriction evidence path is prohibited: {path.relative_to(ROOT)}"
            )
    command = _command()
    result = evaluate_advise_mandate_restriction(
        command,
        advise_source=AuthoritativeAdviseMandateRestrictionSource(),
    )
    candidate = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )
    if not advise_mandate_restriction_runtime_execution_is_valid(candidate):
        errors.append("authoritative Advise mandate-restriction fixture must validate")
    if candidate.get("aggregateBlockersSatisfied") != list(
        ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must satisfy only the live Advise source blocker")
    if candidate.get("remainingCertificationBlockers") != list(
        ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS
    ):
        errors.append("runtime evidence must preserve unrelated certification blockers")

    no_opportunity_result = evaluate_advise_mandate_restriction(
        command,
        advise_source=AuthoritativeAdviseMandateRestrictionSource(
            diagnostic="advise_policy_context_available"
        ),
    )
    no_opportunity = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=no_opportunity_result,
    )
    if not advise_mandate_restriction_runtime_execution_is_valid(no_opportunity):
        errors.append("truthful no-opportunity execution must validate")

    evidence = result.source_evaluation.evidence
    assert evidence is not None and evidence.workflow_runtime is not None
    missing_scope = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=replace(
            result,
            source_evaluation=replace(
                result.source_evaluation,
                evidence=replace(
                    evidence,
                    workflow_runtime=replace(
                        evidence.workflow_runtime,
                        tenant_scope_hash=None,
                    ),
                ),
            ),
        ),
    )
    if advise_mandate_restriction_runtime_execution_is_valid(missing_scope):
        errors.append("missing producer tenant scope must fail closed")

    tampered = deepcopy(candidate)
    tampered["execution"]["workflowReceipt"]["openRequirementCount"] = 0
    if advise_mandate_restriction_runtime_execution_is_valid(tampered):
        errors.append("tampered workflow receipt must fail closed")

    for payload in (candidate, no_opportunity, missing_scope, tampered):
        validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _command() -> EvaluateAdviseMandateRestriction:
    return EvaluateAdviseMandateRestriction(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
        evaluation_id="evaluation-a",
        as_of_date=date(2026, 7, 15),
        evaluated_at_utc=NOW,
        correlation_id="corr-advise",
        trace_id="trace-advise",
    )


def main() -> int:
    errors = validate_advise_mandate_restriction_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Advise mandate-restriction runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
