from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from typing import Callable

import pytest

from app.application.advise_missing_suitability_runtime_evidence import (
    ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS,
    ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateAdviseMissingSuitability,
    advise_missing_suitability_runtime_execution_is_valid,
    build_advise_missing_suitability_runtime_execution,
    evaluate_advise_missing_suitability,
)
from app.application.runtime_evidence import sha256_json
from app.ports.advise_sources import AdvisePolicyEvaluationRuntimeEvidence
from tests.support.advise_missing_suitability_runtime_evidence import (
    AuthoritativeAdviseMissingSuitabilitySource,
)

NOW = datetime(2026, 7, 16, 10, 10, tzinfo=UTC)


def test_runtime_execution_qualifies_candidate_from_one_authoritative_fetch() -> None:
    source = AuthoritativeAdviseMissingSuitabilitySource()

    payload = _payload(source=source)

    assert len(source.requests) == 1
    assert advise_missing_suitability_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == list(
        ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == list(
        ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS
    )
    assert payload["execution"]["evaluationReceipt"]["outcome"] == "candidate_created"
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


def test_runtime_execution_accepts_truthful_no_opportunity_receipt() -> None:
    payload = _payload(source=AuthoritativeAdviseMissingSuitabilitySource(context_missing=False))

    evaluation = payload["execution"]["evaluationReceipt"]
    assert evaluation["outcome"] == "not_eligible"
    assert evaluation["suitabilityContextMissing"] is False
    assert advise_missing_suitability_runtime_execution_is_valid(payload)


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
        (lambda runtime: replace(runtime, trace_id="other"), "advise_source_trace_mismatch"),
        (
            lambda runtime: replace(runtime, as_of_date=runtime.as_of_date - timedelta(days=1)),
            "advise_as_of_date_mismatch",
        ),
        (
            lambda runtime: replace(runtime, generated_at_utc=NOW + timedelta(seconds=1)),
            "advise_evidence_from_future",
        ),
        (lambda runtime: replace(runtime, freshness="stale"), "advise_policy_source_ref_mismatch"),
        (
            lambda runtime: replace(runtime, content_hash="sha256:not-valid"),
            "advise_policy_source_ref_mismatch",
        ),
        (
            lambda runtime: replace(runtime, open_requirement_count=-1),
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
        source=AuthoritativeAdviseMissingSuitabilitySource(runtime_mutation=mutation)
    )

    assert expected_blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert not advise_missing_suitability_runtime_execution_is_valid(payload)


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

    assert not advise_missing_suitability_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("receipt_name", "field", "value"),
    (
        ("requestReceipt", "portfolioIdHash", "sha256:" + "f" * 64),
        ("workflowReceipt", "policyContentHash", "sha256:" + "f" * 64),
        ("evaluationReceipt", "outcome", "candidate_created"),
        ("evaluationReceipt", "suitabilityContextMissing", True),
    ),
)
def test_contract_rejects_receipt_tampering_even_when_digest_is_recomputed(
    receipt_name: str,
    field: str,
    value: object,
) -> None:
    payload = deepcopy(
        _payload(source=AuthoritativeAdviseMissingSuitabilitySource(context_missing=False))
    )
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

    assert not advise_missing_suitability_runtime_execution_is_valid(payload)


def _payload(
    *,
    source: AuthoritativeAdviseMissingSuitabilitySource | None = None,
) -> dict[str, object]:
    result = evaluate_advise_missing_suitability(
        EvaluateAdviseMissingSuitability(
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
        advise_source=source or AuthoritativeAdviseMissingSuitabilitySource(),
    )
    return build_advise_missing_suitability_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )
