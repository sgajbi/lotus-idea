from __future__ import annotations

from pathlib import Path

import pytest

from app.application.implementation_proof_artifact_registry import (
    ImplementationProofArtifactSpec,
    ProofArtifactClassificationStatus,
    ProofArtifactEffect,
)
from app.domain.proof_evidence import EvidenceClass
from scripts.documentation.implementation_proof_artifact_registry import (
    INVENTORY_PATH,
    implementation_proof_artifact_registry_errors,
)


ROOT = Path(__file__).resolve().parents[3]


def test_implementation_proof_artifact_registry_covers_cli_readiness_and_inventory() -> None:
    assert implementation_proof_artifact_registry_errors(root=ROOT) == []


def test_registry_gate_rejects_missing_inventory_family(tmp_path: Path) -> None:
    inventory = (
        (ROOT / INVENTORY_PATH)
        .read_text(encoding="utf-8")
        .replace(
            "| Advise mandate/restriction source-product contract |",
            "| Unregistered mandate/restriction source-product contract |",
        )
    )
    target = tmp_path / INVENTORY_PATH
    target.parent.mkdir(parents=True)
    target.write_text(inventory, encoding="utf-8")

    errors = implementation_proof_artifact_registry_errors(root=tmp_path)

    assert (
        "docs/architecture/implementation-proof-evidence-classification.md: expected one "
        "`Advise mandate/restriction source-product contract` row"
    ) in errors


def test_registry_gate_requires_pending_tracking_posture(tmp_path: Path) -> None:
    inventory = (
        (ROOT / INVENTORY_PATH)
        .read_text(encoding="utf-8")
        .replace("Pending correction:", "Queued correction:")
        .replace(
            "#508 pending behind #507.",
            "#508 queued behind #507.",
        )
    )
    target = tmp_path / INVENTORY_PATH
    target.parent.mkdir(parents=True)
    target.write_text(inventory, encoding="utf-8")

    errors = implementation_proof_artifact_registry_errors(root=tmp_path)

    assert (
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "`Scheduled source-ingestion worker deployment evidence` must remain pending"
    ) in errors


@pytest.mark.parametrize(
    ("status", "evidence_class", "message"),
    (
        (
            ProofArtifactClassificationStatus.CLASSIFIED,
            None,
            "classified proof artifacts require an evidence class",
        ),
        (
            ProofArtifactClassificationStatus.PENDING_CORRECTION,
            EvidenceClass.DEPLOYMENT,
            "pending proof artifacts must not declare a completed evidence class",
        ),
    ),
)
def test_artifact_spec_rejects_incoherent_classification_state(
    status: ProofArtifactClassificationStatus,
    evidence_class: EvidenceClass | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ImplementationProofArtifactSpec(
            cli_flag="--invalid-proof",
            payload_argument="invalid_proof",
            ref_argument="invalid_proof_ref",
            evidence_class=evidence_class,
            effect=ProofArtifactEffect.BLOCKER_CLEARING,
            inventory_label="Invalid proof",
            tracking_issue=507,
            status=status,
        )
