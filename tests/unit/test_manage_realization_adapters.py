"""HTTP adapter fidelity for the shipped manage#660 owner contract.

Split from test_downstream_realization_adapters.py (maintainability cap);
shared fixtures are imported from there. Every fake body here mirrors the
owner's real IdeaActionIntakeResponse and outcome-history shapes.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.domain import (
    ConversionTarget,
    ManageActionRealizationStatus,
    SourceSystem,
)
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    DownstreamRealizationConfigurationError,
    HttpManageActionRealizationClient,
)
from app.ports.downstream_realization import (
    DownstreamRealizationOutcomePosture,
    DownstreamRealizationReadError,
)
from tests.unit.test_downstream_realization_adapters import (
    conversion_intent,
    downstream_json_client,
    manage_service_context,
    report_access_scope,
)


def test_manage_adapter_posts_owner_contract_payload_and_server_context() -> None:
    """The submit leg speaks manage#660 verbatim: the envelope carries the
    authoritative portfolio scope, the trusted principal carries its
    portfolio entitlement, and the ACCEPTED receipt is parsed into the
    owner identity - intake, durable action, version, and the owner\'s own
    request fingerprint - not inferred from HTTP 202."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["payload"] = request.read()
        return httpx.Response(202, json=_manage_intake_receipt_payload())

    adapter = HttpManageActionRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://manage.example",
            submit_path="/api/v1/rebalance/idea-action-intake",
            source_authority=SourceSystem.LOTUS_MANAGE,
            manage_service_context=manage_service_context(),
        ),
        client=downstream_json_client("https://manage.example", httpx.MockTransport(handler)),
    )

    outcome = adapter.submit_action_intent(
        conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE),
        access_scope=report_access_scope(),
        correlation_id="corr-downstream",
        trace_id="trace-downstream",
        idempotency_key="submission-idempotency-001",
    )

    assert outcome.accepted is True
    assert httpx.Response(200, content=captured["payload"]).json() == {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_high_cash_redacted",
        "conversion_intent_id": "conversion-001",
        "intent_type": "REVIEW_FOR_REBALANCE",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_high_cash_redacted",
                "content_hash": "sha256:evidence-redacted",
            }
        ],
    }
    assert captured["headers"]["x-actor-id"] == "lotus-idea-local-development"
    assert captured["headers"]["x-role"] == "SERVICE"
    assert captured["headers"]["x-tenant-id"] == "local-development"
    assert captured["headers"]["x-service-identity"] == "lotus-idea-local-development"
    assert captured["headers"]["x-capabilities"] == (
        "manage.idea_action_intake.accept,manage.idea_action_intake.read"
    )
    assert captured["headers"]["x-portfolio-ids"] == "PB_SG_GLOBAL_BAL_001"
    assert captured["headers"]["x-correlation-id"] == "corr-downstream"
    assert captured["headers"]["x-trace-id"] == "trace-downstream"
    assert captured["headers"]["idempotency-key"] == "submission-idempotency-001"
    receipt = outcome.owner_receipt
    assert receipt is not None
    assert receipt.owner_authority is SourceSystem.LOTUS_MANAGE
    assert receipt.owner_request_id == "iai_1f2e3d4c5b6a7f8e9d0c"
    assert receipt.owner_realization_id == "ima_9f8e7d6c5b4a3f2e1d0c"
    assert receipt.owner_work_id == "ima_9f8e7d6c5b4a3f2e1d0c"
    assert receipt.source_event_version == 1
    assert receipt.source_evidence_fingerprint == "sha256:aabbccddeeff"


def test_manage_adapter_rejected_intake_carries_owner_reason_without_receipt() -> None:
    """A rejected intake creates no durable management action - the owner
    returns action_receipt_accepted=false with reason codes and a null
    management_action_id. The outcome is REJECTED with the owner\'s reason
    and, honestly, no owner receipt to reconcile against."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                **_manage_intake_receipt_payload(),
                "action_receipt_accepted": False,
                "action_register_created": False,
                "management_action_id": None,
                "management_action_status": None,
                "source_event_version": None,
                "outcome_reason_codes": ["IDEA_ACTION_INTAKE_DUPLICATE_CONFLICT"],
            },
        )

    adapter = _manage_adapter(handler)
    outcome = adapter.submit_action_intent(
        conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE),
        access_scope=report_access_scope(),
    )

    assert outcome.posture is DownstreamRealizationOutcomePosture.REJECTED
    assert outcome.failure_reason == "IDEA_ACTION_INTAKE_DUPLICATE_CONFLICT"
    assert outcome.owner_receipt is None


def test_manage_adapter_refuses_receipts_claiming_unsupported_authority() -> None:
    """manage#660 states an accepted intake grants no rebalance-execution,
    order, or client-publication authority. A receipt asserting otherwise is
    not a stronger acceptance - it is a malformed owner response, held as
    UNKNOWN until a human or a corrected owner resolves it."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={**_manage_intake_receipt_payload(), "order_created": True},
        )

    adapter = _manage_adapter(handler)
    outcome = adapter.submit_action_intent(
        conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE),
        access_scope=report_access_scope(),
    )

    assert outcome.posture is DownstreamRealizationOutcomePosture.UNKNOWN
    assert outcome.failure_reason == "downstream_malformed_response"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(action_receipt_accepted="yes"),
        lambda payload: payload.update(action_register_created=False),
    ],
)
def test_manage_adapter_refuses_malformed_acceptance_receipts(mutate: Any) -> None:
    payload = _manage_intake_receipt_payload()
    mutate(payload)
    adapter = _manage_adapter(lambda _request: httpx.Response(202, json=payload))

    outcome = adapter.submit_action_intent(
        conversion_intent(ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE),
        access_scope=report_access_scope(),
    )

    assert outcome.posture is DownstreamRealizationOutcomePosture.UNKNOWN
    assert outcome.failure_reason == "downstream_malformed_response"
    assert outcome.owner_receipt is None


def test_manage_adapter_loads_the_exact_owner_outcome_history() -> None:
    """The read leg fetches the owner history route with the trusted
    portfolio-scoped principal and parses the exact owner body - including
    the reopened-review chain the owner permits."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json=_manage_history_payload())

    adapter = _manage_adapter(
        handler,
        history_path_template="/api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes",
    )
    history = adapter.load_action_realization(
        intake_id="iai_1f2e3d4c5b6a7f8e9d0c",
        access_scope=report_access_scope(),
        correlation_id="corr-downstream",
    )

    assert captured["url"] == (
        "https://manage.example/api/v1/rebalance/idea-action-intakes/"
        "iai_1f2e3d4c5b6a7f8e9d0c/outcomes"
    )
    assert captured["headers"]["x-portfolio-ids"] == "PB_SG_GLOBAL_BAL_001"
    assert history.intake_id == "iai_1f2e3d4c5b6a7f8e9d0c"
    assert history.management_action_id == "ima_9f8e7d6c5b4a3f2e1d0c"
    assert history.status is ManageActionRealizationStatus.PENDING_REVIEW
    assert history.source_event_version == 3
    assert [event.event_type.value for event in history.events] == [
        "INTAKE_ACCEPTED",
        "APPROVE",
        "REQUEST_CHANGES",
    ]


def test_manage_adapter_maps_owner_read_failures_and_invalid_histories() -> None:
    """Owner unavailability is a read error (nothing persisted, retryable);
    an owner body violating its own machine is a ValueError the caller holds
    as a conflict. Neither is ever treated as evidence."""

    def unavailable(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "down"})

    adapter = _manage_adapter(
        unavailable,
        history_path_template="/api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes",
    )
    with pytest.raises(DownstreamRealizationReadError):
        adapter.load_action_realization(
            intake_id="iai_1f2e3d4c5b6a7f8e9d0c",
            access_scope=report_access_scope(),
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(events={}),
        lambda payload: payload.update(events=["not-an-event"]),
    ],
)
def test_manage_adapter_refuses_malformed_owner_history_collections(mutate: Any) -> None:
    payload = _manage_history_payload()
    mutate(payload)
    adapter = _manage_adapter(
        lambda _request: httpx.Response(200, json=payload),
        history_path_template="/api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes",
    )

    with pytest.raises(ValueError):
        adapter.load_action_realization(
            intake_id="iai_1f2e3d4c5b6a7f8e9d0c",
            access_scope=report_access_scope(),
        )

    def invalid(request: httpx.Request) -> httpx.Response:
        payload = _manage_history_payload()
        payload["events"][1]["event_type"] = "INTAKE_ACCEPTED"
        return httpx.Response(200, json=payload)

    adapter = _manage_adapter(
        invalid,
        history_path_template="/api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes",
    )
    with pytest.raises(ValueError):
        adapter.load_action_realization(
            intake_id="iai_1f2e3d4c5b6a7f8e9d0c",
            access_scope=report_access_scope(),
        )


def test_manage_adapter_requires_history_path_template_for_reads() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json={})

    adapter = _manage_adapter(handler)
    with pytest.raises(DownstreamRealizationConfigurationError, match="history_path_template"):
        adapter.load_action_realization(
            intake_id="iai_1f2e3d4c5b6a7f8e9d0c",
            access_scope=report_access_scope(),
        )

    configured = _manage_adapter(
        handler,
        history_path_template="/api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes",
    )
    with pytest.raises(ValueError, match="intake_id is required"):
        configured.load_action_realization(
            intake_id=" ",
            access_scope=report_access_scope(),
        )


def _manage_adapter(
    handler: Any,
    *,
    history_path_template: str | None = None,
) -> HttpManageActionRealizationClient:
    return HttpManageActionRealizationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://manage.example",
            submit_path="/api/v1/rebalance/idea-action-intake",
            history_path_template=history_path_template,
            source_authority=SourceSystem.LOTUS_MANAGE,
            manage_service_context=manage_service_context(),
        ),
        client=downstream_json_client("https://manage.example", httpx.MockTransport(handler)),
    )


def _manage_intake_receipt_payload() -> dict[str, Any]:
    """The shipped IdeaActionIntakeResponse subset the receipt mapper reads,
    with owner-shaped identifiers (iai_/ima_ + sha256:<12-hex> fingerprint)."""
    return {
        "intake_id": "iai_1f2e3d4c5b6a7f8e9d0c",
        "intake_status": "ACCEPTED",
        "action_receipt_accepted": True,
        "idempotency_replay": False,
        "request_fingerprint": "sha256:aabbccddeeff",
        "action_register_created": True,
        "management_action_id": "ima_9f8e7d6c5b4a3f2e1d0c",
        "management_action_status": "PENDING_REVIEW",
        "source_event_version": 1,
        "outcome_reason_codes": ["IDEA_ACTION_INTAKE_ACCEPTED"],
        "rebalance_execution_authority_granted": False,
        "order_created": False,
        "client_publication_authorized": False,
    }


def _manage_history_payload() -> dict[str, Any]:
    """The shipped outcome-history body, exercising the owner\'s reopened
    review: PENDING_REVIEW -> APPROVED -> (REQUEST_CHANGES) PENDING_REVIEW."""
    base_event = {
        "action_id": "ima_9f8e7d6c5b4a3f2e1d0c",
        "actor_id": "pm-001",
        "actor_role": "PORTFOLIO_MANAGER",
        "correlation_id": "corr-owner",
        "causation_id": "conversion-001",
    }
    return {
        "contract_version": "lotus-manage.idea-action-outcome-history.v1",
        "source_authority": "lotus-manage",
        "intake_id": "iai_1f2e3d4c5b6a7f8e9d0c",
        "management_action_id": "ima_9f8e7d6c5b4a3f2e1d0c",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "idea_candidate_id": "idea_high_cash_redacted",
        "conversion_intent_id": "conversion-001",
        "status": "PENDING_REVIEW",
        "source_event_version": 3,
        "events": [
            {
                **base_event,
                "event_id": "imae_0001",
                "source_event_version": 1,
                "event_type": "INTAKE_ACCEPTED",
                "previous_status": None,
                "status": "PENDING_REVIEW",
                "occurred_at": "2026-09-03T10:00:00+00:00",
                "actor_id": "lotus-idea-local-development",
                "actor_role": "SERVICE",
                "reason_code": "idea_conversion_intent_accepted_for_management_review",
            },
            {
                **base_event,
                "event_id": "imae_0002",
                "source_event_version": 2,
                "event_type": "APPROVE",
                "previous_status": "PENDING_REVIEW",
                "status": "APPROVED",
                "occurred_at": "2026-09-03T10:05:00+00:00",
                "reason_code": "REVIEW_APPROVED",
            },
            {
                **base_event,
                "event_id": "imae_0003",
                "source_event_version": 3,
                "event_type": "REQUEST_CHANGES",
                "previous_status": "APPROVED",
                "status": "PENDING_REVIEW",
                "occurred_at": "2026-09-03T10:09:00+00:00",
                "reason_code": "REVIEW_REOPENED_FOR_CHANGES",
            },
        ],
        "rebalance_execution_proven": False,
        "order_execution_proven": False,
        "client_publication_proven": False,
    }
