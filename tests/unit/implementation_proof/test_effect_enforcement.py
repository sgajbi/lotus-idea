from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

import app.application.implementation_proof_artifact_registry as artifact_registry
from app.application.downstream_realization_readiness import (
    build_downstream_realization_readiness_snapshot,
)
from app.application.implementation_proof_artifact_registry import (
    IMPLEMENTATION_PROOF_ARTIFACT_SPECS,
    ImplementationProofArtifactSpec,
    ProofArtifactEffect,
)
from app.application.implementation_proof_capability_updates import (
    apply_blocker_proof,
    build_capability_readiness,
)
from app.application.implementation_proof_consumption import (
    registered_proof_is_valid_and_current,
)
from app.application.implementation_proof_opportunity_archetype_proofs import (
    _apply_valid_opportunity_proof,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    MANIFEST_ENV,
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    build_source_ingestion_readiness_snapshot,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.domain import InMemoryIdeaRepository
from app.runtime.repository_state import DATABASE_URL_ENV
from tests.support.proof_provenance import bound_aggregate_proof
from tests.support.source_ingestion_runtime_evidence import runtime_execution
from tests.support.source_ingestion_scheduler_evidence import (
    deployment_evidence,
    source_contract,
)
from tests.unit.downstream_realization.fixtures import valid_advise_route_source_contract

ROOT = Path(__file__).resolve().parents[3]
EVALUATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_registered_aggregate_proof_rejects_wrong_effect() -> None:
    proof_ref = "output/proof.json"
    proof = bound_aggregate_proof(
        {"generatedAtUtc": "2026-06-21T10:10:00Z"},
        proof_ref,
    )

    assert not registered_proof_is_valid_and_current(
        "durable_repository_proof",
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
        proof,
        proof_ref,
        evaluated_at_utc=EVALUATED_AT,
        proof_is_valid=lambda candidate: bool(candidate),
    )


def test_opportunity_proof_rejects_registry_effect_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _replace_payload_effect(
        monkeypatch,
        "risk_concentration_live_proof",
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
    )
    capability = build_capability_readiness(
        "opportunity-archetype-scenarios",
        "Opportunity archetype scenarios",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=(),
        blockers=("live_proof_missing",),
    )
    proof_ref = "output/opportunity/risk-concentration-live-proof.json"
    proof = bound_aggregate_proof(
        {"generatedAtUtc": "2026-06-21T10:10:00Z"},
        proof_ref,
    )

    capabilities = _apply_valid_opportunity_proof(
        (capability,),
        payload_argument="risk_concentration_live_proof",
        proof=proof,
        proof_is_valid=lambda candidate: bool(candidate),
        apply_proof=lambda candidate, ref: apply_blocker_proof(
            candidate,
            capability_ids=("opportunity-archetype-scenarios",),
            blockers_cleared=("live_proof_missing",),
            proof_ref=ref,
        ),
        proof_ref=proof_ref,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert capabilities[0].blockers == ("live_proof_missing",)
    assert proof_ref not in capabilities[0].evidence_refs


def test_source_ingestion_runtime_proof_rejects_registry_effect_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _replace_payload_effect(
        monkeypatch,
        "source_ingestion_runtime_execution",
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
    )
    manifest_path = tmp_path / "manifest.json"
    proof_path = tmp_path / "runtime-execution.json"
    proof_ref = "output/source-ingestion/live-proof.json"
    proof = bound_aggregate_proof(runtime_execution(), proof_ref)
    manifest_path.write_text("{}", encoding="utf-8")
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest_path))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(proof_path))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        source_ingestion_runtime_execution=proof,
        source_ingestion_runtime_execution_ref=proof_ref,
        repository_root=ROOT,
    )

    source_ingestion = _capability(snapshot, "source-ingestion")
    archetypes = _capability(snapshot, "opportunity-archetype-scenarios")
    assert "live_core_source_proof_missing" in source_ingestion.blockers
    assert "opportunity_archetype_live_core_source_proof_missing" in archetypes.blockers
    assert proof_ref not in source_ingestion.evidence_refs
    assert proof_ref not in archetypes.evidence_refs


@pytest.mark.parametrize(
    ("ref_argument", "effect"),
    (
        (
            "source_ingestion_scheduled_worker_source_contract_ref",
            ProofArtifactEffect.BLOCKER_CLEARING,
        ),
        (
            "source_ingestion_scheduled_worker_deployment_evidence_ref",
            ProofArtifactEffect.SUPPORTING_EVIDENCE,
        ),
    ),
)
def test_scheduler_proofs_reject_registry_effect_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ref_argument: str,
    effect: ProofArtifactEffect,
) -> None:
    _replace_ref_effect(monkeypatch, ref_argument, effect)
    source_contract_path = tmp_path / "source-contract.json"
    deployment_path = tmp_path / "deployment-evidence.json"
    source_contract_path.write_text(
        json.dumps(source_contract(repository_root=ROOT)),
        encoding="utf-8",
    )
    deployment_path.write_text(
        json.dumps(deployment_evidence(repository_root=ROOT)),
        encoding="utf-8",
    )
    monkeypatch.setenv(SCHEDULED_WORKER_SOURCE_CONTRACT_ENV, str(source_contract_path))
    monkeypatch.setenv(SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV, str(deployment_path))

    snapshot = build_source_ingestion_readiness_snapshot(repository_root=ROOT)

    assert snapshot.scheduled_worker_deployment_evidence_valid is False
    assert "scheduled_worker_deploy_proof_missing" in snapshot.certification_blockers


def test_downstream_source_contract_rejects_registry_effect_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _replace_payload_effect(
        monkeypatch,
        "advise_proposal_route_proof",
        ProofArtifactEffect.BLOCKER_CLEARING,
    )
    proof_ref = "output/downstream/advise-route-source-contract-proof.json"

    snapshot = build_downstream_realization_readiness_snapshot(
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        advise_proposal_route_proof=valid_advise_route_source_contract(),
        advise_proposal_route_proof_ref=proof_ref,
    )

    advise = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "advise-proposal-realization"
    )
    assert proof_ref not in advise.evidence_refs
    assert "advise_live_contract_proof_missing" in advise.blockers


def _replace_payload_effect(
    monkeypatch: pytest.MonkeyPatch,
    payload_argument: str,
    effect: ProofArtifactEffect,
) -> None:
    _replace_effect(
        monkeypatch,
        matches=lambda spec: spec.payload_argument == payload_argument,
        effect=effect,
    )


def _replace_ref_effect(
    monkeypatch: pytest.MonkeyPatch,
    ref_argument: str,
    effect: ProofArtifactEffect,
) -> None:
    _replace_effect(
        monkeypatch,
        matches=lambda spec: spec.ref_argument == ref_argument,
        effect=effect,
    )


def _replace_effect(
    monkeypatch: pytest.MonkeyPatch,
    *,
    matches: Callable[[ImplementationProofArtifactSpec], bool],
    effect: ProofArtifactEffect,
) -> None:
    matched = False
    specs = []
    for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS:
        if matches(spec):
            specs.append(replace(spec, effect=effect))
            matched = True
        else:
            specs.append(spec)
    assert matched
    monkeypatch.setattr(
        artifact_registry,
        "IMPLEMENTATION_PROOF_ARTIFACT_SPECS",
        tuple(specs),
    )


def _capability(
    snapshot: ImplementationProofReadinessSnapshot,
    capability_id: str,
) -> ImplementationProofCapabilityReadiness:
    return next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == capability_id
    )
