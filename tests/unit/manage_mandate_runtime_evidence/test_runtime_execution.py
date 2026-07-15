from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable

import pytest

from app.application.core_runtime_evidence import sha256_json
from app.application.manage_mandate_runtime_evidence import (
    EvaluateManageMandateReadiness,
    build_blocked_manage_mandate_runtime_execution,
    build_manage_mandate_runtime_execution,
    evaluate_manage_mandate_readiness,
    manage_mandate_runtime_execution_is_valid,
)
from app.domain import EvidenceFreshness, SignalEvaluationOutcome
from app.ports.manage_sources import ManageMandateHealthEvidenceRequest, ManageSourceUnavailable
from tests.support.manage_mandate_runtime_evidence import (
    AuthoritativeManageMandateSource,
    valid_manage_mandate_runtime_evidence,
)

NOW = datetime(2026, 6, 28, 10, 10, tzinfo=UTC)


def test_runtime_execution_binds_one_authoritative_source_evaluation() -> None:
    source = AuthoritativeManageMandateSource()
    command = _command()

    result = evaluate_manage_mandate_readiness(command, manage_source=source)
    payload = build_manage_mandate_runtime_execution(generated_at_utc=NOW, result=result)

    assert result.source_evaluation.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert source.requests == [
        ManageMandateHealthEvidenceRequest(
            tenant_id="tenant-a",
            portfolio_id="portfolio-a",
            as_of_date=date(2026, 6, 28),
            evaluated_at_utc=NOW,
            correlation_id="corr-manage",
            trace_id="trace-manage",
        )
    ]
    assert payload["execution"]["status"] == "completed"
    assert payload["execution"]["qualificationBlockers"] == []
    assert manage_mandate_runtime_execution_is_valid(payload) is True


@pytest.mark.parametrize(
    ("workflow_count", "lineage_count"),
    ((0, 4), (2, 0), (0, 0)),
)
def test_runtime_execution_preserves_supported_no_opportunity(
    workflow_count: int,
    lineage_count: int,
) -> None:
    payload = valid_manage_mandate_runtime_evidence(
        evaluated_at_utc=NOW,
        workflow_count=workflow_count,
        lineage_count=lineage_count,
    )

    assert payload["execution"]["evaluationReceipt"]["outcome"] == "not_eligible"
    assert payload["execution"]["evaluationReceipt"]["candidateIdHash"] is None
    assert manage_mandate_runtime_execution_is_valid(payload) is True


@pytest.mark.parametrize(
    "mutation",
    (
        lambda payload: payload.update({"unexpected": True}),
        lambda payload: payload["execution"].update({"unexpected": True}),
        lambda payload: payload["nonProofClaims"].update({"rebalanceActionCreated": True}),
        lambda payload: payload["execution"]["actionRegisterReceipt"].update(
            {"sourceSystem": "lotus-idea"}
        ),
        lambda payload: payload["execution"]["mandatePerformanceHealthReceipt"].update(
            {"asOfDate": "2026-06-27"}
        ),
        lambda payload: payload["execution"]["mandateRiskHealthReceipt"].update(
            {"freshness": "stale"}
        ),
        lambda payload: payload["execution"]["evaluationReceipt"].update(
            {"candidateIdHash": None}
        ),
    ),
)
def test_contract_rejects_unknown_claims_and_receipt_tampering(
    mutation: Callable[[dict[str, Any]], object],
) -> None:
    payload = valid_manage_mandate_runtime_evidence(evaluated_at_utc=NOW)

    mutation(payload)

    assert manage_mandate_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("receipt_name", "changes"),
    (
        ("requestReceipt", {"asOfDate": "2026-06-27"}),
        ("actionRegisterReceipt", {"responseTenantIdHash": "sha256:" + "f" * 64}),
        ("actionRegisterReceipt", {"workflowDecisionCount": 0}),
        ("mandatePerformanceHealthReceipt", {"route": "/wrong"}),
        ("mandateRiskHealthReceipt", {"generatedAtUtc": "2026-06-29T10:10:00Z"}),
        ("evaluationReceipt", {"outcome": "not_eligible"}),
        ("evaluationReceipt", {"minimumWorkflowDecisionCount": "1"}),
        ("evaluationReceipt", {"minimumLineageEdgeCount": True}),
        ("evaluationReceipt", {"candidateScore": "not-a-decimal"}),
    ),
)
def test_contract_rejects_semantic_forgery_with_recomputed_digest(
    receipt_name: str,
    changes: dict[str, Any],
) -> None:
    payload = valid_manage_mandate_runtime_evidence(evaluated_at_utc=NOW)
    receipt = payload["execution"][receipt_name]
    receipt.update(changes)
    digest_key = next(
        key for key in ("requestDigest", "evaluationDigest", "receiptDigest") if key in receipt
    )
    receipt[digest_key] = sha256_json(
        {key: value for key, value in receipt.items() if key != digest_key}
    )

    assert manage_mandate_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("mutation", "blocker"),
    (
        (
            lambda evidence: replace(evidence, action_register_runtime=None),
            "manage_action_register_runtime_receipt_missing",
        ),
        (
            lambda evidence: replace(evidence, portfolio_scope_confirmed=False),
            "manage_portfolio_scope_not_confirmed",
        ),
        (
            lambda evidence: replace(evidence, supportability_state="degraded"),
            "manage_action_register_not_ready",
        ),
        (
            lambda evidence: replace(evidence, mandate_performance_health_ref=None),
            "mandate_performance_health_source_ref_missing",
        ),
        (
            lambda evidence: replace(
                evidence,
                mandate_risk_health_ref=replace(
                    evidence.mandate_risk_health_ref,
                    freshness=EvidenceFreshness.STALE,
                ),
            ),
            "mandate_risk_health_evidence_not_current",
        ),
        (
            lambda evidence: replace(
                evidence,
                action_register_runtime=replace(
                    evidence.action_register_runtime,
                    generated_at_utc=NOW + timedelta(minutes=1),
                ),
            ),
            "manage_action_register_future_evidence",
        ),
    ),
)
def test_runtime_execution_fails_closed_on_incomplete_or_inconsistent_evidence(
    mutation: Callable[[Any], Any],
    blocker: str,
) -> None:
    result = evaluate_manage_mandate_readiness(
        _command(),
        manage_source=AuthoritativeManageMandateSource(),
    )
    evidence = result.source_evaluation.evidence
    assert evidence is not None
    result = replace(
        result,
        source_evaluation=replace(result.source_evaluation, evidence=mutation(evidence)),
    )

    payload = build_manage_mandate_runtime_execution(generated_at_utc=NOW, result=result)

    assert blocker in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert manage_mandate_runtime_execution_is_valid(payload) is False


def test_runtime_execution_preserves_source_error_without_qualifying() -> None:
    result = evaluate_manage_mandate_readiness(
        _command(),
        manage_source=_FailingSource(),
    )

    payload = build_manage_mandate_runtime_execution(generated_at_utc=NOW, result=result)

    assert payload["execution"]["status"] == "blocked"
    assert "manage_temporal_identity_missing" in payload["execution"]["qualificationBlockers"]
    assert payload["aggregateBlockersSatisfied"] == []
    assert manage_mandate_runtime_execution_is_valid(payload) is False


def test_explicit_blocked_runtime_execution_never_qualifies() -> None:
    payload = build_blocked_manage_mandate_runtime_execution(
        generated_at_utc=NOW,
        command=_command(),
        error_code="manage_source_entitlement_denied",
    )

    assert payload["aggregateBlockersSatisfied"] == []
    assert manage_mandate_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "changes",
    ({"tenant_id": " "}, {"portfolio_id": " "}, {"correlation_id": " "}),
)
def test_readiness_command_rejects_invalid_scope(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(_command(), **changes)


def _command() -> EvaluateManageMandateReadiness:
    return EvaluateManageMandateReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=date(2026, 6, 28),
        evaluated_at_utc=NOW,
        correlation_id="corr-manage",
        trace_id="trace-manage",
    )


class _FailingSource:
    def fetch_mandate_health_evidence(
        self,
        request: ManageMandateHealthEvidenceRequest,
    ) -> Any:
        raise ManageSourceUnavailable(code="manage_temporal_identity_missing")
