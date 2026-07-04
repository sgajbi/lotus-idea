from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.source_ingestion_readiness as source_ingestion_readiness_api
from app.application.source_ingestion import HighCashSourceIngestionBatchResult
from app.application.source_ingestion import SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.observability import OperationOutcome
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceUnavailable,
)
from app.runtime.repository_state import DATABASE_URL_ENV
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    SourceIngestionRuntime,
    SourceIngestionRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@pytest.fixture(autouse=True)
def reset_repository_provider() -> Iterator[None]:
    reset_idea_repository_for_tests()
    yield
    reset_idea_repository_for_tests()


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    seen_request: CoreHighCashEvidenceRequest | None = None
    error: Exception | None = None
    close_count: int = 0

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return _core_evidence()

    def close(self) -> None:
        self.close_count += 1


def source_ingestion_readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.source-ingestion.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-source-ingestion-readiness-api",
    }


def source_ingestion_run_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.source-ingestion.run",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-source-ingestion-run-api",
    }


def test_source_ingestion_readiness_api_returns_blocked_operator_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_PROOF_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    client = TestClient(app)

    response = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["opportunityFamily"] == "high_cash"
    assert payload["exampleManifestAvailable"] is True
    assert payload["configuredManifestAvailable"] is False
    assert payload["configuredLiveProofAvailable"] is False
    assert payload["liveCoreSourceProofValid"] is False
    assert payload["configuredScheduledWorkerProofAvailable"] is False
    assert payload["scheduledWorkerDeployProofValid"] is False
    assert payload["coreBaseUrlConfigured"] is False
    assert payload["coreQueryBaseUrlConfigured"] is False
    assert payload["coreQueryControlPlaneBaseUrlConfigured"] is False
    assert payload["durableRepositoryConfigured"] is False
    assert payload["runOnceConfigurationStatus"] == "blocked"
    assert payload["runOnceConfigured"] is False
    assert payload["certificationStatus"] == "not_certified"
    assert payload["liveSourceCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["configurationBlockers"] == [
        "source_ingestion_manifest_not_configured",
        "lotus_core_query_base_url_not_configured",
        "lotus_core_query_control_plane_base_url_not_configured",
        "lotus_core_base_url_not_configured",
        "durable_repository_not_configured",
    ]
    assert payload["certificationBlockers"] == [
        "live_core_source_proof_missing",
        "scheduled_worker_deploy_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    ]
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


def test_source_ingestion_readiness_api_requires_operator_permission() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/source-ingestion/readiness")
    role_denied = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(
            capabilities="idea.review.queue.read",
        ),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"
    assert "lotus_core_base_url" not in response.text.lower()


def test_source_ingestion_readiness_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_PROOF_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    events: list[tuple[str, str, str, bool, bool, str | None]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                event.error_code,
            )
        )

    monkeypatch.setattr(source_ingestion_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "source_ingestion_readiness_read",
            "blocked",
            "not_certified",
            False,
            False,
            None,
        )
    ]


def test_source_ingestion_readiness_api_emits_configured_run_once_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.delenv(LIVE_PROOF_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_PROOF_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")
    events: list[tuple[str, str, str, bool, bool, str | None]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                event.error_code,
            )
        )

    monkeypatch.setattr(source_ingestion_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(),
    )

    assert response.status_code == 200
    assert response.json()["runOnceConfigurationStatus"] == "configured"
    assert response.json()["coreQueryBaseUrlConfigured"] is True
    assert response.json()["coreQueryControlPlaneBaseUrlConfigured"] is True
    assert events == [
        (
            "source_ingestion_readiness_read",
            "accepted",
            "not_certified",
            True,
            False,
            None,
        )
    ]


def test_source_ingestion_run_once_api_blocks_without_durable_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    runtime_builder_called = False

    def fail_if_called() -> SourceIngestionRuntime:
        nonlocal runtime_builder_called
        runtime_builder_called = True
        raise AssertionError("runtime builder must not run without durable repository")

    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "_build_source_ingestion_runtime_from_environment",
        fail_if_called,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "blocked"
    assert payload["durableStorageBacked"] is False
    assert payload["totalCount"] == 0
    assert payload["decisionCounts"]["accepted"] == 0
    assert payload["configurationBlockers"] == ["durable_repository_not_configured"]
    assert runtime_builder_called is False
    assert "PB_SG_GLOBAL_BAL_001" not in response.text
    assert "idempotency" not in response.text.lower()


def test_source_ingestion_run_once_api_blocks_runtime_configuration_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryIdeaRepository()
    reset_idea_repository_for_tests(repository=repository)
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "idea_repository_durable_storage_backed",
        lambda _repository: True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "_build_source_ingestion_runtime_from_environment",
        lambda: SourceIngestionRuntimeBlocker(
            "source_ingestion_manifest_not_configured",
            configured_manifest_available=False,
            core_base_url_configured=False,
            core_query_base_url_configured=False,
            core_query_control_plane_base_url_configured=False,
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "blocked"
    assert payload["durableStorageBacked"] is True
    assert payload["configuredManifestAvailable"] is False
    assert payload["coreBaseUrlConfigured"] is False
    assert payload["coreQueryBaseUrlConfigured"] is False
    assert payload["coreQueryControlPlaneBaseUrlConfigured"] is False
    assert payload["totalCount"] == 0
    assert "source_ingestion_manifest_not_configured" in payload["configurationBlockers"]
    assert len(repository.snapshot().candidate_records) == 0


def test_source_ingestion_run_once_api_blocks_manifest_over_batch_ceiling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = InMemoryIdeaRepository()
    reset_idea_repository_for_tests(repository=repository)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "maxItems": SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING + 1,
                "workItems": [
                    {
                        "portfolioId": PORTFOLIO_ID,
                        "asOfDate": "2026-06-21",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "idea_repository_durable_storage_backed",
        lambda _repository: True,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "blocked"
    assert payload["configurationBlockers"] == ["source_ingestion_batch_limit_exceeded"]
    assert payload["totalCount"] == 0
    assert len(repository.snapshot().candidate_records) == 0
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


def test_source_ingestion_run_once_api_executes_configured_batch_source_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryIdeaRepository()
    reset_idea_repository_for_tests(repository=repository)
    source = RecordingCoreSource()
    runtime = SourceIngestionRuntime(
        plan=source_ingestion_worker_plan_from_manifest(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "correlationId": "corr-source-ingestion-run-api",
                "traceId": "trace-source-ingestion-run-api",
                "workItems": [
                    {
                        "portfolioId": PORTFOLIO_ID,
                        "asOfDate": "2026-06-21",
                    }
                ],
            }
        ),
        core_source=source,
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "idea_repository_durable_storage_backed",
        lambda _repository: True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "_build_source_ingestion_runtime_from_environment",
        lambda: runtime,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "completed"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["opportunityFamily"] == "high_cash"
    assert payload["durableStorageBacked"] is True
    assert payload["configuredManifestAvailable"] is True
    assert payload["coreBaseUrlConfigured"] is True
    assert payload["coreQueryBaseUrlConfigured"] is True
    assert payload["coreQueryControlPlaneBaseUrlConfigured"] is True
    assert payload["totalCount"] == 1
    assert payload["decisionCounts"]["accepted"] == 1
    assert payload["configurationBlockers"] == []
    assert payload["liveSourceCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "live_core_source_proof_missing" in payload["certificationBlockers"]
    assert len(repository.snapshot().candidate_records) == 1
    assert source.seen_request is not None
    assert source.seen_request.correlation_id == "corr-source-ingestion-run-api"
    assert source.close_count == 1
    assert "PB_SG_GLOBAL_BAL_001" not in response.text
    assert "candidateId" not in response.text
    assert "idempotency" not in response.text.lower()


def test_source_ingestion_run_once_api_closes_runtime_after_source_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryIdeaRepository()
    reset_idea_repository_for_tests(repository=repository)
    source = RecordingCoreSource(error=CoreSourceUnavailable())
    runtime = SourceIngestionRuntime(
        plan=source_ingestion_worker_plan_from_manifest(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "correlationId": "corr-source-ingestion-run-api",
                "traceId": "trace-source-ingestion-run-api",
                "workItems": [
                    {
                        "portfolioId": PORTFOLIO_ID,
                        "asOfDate": "2026-06-21",
                    }
                ],
            }
        ),
        core_source=source,
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "idea_repository_durable_storage_backed",
        lambda _repository: True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "_build_source_ingestion_runtime_from_environment",
        lambda: runtime,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runStatus"] == "completed"
    assert payload["decisionCounts"]["blocked"] == 1
    assert payload["decisionCounts"]["accepted"] == 0
    assert source.seen_request is not None
    assert source.close_count == 1
    assert len(repository.snapshot().candidate_records) == 0


def test_source_ingestion_run_once_api_requires_operator_permission() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/source-ingestion/run-once")
    role_denied = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(roles="advisor"),
    )
    capability_denied = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(
            capabilities="idea.source-ingestion.readiness.read",
        ),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"


def test_source_ingestion_run_once_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryIdeaRepository()
    reset_idea_repository_for_tests(repository=repository)
    runtime = SourceIngestionRuntime(
        plan=source_ingestion_worker_plan_from_manifest(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "workItems": [
                    {
                        "portfolioId": PORTFOLIO_ID,
                        "asOfDate": "2026-06-21",
                    }
                ],
            }
        ),
        core_source=RecordingCoreSource(),
        configured_manifest_available=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "idea_repository_durable_storage_backed",
        lambda _repository: True,
    )
    monkeypatch.setattr(
        source_ingestion_readiness_api,
        "_build_source_ingestion_runtime_from_environment",
        lambda: runtime,
    )
    events: list[tuple[str, str, str, bool, bool, str | None, dict[str, str]]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                event.error_code,
                dict(event.attributes),
            )
        )

    monkeypatch.setattr(source_ingestion_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.post(
        "/api/v1/source-ingestion/run-once",
        headers=source_ingestion_run_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "source_ingestion_run_once",
            "accepted",
            "not_certified",
            True,
            False,
            None,
            {"work_item_count_bucket": "1-10"},
        )
    ]


def test_source_ingestion_run_once_operation_events_use_bounded_count_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str | None, dict[str, str]]] = []

    def capture(event: Any) -> None:
        events.append((event.outcome.value, event.error_code, dict(event.attributes)))

    monkeypatch.setattr(source_ingestion_readiness_api, "emit_operation_event", capture)

    assert (
        source_ingestion_readiness_api._source_ingestion_operation_outcome(
            HighCashSourceIngestionBatchResult(item_results=())
        ).value
        == "blocked"
    )
    source_ingestion_readiness_api._emit_source_ingestion_run_event(
        OperationOutcome.BLOCKED,
        total_count=0,
    )
    source_ingestion_readiness_api._emit_source_ingestion_run_event(
        OperationOutcome.ACCEPTED,
        total_count=42,
    )
    source_ingestion_readiness_api._emit_source_ingestion_run_event(
        OperationOutcome.ACCEPTED,
        total_count=101,
    )

    assert events == [
        ("blocked", None, {"work_item_count_bucket": "0"}),
        ("accepted", None, {"work_item_count_bucket": "11-100"}),
        ("accepted", None, {"work_item_count_bucket": "100+"}),
    ]


def _source_ref(product_id: str) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _core_evidence() -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )
