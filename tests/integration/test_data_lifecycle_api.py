from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.api import data_lifecycle as api_module
from app.domain.data_lifecycle import (
    REGULATED_ADVISORY_POLICY_REF,
    DataLifecycleAction,
    DataLifecycleCandidateContext,
    DataLifecycleCommand,
    DataLifecycleControl,
    DataLifecycleDecision,
    DataLifecycleOperationResult,
    DataLifecycleState,
)
from app.main import app
from app.ports.data_lifecycle import DataLifecycleEvaluator

REQUESTED_AT = datetime(2026, 7, 10, 9, 0, tzinfo=UTC)


class ApiLifecycleRepository:
    durable_storage_backed = True

    def __init__(self, context: DataLifecycleCandidateContext | None = None) -> None:
        self.context = context or valid_context()
        self.results_by_key: dict[str, tuple[str, DataLifecycleOperationResult]] = {}
        self.commands: list[DataLifecycleCommand] = []
        self.calls = 0

    def execute_data_lifecycle(
        self,
        command: DataLifecycleCommand,
        *,
        evaluated_at_utc: datetime,
        evaluator: DataLifecycleEvaluator,
    ) -> DataLifecycleOperationResult:
        self.calls += 1
        self.commands.append(command)
        existing = self.results_by_key.get(command.idempotency_key)
        if existing is not None:
            fingerprint, result = existing
            return replace(
                result,
                decision=(
                    DataLifecycleDecision.REPLAYED
                    if fingerprint == command.request_fingerprint
                    else DataLifecycleDecision.CONFLICT
                ),
            )
        evaluation = evaluator(command, self.context, evaluated_at_utc=evaluated_at_utc)
        control = evaluation.projected_control
        if evaluation.decision is DataLifecycleDecision.APPLIED and control is not None:
            self.context = replace(self.context, control=control)
        digest = hashlib.sha256(command.idempotency_key.encode("utf-8")).hexdigest()
        result = DataLifecycleOperationResult(
            operation_id=f"lifecycle-operation-{digest[:24]}",
            decision=evaluation.decision,
            control=control,
            blockers=evaluation.blockers,
            dry_run=command.dry_run,
            audit_sha256=digest,
            affected_row_counts=(
                {"idea_data_lifecycle_control": 1}
                if evaluation.decision is DataLifecycleDecision.APPLIED
                else {}
            ),
        )
        self.results_by_key[command.idempotency_key] = (command.request_fingerprint, result)
        return result


def test_data_lifecycle_api_previews_replays_and_conflicts_source_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = ApiLifecycleRepository()
    monkeypatch.setattr(api_module, "get_idea_repository", lambda: repository)
    client = TestClient(app)
    request = lifecycle_request(dry_run=True)
    headers = lifecycle_headers("lifecycle-api-preview-001")

    preview = client.post(lifecycle_path(), json=request, headers=headers)
    replay = client.post(lifecycle_path(), json=request, headers=headers)
    conflict = client.post(
        lifecycle_path(),
        json={**request, "reason": "different_approved_reason"},
        headers=headers,
    )

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["decision"] == "preview"
    assert payload["state"] == "erased"
    assert payload["dryRun"] is True
    assert payload["affectedRowCounts"] == {}
    assert payload["certificationStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert replay.status_code == 200
    assert replay.json()["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "data_lifecycle_idempotency_conflict"
    assert "privacy-operator-001" not in preview.text
    assert "tenant-001" not in preview.text
    assert repository.commands[0].correlation_id == "corr-lifecycle-api-001"
    assert repository.commands[0].trace_id == "trace-lifecycle-api-001"


def test_data_lifecycle_api_requires_role_capability_and_exact_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = ApiLifecycleRepository()
    monkeypatch.setattr(api_module, "get_idea_repository", lambda: repository)
    client = TestClient(app)

    denied = client.post(
        lifecycle_path(),
        json=lifecycle_request(),
        headers={"Idempotency-Key": "lifecycle-api-denied-001"},
    )
    wrong_tenant_headers = lifecycle_headers("lifecycle-api-wrong-tenant-001")
    wrong_tenant_headers["X-Caller-Tenant-Ids"] = "tenant-other"
    wrong_tenant = client.post(
        lifecycle_path(),
        json=lifecycle_request(),
        headers=wrong_tenant_headers,
    )

    assert denied.status_code == 403
    assert wrong_tenant.status_code == 403
    assert wrong_tenant.json()["code"] == "permission_denied"
    assert repository.calls == 0


def test_data_lifecycle_api_rejects_invalid_request_and_blocks_unsafe_erasure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = ApiLifecycleRepository(replace(valid_context(), active_outbox_count=1))
    monkeypatch.setattr(api_module, "get_idea_repository", lambda: repository)
    client = TestClient(app)

    invalid_key = client.post(
        lifecycle_path(),
        json=lifecycle_request(),
        headers=lifecycle_headers(" "),
    )
    blocked = client.post(
        lifecycle_path(),
        json=lifecycle_request(),
        headers=lifecycle_headers("lifecycle-api-blocked-001"),
    )

    assert invalid_key.status_code == 400
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "data_lifecycle_action_blocked"
    assert repository.context.control is not None
    assert repository.context.control.state is DataLifecycleState.ACTIVE


def test_data_lifecycle_api_does_not_disclose_cross_tenant_candidate_existence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = ApiLifecycleRepository(
        replace(valid_context(), candidate_exists=False, control=None)
    )
    monkeypatch.setattr(api_module, "get_idea_repository", lambda: repository)
    client = TestClient(app)

    response = client.post(
        lifecycle_path(),
        json=lifecycle_request(),
        headers=lifecycle_headers("lifecycle-api-not-found-001"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "data_lifecycle_candidate_not_found"
    assert "tenant-001" not in response.text


def test_data_lifecycle_openapi_certifies_success_and_failure_contracts() -> None:
    operation = app.openapi()["paths"][lifecycle_route_path()]["post"]

    assert operation["operationId"] == "applyIdeaCandidateDataLifecycleAction"
    assert operation["security"] == [{"LotusCallerContext": []}]
    assert operation["x-lotus-caller-context"]["requiredCapabilities"] == [
        "idea.data-lifecycle.manage"
    ]
    assert operation["x-lotus-caller-context"]["alternativeRoles"] == [
        "privacy_officer",
        "records_manager",
    ]
    assert "exactly match" in operation["x-lotus-caller-context"]["entitlementScope"]
    assert set(operation["responses"]) == {"200", "400", "403", "404", "409", "422", "503"}
    assert {
        example["value"]["code"]
        for example in operation["responses"]["409"]["content"]["application/json"][
            "examples"
        ].values()
    } == {
        "data_lifecycle_action_blocked",
        "data_lifecycle_idempotency_conflict",
    }


def valid_context() -> DataLifecycleCandidateContext:
    return DataLifecycleCandidateContext(
        candidate_exists=True,
        candidate_tenant_id="tenant-001",
        control=DataLifecycleControl(
            candidate_id="candidate-001",
            tenant_id="tenant-001",
            policy_ref=REGULATED_ADVISORY_POLICY_REF,
            state=DataLifecycleState.ACTIVE,
            retention_expires_at_utc=REQUESTED_AT + timedelta(days=365 * 7),
            version=1,
            updated_at_utc=REQUESTED_AT,
        ),
        active_outbox_count=0,
        active_downstream_count=0,
    )


def lifecycle_path() -> str:
    return "/api/v1/data-lifecycle/candidates/candidate-001/actions"


def lifecycle_route_path() -> str:
    return "/api/v1/data-lifecycle/candidates/{candidateId}/actions"


def lifecycle_request(*, dry_run: bool = False) -> dict[str, object]:
    return {
        "tenantId": "tenant-001",
        "action": DataLifecycleAction.ERASE.value,
        "authorityRef": "bank-privacy-governance:decision-001",
        "reason": "approved_lifecycle_request",
        "changeReference": "privacy-case-001",
        "requestedAtUtc": REQUESTED_AT.isoformat(),
        "dryRun": dry_run,
        "approverSubject": "privacy-approver-001",
    }


def lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "Idempotency-Key": idempotency_key,
        "X-Caller-Subject": "privacy-operator-001",
        "X-Caller-Roles": "privacy_officer",
        "X-Caller-Capabilities": "idea.data-lifecycle.manage",
        "X-Caller-Tenant-Ids": "tenant-001",
        "X-Correlation-Id": "corr-lifecycle-api-001",
        "X-Trace-Id": "trace-lifecycle-api-001",
    }
