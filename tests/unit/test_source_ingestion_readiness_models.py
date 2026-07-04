from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from app.api.source_ingestion_readiness_models import (
    SourceIngestionReadinessResponse,
    SourceIngestionRunOnceResponse,
    SourceIngestionRunOnceRuntimeView,
)
from app.application.source_ingestion import (
    HighCashSourceIngestionBatchResult,
    HighCashSourceIngestionDecision,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
    SourceIngestionReadinessSnapshot,
)
from app.application.source_ingestion_worker import MANIFEST_SCHEMA_VERSION


def test_source_ingestion_readiness_response_preserves_certification_boundaries() -> None:
    snapshot = SourceIngestionReadinessSnapshot(
        repository="lotus-idea",
        source_authority="lotus-core",
        opportunity_family="high_cash",
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        example_manifest_path="docs/examples/source-ingestion/high-cash-worker-manifest.example.json",
        example_manifest_available=True,
        configured_manifest_available=True,
        configured_live_proof_available=False,
        live_core_source_proof_valid=False,
        configured_scheduled_worker_proof_available=True,
        scheduled_worker_deploy_proof_valid=True,
        core_base_url_configured=True,
        core_query_base_url_configured=True,
        core_query_control_plane_base_url_configured=True,
        durable_repository_configured=True,
        run_once_configuration_status="configured",
        certification_status="not_certified",
        configuration_blockers=(),
        certification_blockers=("live_core_source_proof_missing",),
        supported_feature_promoted=False,
    )

    response = SourceIngestionReadinessResponse.from_domain(snapshot).model_dump(by_alias=True)

    assert response["repository"] == "lotus-idea"
    assert response["sourceAuthority"] == "lotus-core"
    assert response["opportunityFamily"] == "high_cash"
    assert response["runOnceConfigured"] is True
    assert response["liveSourceCertified"] is False
    assert response["certificationBlockers"] == ("live_core_source_proof_missing",)
    assert response["supportedFeaturePromoted"] is False


def test_source_ingestion_run_once_blocked_response_is_source_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_source_ingestion_environment(monkeypatch)

    response = SourceIngestionRunOnceResponse.blocked(
        blocker="durable_repository_not_configured",
        durable_storage_backed=False,
    ).model_dump(by_alias=True)

    assert response["repository"] == "lotus-idea"
    assert response["runStatus"] == "blocked"
    assert response["supportabilityStatus"] == "not_certified"
    assert response["sourceAuthority"] == "lotus-core"
    assert response["opportunityFamily"] == "high_cash"
    assert response["durableStorageBacked"] is False
    assert response["totalCount"] == 0
    assert response["decisionCounts"] == {
        decision.value: 0 for decision in HighCashSourceIngestionDecision
    }
    assert response["configurationBlockers"] == ("durable_repository_not_configured",)
    assert "supported_feature_promotion_missing" in response["certificationBlockers"]
    assert response["liveSourceCertified"] is False
    assert response["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in str(response)


def test_source_ingestion_run_once_response_maps_aggregate_result_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_source_ingestion_environment(monkeypatch)
    runtime = cast(
        SourceIngestionRunOnceRuntimeView,
        SimpleNamespace(
            configured_manifest_available=True,
            core_base_url_configured=True,
            core_query_base_url_configured=True,
            core_query_control_plane_base_url_configured=True,
        ),
    )

    response = SourceIngestionRunOnceResponse.from_domain(
        HighCashSourceIngestionBatchResult(item_results=()),
        runtime=runtime,
        durable_storage_backed=True,
    ).model_dump(by_alias=True)

    assert response["runStatus"] == "completed"
    assert response["durableStorageBacked"] is True
    assert response["configuredManifestAvailable"] is True
    assert response["coreBaseUrlConfigured"] is True
    assert response["coreQueryBaseUrlConfigured"] is True
    assert response["coreQueryControlPlaneBaseUrlConfigured"] is True
    assert response["totalCount"] == 0
    assert response["configurationBlockers"] == ()
    assert response["decisionCounts"] == {
        decision.value: 0 for decision in HighCashSourceIngestionDecision
    }
    assert response["liveSourceCertified"] is False
    assert response["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in str(response)


def _clear_source_ingestion_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in (
        MANIFEST_ENV,
        CORE_BASE_URL_ENV,
        CORE_QUERY_BASE_URL_ENV,
        CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
        LIVE_PROOF_ENV,
        SCHEDULED_WORKER_PROOF_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)
