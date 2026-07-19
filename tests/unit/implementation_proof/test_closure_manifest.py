from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import app.application.implementation_proof_closure_manifest as closure_manifest_module
from app.application.implementation_proof_closure_manifest import (
    BLOCKER_CLOSURE_CONTRACT_PATH,
    blocker_closure_manifest_errors,
    blocker_closure_manifest_payload,
)
from app.application.implementation_proof_artifact_registry import (
    ProofArtifactClassificationStatus,
)
from app.application.implementation_proof_models import ImplementationProofReadinessSnapshot
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[3]
EVALUATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_closure_manifest_covers_current_default_readiness_blockers() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)
    payload = blocker_closure_manifest_payload(snapshot=snapshot, contract=contract)

    assert errors == []
    assert payload["repository"] == "lotus-idea"
    assert payload["rfc"] == "RFC-0002"
    assert payload["certificationReady"] is False
    assert payload["supportedFeaturesPromoted"] is False
    assert payload["blockerCount"] == len(snapshot.overall_blockers)
    assert {row["blocker"] for row in payload["blockers"]} == set(snapshot.overall_blockers)


def test_closure_manifest_rejects_missing_blocker_owner() -> None:
    snapshot = _strict_default_snapshot()
    contract = _without_blocker(_load_contract(), snapshot.overall_blockers[0])

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert (
        f"RFC-0002 blocker `{snapshot.overall_blockers[0]}` has no closure-manifest owner" in errors
    )


def test_closure_manifest_rejects_duplicate_blocker_owner() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    blocker = snapshot.overall_blockers[0]
    contract["blockerGroups"][1]["blockers"].append(blocker)

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert f"RFC-0002 blocker `{blocker}` appears 2 times in the manifest" in errors


def test_closure_manifest_rejects_stale_blocker() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    contract["blockerGroups"][0]["blockers"].append("retired_rfc0002_blocker")

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert "RFC-0002 blocker `retired_rfc0002_blocker` is stale in the closure manifest" in errors


def test_closure_manifest_rejects_unknown_evidence_class() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    contract["blockerGroups"][0]["requiredEvidenceClass"] = "source_design_contract"

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert (
        "source-ingestion-runtime-configuration: `requiredEvidenceClass` must be "
        "a known evidence class"
    ) in errors


def test_closure_manifest_rejects_issue_url_drift() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    contract["blockerGroups"][0]["ownerIssue"]["url"] = (
        "https://github.com/sgajbi/lotus-idea/issues/999"
    )

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert (
        "source-ingestion-runtime-configuration: issue URL must be "
        "`https://github.com/sgajbi/lotus-idea/issues/698`"
    ) in errors


def test_closure_manifest_rejects_header_drift_and_malformed_blocker_groups() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    contract["schemaVersion"] = "stale"
    contract["repository"] = "lotus-core"
    contract["rfc"] = "RFC-9999"
    contract["trackingIssue"] = "https://github.com/sgajbi/lotus-idea/issues/999"
    contract["blockerGroups"] = {"groupId": "not-a-list"}

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert (
        f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `schemaVersion` must be "
        "`lotus-idea.rfc0002.blocker-closure-manifest.v1`"
    ) in errors
    assert f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `repository` must be `lotus-idea`" in errors
    assert f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `rfc` must be `RFC-0002`" in errors
    assert (
        f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `trackingIssue` must be "
        "`https://github.com/sgajbi/lotus-idea/issues/700`"
    ) in errors
    assert f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `blockerGroups` must be a list" in errors


def test_closure_manifest_rejects_malformed_blocker_group_fields() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    group = contract["blockerGroups"][0]
    group["groupId"] = ""
    group["blockers"] = ["", 42]
    group["sliceIds"] = "RFC-0002/slice-17"
    group["closureStatus"] = None
    group["supportedFeatureEffect"] = ""
    group["ownerIssue"] = "https://github.com/sgajbi/lotus-idea/issues/700"

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert f"{BLOCKER_CLOSURE_CONTRACT_PATH}: `groupId` must be a string" in errors
    assert "<invalid>: `blockers` must contain at least one string" in errors
    assert "<invalid>: `sliceIds` must contain at least one string" in errors
    assert "<invalid>: `closureStatus` must be a string" in errors
    assert "<invalid>: `supportedFeatureEffect` must be a string" in errors
    assert "<invalid>: `ownerIssue` must be an issue reference object" in errors


def test_closure_manifest_rejects_malformed_dependency_issue_list() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    contract["blockerGroups"][0]["dependencyIssues"] = {
        "repository": "sgajbi/lotus-core",
        "number": 790,
    }

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert "source-ingestion-runtime-configuration: `dependencyIssues` must be a list" in errors


def test_closure_manifest_rejects_malformed_issue_reference_fields() -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    contract["blockerGroups"][0]["dependencyIssues"] = [
        {
            "repository": "external/vendor",
            "number": 0,
            "url": "https://github.com/external/vendor/issues/0",
        },
        {
            "repository": "sgajbi/lotus-core",
            "number": 790,
            "url": "https://github.com/sgajbi/lotus-core/issues/791",
        },
    ]

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert (
        "source-ingestion-runtime-configuration: issue repository must be an "
        "sgajbi Lotus repository"
    ) in errors
    assert (
        "source-ingestion-runtime-configuration: issue number must be a positive integer" in errors
    )
    assert (
        "source-ingestion-runtime-configuration: issue URL must be "
        "`https://github.com/sgajbi/lotus-core/issues/790`"
    ) in errors


def test_closure_manifest_rejects_unclassified_proof_artifact_registry(
    monkeypatch: Any,
) -> None:
    snapshot = _strict_default_snapshot()
    contract = _load_contract()
    monkeypatch.setattr(
        closure_manifest_module,
        "IMPLEMENTATION_PROOF_ARTIFACT_SPECS",
        (
            SimpleNamespace(
                cli_flag="--ungoverned-proof",
                evidence_class=None,
                status=ProofArtifactClassificationStatus.PENDING_CORRECTION,
                tracking_issue=0,
            ),
        ),
    )

    errors = blocker_closure_manifest_errors(snapshot=snapshot, contract=contract)

    assert "--ungoverned-proof: proof artifact must be classified before closure" in errors
    assert "--ungoverned-proof: proof artifact must declare an evidence class" in errors
    assert "--ungoverned-proof: proof artifact must name a tracking issue" in errors


def _strict_default_snapshot() -> ImplementationProofReadinessSnapshot:
    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT_UTC,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )


def _load_contract() -> dict[str, Any]:
    payload = json.loads((ROOT / BLOCKER_CLOSURE_CONTRACT_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _without_blocker(contract: dict[str, Any], blocker: str) -> dict[str, Any]:
    updated = copy.deepcopy(contract)
    for group in updated["blockerGroups"]:
        group["blockers"] = [candidate for candidate in group["blockers"] if candidate != blocker]
    return updated
