from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from typing import Any, Callable

import pytest

from app.application.advise_missing_risk_profile_runtime_evidence import (
    ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS,
    ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateAdviseMissingRiskProfile,
    advise_missing_risk_profile_runtime_execution_is_valid,
    build_advise_missing_risk_profile_runtime_execution,
    evaluate_advise_missing_risk_profile,
)
from app.application.runtime_evidence import sha256_json
from app.ports.advise_sources import AdvisePolicyEvaluationRuntimeEvidence
from tests.support.advise_missing_risk_profile_runtime_evidence import (
    AuthoritativeAdviseMissingRiskProfileSource,
)

NOW = datetime(2026, 7, 16, 11, 10, tzinfo=UTC)


def test_runtime_execution_qualifies_candidate_from_one_authoritative_fetch() -> None:
    source = AuthoritativeAdviseMissingRiskProfileSource()

    payload = _payload(source=source)

    assert len(source.requests) == 1
    assert advise_missing_risk_profile_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == list(
        ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(
        ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS
    )
    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "candidate_created"
    assert evaluation["riskProfilePosture"] == "MISSING"
    assert evaluation["riskProfileReviewRequired"] is True
    serialized = json.dumps(payload)
    for raw_identifier in (
        "tenant-a",
        "book-a",
        "portfolio-a",
        "client-a",
        "evaluation-a",
        "corr-advise",
        "trace-advise",
    ):
        assert raw_identifier not in serialized


@pytest.mark.parametrize(
    ("diagnostic", "posture"),
    (
        ("risk_profile_stale", "STALE"),
        ("risk_profile_expired", "EXPIRED"),
        ("risk_profile_review_due", "REVIEW_DUE"),
    ),
)
def test_runtime_execution_qualifies_reviewable_risk_profile_postures(
    diagnostic: str,
    posture: str,
) -> None:
    payload = _payload(source=AuthoritativeAdviseMissingRiskProfileSource(diagnostic=diagnostic))

    assert payload["execution"]["evaluationReceipt"]["riskProfilePosture"] == posture
    assert advise_missing_risk_profile_runtime_execution_is_valid(payload)


def test_runtime_execution_accepts_truthful_current_profile_no_opportunity() -> None:
    payload = _payload(
        source=AuthoritativeAdviseMissingRiskProfileSource(diagnostic="risk_profile_current")
    )

    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "not_eligible"
    assert evaluation["riskProfilePosture"] == "CURRENT"
    assert evaluation["riskProfileReviewRequired"] is False
    assert advise_missing_risk_profile_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "diagnostic",
    (
        "advise_policy_requirements_open",
        "risk_profile_missing,risk_profile_current",
    ),
)
def test_runtime_execution_rejects_unrecognized_or_conflicting_diagnostic(
    diagnostic: str,
) -> None:
    payload = _payload(source=AuthoritativeAdviseMissingRiskProfileSource(diagnostic=diagnostic))

    assert "advise_risk_profile_diagnostic_missing" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not advise_missing_risk_profile_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    (
        (
            lambda runtime: replace(runtime, evaluation_id="other"),
            "advise_evaluation_scope_mismatch",
        ),
        (
            lambda runtime: replace(runtime, tenant_scope_hash="sha256:" + "f" * 64),
            "advise_tenant_scope_mismatch",
        ),
        (
            lambda runtime: replace(runtime, portfolio_id="other"),
            "advise_portfolio_scope_mismatch",
        ),
        (
            lambda runtime: replace(runtime, correlation_id="other"),
            "advise_source_correlation_mismatch",
        ),
        (
            lambda runtime: replace(runtime, trace_id="other"),
            "advise_source_trace_mismatch",
        ),
        (
            lambda runtime: replace(
                runtime,
                as_of_date=runtime.as_of_date - timedelta(days=1),
            ),
            "advise_as_of_date_mismatch",
        ),
        (
            lambda runtime: replace(runtime, generated_at_utc=NOW + timedelta(seconds=1)),
            "advise_evidence_from_future",
        ),
        (
            lambda runtime: replace(runtime, freshness="stale"),
            "advise_policy_source_ref_mismatch",
        ),
        (
            lambda runtime: replace(runtime, content_hash="sha256:not-valid"),
            "advise_policy_source_ref_mismatch",
        ),
        (
            lambda runtime: replace(runtime, sign_off_blocker_count=-1),
            "advise_workflow_counts_invalid",
        ),
    ),
)
def test_runtime_execution_fails_closed_on_untrusted_workflow_evidence(
    mutation: Callable[
        [AdvisePolicyEvaluationRuntimeEvidence], AdvisePolicyEvaluationRuntimeEvidence
    ],
    expected_blocker: str,
) -> None:
    payload = _payload(
        source=AuthoritativeAdviseMissingRiskProfileSource(runtime_mutation=mutation)
    )

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not advise_missing_risk_profile_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "path",
    (
        ("unexpected",),
        ("execution", "unexpected"),
        ("execution", "requestReceipt", "unexpected"),
        ("execution", "workflowReceipt", "unexpected"),
        ("execution", "evaluationReceipt", "unexpected"),
        ("nonProofClaims", "unexpected"),
    ),
)
def test_contract_rejects_unknown_fields(path: tuple[str, ...]) -> None:
    payload = deepcopy(_payload())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = True

    assert not advise_missing_risk_profile_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("receipt_name", "field", "value"),
    (
        ("requestReceipt", "portfolioIdHash", "sha256:" + "f" * 64),
        ("workflowReceipt", "policyContentHash", "sha256:" + "f" * 64),
        ("workflowReceipt", "adviseDiagnostic", "risk_profile_current"),
        ("evaluationReceipt", "riskProfilePosture", "CURRENT"),
        ("evaluationReceipt", "riskProfileReviewRequired", False),
        ("evaluationReceipt", "outcome", "not_eligible"),
    ),
)
def test_contract_rejects_semantic_tampering_even_with_recomputed_digest(
    receipt_name: str,
    field: str,
    value: object,
) -> None:
    payload = deepcopy(_payload())
    receipt = payload["execution"][receipt_name]
    receipt[field] = value
    digest_key = {
        "requestReceipt": "requestDigest",
        "workflowReceipt": "receiptDigest",
        "evaluationReceipt": "evaluationDigest",
    }[receipt_name]
    receipt[digest_key] = sha256_json(
        {key: item for key, item in receipt.items() if key != digest_key}
    )
    if receipt_name == "workflowReceipt" and field == "adviseDiagnostic":
        evaluation = payload["execution"]["evaluationReceipt"]
        evaluation["sourceRefsDigest"] = sha256_json([dict(receipt)])
        evaluation["evaluationDigest"] = sha256_json(
            {key: item for key, item in evaluation.items() if key != "evaluationDigest"}
        )

    assert not advise_missing_risk_profile_runtime_execution_is_valid(payload)


def _payload(
    *,
    source: AuthoritativeAdviseMissingRiskProfileSource | None = None,
) -> dict[str, Any]:
    result = evaluate_advise_missing_risk_profile(
        EvaluateAdviseMissingRiskProfile(
            tenant_id="tenant-a",
            book_id="book-a",
            portfolio_id="portfolio-a",
            client_id="client-a",
            evaluation_id="evaluation-a",
            as_of_date=NOW.date(),
            evaluated_at_utc=NOW,
            correlation_id="corr-advise",
            trace_id="trace-advise",
        ),
        advise_source=source or AuthoritativeAdviseMissingRiskProfileSource(),
    )
    return build_advise_missing_risk_profile_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )
