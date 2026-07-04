from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any

import pytest

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.source_ingestion_live_proof import (
    build_source_ingestion_live_proof_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.domain import InMemoryIdeaRepository
from app.runtime.repository_state import DATABASE_URL_ENV

ROOT = Path(__file__).resolve().parents[2]
EVALUATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
SOURCE_INGESTION_PROOF_REF = "output/source-ingestion/live-proof.json"


def test_current_bound_source_ingestion_live_proof_clears_only_aggregate_live_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof = _bound_source_ingestion_proof(_valid_source_ingestion_live_proof())
    snapshot = _build_snapshot_with_live_proof(monkeypatch, tmp_path, proof)

    source_ingestion = _capability(snapshot, "source-ingestion")
    archetypes = _capability(snapshot, "opportunity-archetype-scenarios")

    assert "live_core_source_proof_missing" not in source_ingestion.blockers
    assert SOURCE_INGESTION_PROOF_REF in source_ingestion.evidence_refs
    assert "opportunity_archetype_live_core_source_proof_missing" not in archetypes.blockers
    assert SOURCE_INGESTION_PROOF_REF in archetypes.evidence_refs
    assert "scheduled_worker_deploy_proof_missing" in source_ingestion.blockers
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers


@pytest.mark.parametrize(
    "proof_factory",
    [
        pytest.param(lambda: _valid_source_ingestion_live_proof(), id="missing-provenance"),
        pytest.param(
            lambda: _bound_source_ingestion_proof(
                _valid_source_ingestion_live_proof(),
                proof_ref="output/source-ingestion/copied-live-proof.json",
            ),
            id="wrong-ref",
        ),
        pytest.param(
            lambda: _bound_source_ingestion_proof(
                _valid_source_ingestion_live_proof(
                    generated_at_utc=datetime(2026, 6, 20, 9, 0, tzinfo=UTC)
                )
            ),
            id="stale",
        ),
        pytest.param(
            lambda: _bound_source_ingestion_proof(
                _valid_source_ingestion_live_proof(
                    generated_at_utc=datetime(2026, 6, 21, 10, 11, tzinfo=UTC)
                )
            ),
            id="future-dated",
        ),
        pytest.param(lambda: _wrong_source_revision_proof(), id="wrong-source-revision"),
    ],
)
def test_source_ingestion_live_proof_requires_aggregate_current_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    proof_factory: Callable[[], dict[str, Any]],
) -> None:
    proof = proof_factory()
    snapshot = _build_snapshot_with_live_proof(monkeypatch, tmp_path, proof)

    source_ingestion = _capability(snapshot, "source-ingestion")
    archetypes = _capability(snapshot, "opportunity-archetype-scenarios")

    assert "live_core_source_proof_missing" in source_ingestion.blockers
    assert SOURCE_INGESTION_PROOF_REF not in source_ingestion.evidence_refs
    assert "opportunity_archetype_live_core_source_proof_missing" in archetypes.blockers
    assert SOURCE_INGESTION_PROOF_REF not in archetypes.evidence_refs


def _build_snapshot_with_live_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    proof: dict[str, Any],
) -> ImplementationProofReadinessSnapshot:
    manifest_path = tmp_path / "manifest.json"
    proof_path = tmp_path / "source-ingestion-live-proof.json"
    manifest_path.write_text("{}", encoding="utf-8")
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest_path))
    monkeypatch.setenv(LIVE_PROOF_ENV, str(proof_path))
    monkeypatch.delenv(SCHEDULED_WORKER_PROOF_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        source_ingestion_live_proof=proof,
        source_ingestion_live_proof_ref=SOURCE_INGESTION_PROOF_REF,
        repository_root=ROOT,
    )


def _valid_source_ingestion_live_proof(
    *,
    generated_at_utc: datetime = EVALUATED_AT,
) -> dict[str, Any]:
    return build_source_ingestion_live_proof_payload(
        generated_at_utc=generated_at_utc,
        live_core_source_attempted=True,
        worker_summary={
            "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
            "mode": "run_once",
            "sourceAuthority": "lotus-core",
            "durableStorageBacked": True,
            "totalCount": 1,
            "decisionCounts": {"accepted": 1, "replayed": 0},
        },
    )


def _bound_source_ingestion_proof(
    payload: dict[str, Any],
    *,
    proof_ref: str = SOURCE_INGESTION_PROOF_REF,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "source-ingestion-live-proof.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        bound = bind_aggregate_proof_provenance(
            payload,
            artifact_path=artifact_path,
            proof_ref=proof_ref,
            repository_root=ROOT,
        )
        bound["aggregateProofProvenance"]["sourceTreeDirty"] = False
        return bound


def _wrong_source_revision_proof() -> dict[str, Any]:
    proof = _bound_source_ingestion_proof(_valid_source_ingestion_live_proof())
    proof["aggregateProofProvenance"]["sourceRevision"] = "0000000000000000000000000000000000000000"
    return proof


def _capability(
    snapshot: ImplementationProofReadinessSnapshot,
    capability_id: str,
) -> ImplementationProofCapabilityReadiness:
    return next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == capability_id
    )
