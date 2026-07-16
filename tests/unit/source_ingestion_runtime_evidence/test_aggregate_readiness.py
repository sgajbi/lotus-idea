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
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    MANIFEST_ENV,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.domain import InMemoryIdeaRepository
from app.runtime.repository_state import DATABASE_URL_ENV
from tests.support.source_ingestion_runtime_evidence import runtime_execution

ROOT = Path(__file__).resolve().parents[3]
EVALUATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
SOURCE_INGESTION_PROOF_REF = "output/source-ingestion/live-proof.json"


def test_current_bound_source_ingestion_runtime_execution_clears_only_aggregate_live_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof = _bound_source_ingestion_proof(_valid_source_ingestion_runtime_execution())
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
        pytest.param(lambda: _valid_source_ingestion_runtime_execution(), id="missing-provenance"),
        pytest.param(
            lambda: _bound_source_ingestion_proof(
                _valid_source_ingestion_runtime_execution(),
                proof_ref="output/source-ingestion/copied-live-proof.json",
            ),
            id="wrong-ref",
        ),
        pytest.param(
            lambda: _bound_source_ingestion_proof(
                _valid_source_ingestion_runtime_execution(
                    generated_at_utc=datetime(2026, 6, 20, 9, 0, tzinfo=UTC)
                )
            ),
            id="stale",
        ),
        pytest.param(
            lambda: _bound_source_ingestion_proof(
                _valid_source_ingestion_runtime_execution(
                    generated_at_utc=datetime(2026, 6, 21, 10, 11, tzinfo=UTC)
                )
            ),
            id="future-dated",
        ),
        pytest.param(lambda: _wrong_source_revision_proof(), id="wrong-source-revision"),
    ],
)
def test_source_ingestion_runtime_execution_requires_aggregate_current_provenance(
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
    proof_path = tmp_path / "source-ingestion-runtime-execution.json"
    manifest_path.write_text("{}", encoding="utf-8")
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest_path))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(proof_path))
    monkeypatch.delenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, raising=False)
    monkeypatch.delenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, raising=False)
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        source_ingestion_runtime_execution=proof,
        source_ingestion_runtime_execution_ref=SOURCE_INGESTION_PROOF_REF,
        repository_root=ROOT,
    )


def _valid_source_ingestion_runtime_execution(
    *,
    generated_at_utc: datetime = EVALUATED_AT,
) -> dict[str, Any]:
    return runtime_execution(generated_at_utc=generated_at_utc)


def _bound_source_ingestion_proof(
    payload: dict[str, Any],
    *,
    proof_ref: str = SOURCE_INGESTION_PROOF_REF,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "source-ingestion-runtime-execution.json"
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
    proof = _bound_source_ingestion_proof(_valid_source_ingestion_runtime_execution())
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
