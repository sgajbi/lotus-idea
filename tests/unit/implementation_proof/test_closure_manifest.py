from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.application.implementation_proof_closure_manifest import (
    BLOCKER_CLOSURE_CONTRACT_PATH,
    blocker_closure_manifest_errors,
    blocker_closure_manifest_payload,
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
