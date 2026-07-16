from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import app.application.implementation_proof_artifact_registry as artifact_registry
import scripts.documentation.implementation_proof_artifact_registry as registry_gate
from app.application.implementation_proof_artifact_registry import (
    IMPLEMENTATION_PROOF_ARTIFACT_SPECS,
    ImplementationProofArtifactSpec,
    ProofArtifactClassificationStatus,
    ProofArtifactEffect,
    proof_artifact_effect_matches_payload,
    proof_artifact_effect_matches_ref,
    proof_artifact_spec_for_payload_argument,
    proof_artifact_spec_for_ref_argument,
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


def test_registry_gate_requires_scheduler_source_contract_classification(
    tmp_path: Path,
) -> None:
    inventory = (
        (ROOT / INVENTORY_PATH)
        .read_text(encoding="utf-8")
        .replace(
            "| Scheduled source-ingestion worker source contract | `source_contract` |",
            "| Scheduled source-ingestion worker source contract | `deployment` |",
        )
    )
    target = tmp_path / INVENTORY_PATH
    target.parent.mkdir(parents=True)
    target.write_text(inventory, encoding="utf-8")

    errors = implementation_proof_artifact_registry_errors(root=tmp_path)

    assert (
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "`Scheduled source-ingestion worker source contract` must name `source_contract`"
    ) in errors


def test_registry_gate_requires_scheduler_deployment_classification(
    tmp_path: Path,
) -> None:
    inventory = (
        (ROOT / INVENTORY_PATH)
        .read_text(encoding="utf-8")
        .replace(
            "| Scheduled source-ingestion worker deployment evidence | `deployment` |",
            "| Scheduled source-ingestion worker deployment evidence | `source_contract` |",
        )
    )
    target = tmp_path / INVENTORY_PATH
    target.parent.mkdir(parents=True)
    target.write_text(inventory, encoding="utf-8")

    errors = implementation_proof_artifact_registry_errors(root=tmp_path)

    assert (
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "`Scheduled source-ingestion worker deployment evidence` must name `deployment`"
    ) in errors


@pytest.mark.parametrize(
    ("field_name", "duplicate_field", "message"),
    (
        (
            "cli_flag",
            "--source-ingestion-runtime-execution",
            "duplicate flags",
        ),
        (
            "payload_argument",
            "source_ingestion_runtime_execution",
            "duplicate payload arguments",
        ),
        (
            "ref_argument",
            "source_ingestion_runtime_execution_ref",
            "duplicate reference arguments",
        ),
    ),
)
def test_registry_gate_rejects_duplicate_consumption_keys(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    duplicate_field: str,
    message: str,
) -> None:
    source = IMPLEMENTATION_PROOF_ARTIFACT_SPECS[1]
    if field_name == "cli_flag":
        duplicate = replace(
            source,
            cli_flag=duplicate_field,
            ref_argument="unique_ref_argument",
        )
    elif field_name == "payload_argument":
        duplicate = replace(
            source,
            cli_flag="--unique-payload-proof",
            payload_argument=duplicate_field,
            ref_argument="unique_payload_proof_ref",
        )
    else:
        duplicate = replace(
            source,
            cli_flag="--unique-reference-proof",
            payload_argument="unique_reference_proof",
            ref_argument=duplicate_field,
        )
    monkeypatch.setattr(
        registry_gate,
        "IMPLEMENTATION_PROOF_ARTIFACT_SPECS",
        (*IMPLEMENTATION_PROOF_ARTIFACT_SPECS, duplicate),
    )

    errors = implementation_proof_artifact_registry_errors(root=ROOT)

    assert any(message in error for error in errors)


def test_registry_lookup_requires_one_classified_effect_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_argument = "durable_repository_proof"
    ref_argument = "durable_repository_proof_ref"

    assert proof_artifact_spec_for_payload_argument(payload_argument) is not None
    assert proof_artifact_spec_for_ref_argument(ref_argument) is not None
    assert proof_artifact_effect_matches_payload(
        payload_argument,
        ProofArtifactEffect.BLOCKER_CLEARING,
    )
    assert proof_artifact_effect_matches_ref(
        ref_argument,
        ProofArtifactEffect.BLOCKER_CLEARING,
    )
    assert not proof_artifact_effect_matches_payload(
        payload_argument,
        ProofArtifactEffect.SUPPORTING_EVIDENCE,
    )

    duplicate = next(
        spec
        for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS
        if spec.payload_argument == payload_argument
    )
    monkeypatch.setattr(
        artifact_registry,
        "IMPLEMENTATION_PROOF_ARTIFACT_SPECS",
        (*IMPLEMENTATION_PROOF_ARTIFACT_SPECS, duplicate),
    )

    assert proof_artifact_spec_for_payload_argument(payload_argument) is None
    assert proof_artifact_spec_for_ref_argument(ref_argument) is None
    assert not proof_artifact_effect_matches_payload(
        payload_argument,
        ProofArtifactEffect.BLOCKER_CLEARING,
    )
    assert not proof_artifact_effect_matches_ref(
        ref_argument,
        ProofArtifactEffect.BLOCKER_CLEARING,
    )


def test_registry_effect_match_rejects_pending_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_argument = "durable_repository_proof"
    specs = tuple(
        replace(
            spec,
            evidence_class=None,
            status=ProofArtifactClassificationStatus.PENDING_CORRECTION,
        )
        if spec.payload_argument == payload_argument
        else spec
        for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS
    )
    monkeypatch.setattr(
        artifact_registry,
        "IMPLEMENTATION_PROOF_ARTIFACT_SPECS",
        specs,
    )

    assert not proof_artifact_effect_matches_payload(
        payload_argument,
        ProofArtifactEffect.BLOCKER_CLEARING,
    )


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
