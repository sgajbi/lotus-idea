from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
import json
from typing import Any, Callable

import pytest

from app.application.advise_mandate_restriction_runtime_evidence import (
    ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateAdviseMandateRestriction,
    advise_mandate_restriction_runtime_execution_is_valid,
    build_advise_mandate_restriction_runtime_execution,
    evaluate_advise_mandate_restriction,
)
from app.application.runtime_evidence import sha256_json
from app.domain import EvidenceFreshness
from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)
from tests.support.advise_mandate_restriction_runtime_evidence import (
    AuthoritativeAdviseMandateRestrictionSource,
)

NOW = datetime(2026, 7, 15, 10, 10, tzinfo=UTC)


def test_runtime_execution_qualifies_only_the_live_advise_source_blocker() -> None:
    result = _result()

    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert advise_mandate_restriction_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == list(
        ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(
        ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS
    )
    execution = payload["execution"]
    assert execution["evaluationReceipt"]["outcome"] == "candidate_created"
    assert execution["qualificationBlockers"] == []
    serialized = json.dumps(payload)
    for secret in (
        "tenant-a",
        "book-a",
        "portfolio-a",
        "client-a",
        "evaluation-a",
        "corr-advise",
        "trace-advise",
    ):
        assert secret not in serialized


def test_runtime_execution_accepts_a_truthful_no_opportunity_evaluation() -> None:
    result = _result(diagnostic="advise_policy_context_available")

    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "not_eligible"
    assert evaluation["restrictionReviewRequired"] is False
    assert advise_mandate_restriction_runtime_execution_is_valid(payload)


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
        (lambda runtime: replace(runtime, portfolio_id="other"), "advise_portfolio_scope_mismatch"),
        (
            lambda runtime: replace(runtime, correlation_id="other"),
            "advise_source_correlation_mismatch",
        ),
        (lambda runtime: replace(runtime, trace_id=None), "advise_source_trace_missing"),
        (
            lambda runtime: replace(runtime, as_of_date=date(2026, 7, 14)),
            "advise_as_of_date_mismatch",
        ),
        (
            lambda runtime: replace(runtime, generated_at_utc=NOW + timedelta(seconds=1)),
            "advise_evidence_from_future",
        ),
        (
            lambda runtime: replace(runtime, content_hash="not-a-hash"),
            "advise_workflow_hash_invalid",
        ),
        (lambda runtime: replace(runtime, freshness="stale"), "advise_source_evidence_not_current"),
        (
            lambda runtime: replace(runtime, data_quality_status="unknown"),
            "advise_source_quality_not_ready",
        ),
        (
            lambda runtime: replace(runtime, open_requirement_count=-1),
            "advise_workflow_counts_invalid",
        ),
        (
            lambda runtime: replace(runtime, policy_pack_id=None),
            "advise_policy_pack_identity_missing",
        ),
        (
            lambda runtime: replace(runtime, evaluation_status=None),
            "advise_evaluation_status_missing",
        ),
        (lambda runtime: replace(runtime, product_id="other:v1"), "advise_source_product_mismatch"),
        (lambda runtime: replace(runtime, route="/other"), "advise_source_route_mismatch"),
    ),
)
def test_runtime_execution_fails_closed_on_inconsistent_workflow_evidence(
    mutation: Callable[[Any], Any],
    expected_blocker: str,
) -> None:
    result = _result()
    evidence = result.source_evaluation.evidence
    assert evidence is not None and evidence.workflow_runtime is not None
    result = replace(
        result,
        source_evaluation=replace(
            result.source_evaluation,
            evidence=replace(evidence, workflow_runtime=mutation(evidence.workflow_runtime)),
        ),
    )

    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not advise_mandate_restriction_runtime_execution_is_valid(payload)


def test_runtime_execution_rejects_source_ref_and_workflow_disagreement() -> None:
    result = _result()
    evidence = result.source_evaluation.evidence
    assert evidence is not None and evidence.policy_ref is not None
    result = replace(
        result,
        source_evaluation=replace(
            result.source_evaluation,
            evidence=replace(
                evidence,
                policy_ref=replace(evidence.policy_ref, freshness=EvidenceFreshness.STALE),
            ),
        ),
    )

    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert "advise_policy_source_ref_mismatch" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []


def test_runtime_execution_preserves_source_failure_without_qualifying() -> None:
    result = evaluate_advise_mandate_restriction(
        _command(),
        advise_source=_UnavailableSource(),
    )

    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert payload["execution"]["status"] == "blocked"
    assert "advise_temporal_identity_missing" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not advise_mandate_restriction_runtime_execution_is_valid(payload)


def test_runtime_execution_preserves_entitlement_denial_without_qualifying() -> None:
    result = evaluate_advise_mandate_restriction(
        _command(),
        advise_source=_EntitlementDeniedSource(),
    )

    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )

    assert payload["execution"]["status"] == "blocked"
    assert "advise_source_entitlement_denied" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not advise_mandate_restriction_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("execution", "requestReceipt", "tenantIdHash"), "sha256:" + "0" * 64),
        (("execution", "workflowReceipt", "openRequirementCount"), 0),
        (("execution", "evaluationReceipt", "outcome"), "not_eligible"),
        (("nonProofClaims", "restrictionCleared"), True),
        (("aggregateBlockersSatisfied",), []),
    ),
)
def test_closed_contract_rejects_tampered_semantics(
    path: tuple[str, ...],
    value: object,
) -> None:
    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=_result(),
    )
    tampered = deepcopy(payload)
    target: Any = tampered
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    _refresh_receipt_digests(tampered)

    assert not advise_mandate_restriction_runtime_execution_is_valid(tampered)


def test_closed_contract_rejects_unknown_fields() -> None:
    payload = build_advise_mandate_restriction_runtime_execution(
        generated_at_utc=NOW,
        result=_result(),
    )
    payload["callerAssertion"] = True

    assert not advise_mandate_restriction_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    "changes",
    (
        {"tenant_id": " "},
        {"portfolio_id": " "},
        {"book_id": " "},
        {"client_id": " "},
        {"evaluation_id": " "},
        {"correlation_id": " "},
    ),
)
def test_command_rejects_incomplete_or_blank_scope(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(_command(), **changes)


def _result(*, diagnostic: str = "mandate_restriction_review_required") -> Any:
    return evaluate_advise_mandate_restriction(
        _command(),
        advise_source=AuthoritativeAdviseMandateRestrictionSource(diagnostic=diagnostic),
    )


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


def _refresh_receipt_digests(payload: dict[str, Any]) -> None:
    execution = payload["execution"]
    for receipt_name, digest_key in (
        ("requestReceipt", "requestDigest"),
        ("workflowReceipt", "receiptDigest"),
        ("evaluationReceipt", "evaluationDigest"),
    ):
        receipt = execution[receipt_name]
        receipt[digest_key] = sha256_json(
            {key: value for key, value in receipt.items() if key != digest_key}
        )


class _UnavailableSource:
    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        raise AdviseSourceUnavailable(code="advise_temporal_identity_missing")


class _EntitlementDeniedSource:
    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        raise AdviseSourceEntitlementDenied
