from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, cast

import pytest

from app.application.ai_attestation.source_contract import (
    AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
    AI_ATTESTATION_SOURCE_CONTRACT_SCHEMA_VERSION,
    REMAINING_AI_ATTESTATION_CERTIFICATION_BLOCKERS,
    build_ai_attestation_source_contract,
    idea_consumer_source_contract_is_valid,
    signed_ai_attestation_source_contract_is_valid,
)
from app.domain.proof_evidence import EvidenceClass
from tests.support.ai_attestation.source_fixture import write_lotus_ai_attestation_source


ROOT = Path(__file__).resolve().parents[3]
GENERATED_AT = datetime(2026, 7, 15, 0, 0, tzinfo=UTC)


def test_builds_closed_digest_bound_signed_ai_attestation_source_contract(
    tmp_path: Path,
) -> None:
    payload = _valid_payload(tmp_path)

    assert payload["schemaVersion"] == AI_ATTESTATION_SOURCE_CONTRACT_SCHEMA_VERSION
    assert payload["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert payload["validationScope"] == "full_cross_repository"
    assert payload["sourceContractValid"] is True
    assert payload["consumerSourceContractValid"] is True
    assert payload["producerSourceContractValid"] is True
    assert payload["sourceContractBlockersSatisfied"] == (
        AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == (
        REMAINING_AI_ATTESTATION_CERTIFICATION_BLOCKERS
    )
    assert len(cast(str, payload["consumerSourceAuthorityDigest"])) == 64
    assert len(cast(str, payload["producerSourceAuthorityDigest"])) == 64
    assert signed_ai_attestation_source_contract_is_valid(payload) is True


def test_missing_producer_is_explicit_consumer_only_non_proof(tmp_path: Path) -> None:
    payload = build_ai_attestation_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        lotus_ai_root=tmp_path / "missing-lotus-ai",
    )

    assert payload["validationScope"] == "idea_consumer_only"
    assert payload["sourceContractValid"] is False
    assert payload["consumerSourceContractValid"] is True
    assert payload["producerSourceContractValid"] is False
    assert payload["producerSourceAuthorityDigest"] is None
    assert idea_consumer_source_contract_is_valid(payload) is True
    assert signed_ai_attestation_source_contract_is_valid(payload) is False


def test_changed_producer_source_changes_bound_collection_digest(tmp_path: Path) -> None:
    producer_root = write_lotus_ai_attestation_source(tmp_path / "lotus-ai")
    original = build_ai_attestation_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        lotus_ai_root=producer_root,
    )
    signing_path = producer_root / "src/app/services/workflow_run_attestation_signing.py"
    signing_path.write_text(
        signing_path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8"
    )
    changed = build_ai_attestation_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        lotus_ai_root=producer_root,
    )

    assert original["producerSourceAuthorityDigest"] != changed["producerSourceAuthorityDigest"]
    assert signed_ai_attestation_source_contract_is_valid(changed) is True


def test_missing_required_producer_declaration_fails_closed(tmp_path: Path) -> None:
    producer_root = write_lotus_ai_attestation_source(tmp_path / "lotus-ai")
    issuance = producer_root / "src/app/services/workflow_run_attestation_issuance.py"
    issuance.write_text("model_risk_status = 'approved'\n", encoding="utf-8")

    payload = build_ai_attestation_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        lotus_ai_root=producer_root,
    )

    assert payload["contractChecks"]["producerIssuanceFailClosed"] is False
    assert payload["sourceContractValid"] is False
    assert signed_ai_attestation_source_contract_is_valid(payload) is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schemaVersion", "v1"),
        ("repository", "lotus-ai"),
        ("proofType", "runtime_execution"),
        ("proofScope", "production"),
        ("validationScope", "production"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("sourceContractValid", False),
        ("consumerSourceContractValid", False),
        ("producerSourceContractValid", False),
        ("sourceContractBlockersSatisfied", ("lotus_ai_runtime_execution_missing",)),
        (
            "requiredBlockerEvidenceClasses",
            {"lotus_ai_runtime_execution_missing": "source_contract"},
        ),
        ("evidenceRefs", ()),
        ("remainingCertificationBlockers", ()),
        ("generatedAtUtc", "2026-07-15T00:00:00"),
        ("runtimeExecutionObserved", True),
        ("liveProviderExecuted", True),
        ("modelRiskApprovalObserved", True),
        ("deploymentObserved", True),
        ("productionCertificationGranted", True),
        ("workbenchProductProofCertified", True),
        ("clientReadyPublicationAuthorized", True),
        ("supportedFeaturePromoted", True),
        ("certificationClosed", True),
    ],
)
def test_rejects_identity_boundary_or_authority_claim_mutation(
    field: str,
    value: object,
    tmp_path: Path,
) -> None:
    payload = _valid_payload(tmp_path)
    payload[field] = value

    assert signed_ai_attestation_source_contract_is_valid(payload) is False


@pytest.mark.parametrize("container", ["payload", "checks", "consumer_source", "producer_source"])
def test_rejects_unknown_fields(container: str, tmp_path: Path) -> None:
    payload = _valid_payload(tmp_path)
    if container == "payload":
        payload["runtimeCertified"] = True
    elif container == "checks":
        cast(dict[str, object], payload["contractChecks"])["productionCertified"] = True
    else:
        field = (
            "consumerSourceAuthority"
            if container == "consumer_source"
            else "producerSourceAuthority"
        )
        sources = [dict(item) for item in cast(tuple[Mapping[str, object], ...], payload[field])]
        sources[0]["runtimeCertified"] = True
        payload[field] = sources

    assert signed_ai_attestation_source_contract_is_valid(payload) is False


@pytest.mark.parametrize("authority", ["consumer", "producer"])
def test_rejects_source_authority_identity_digest_or_collection_substitution(
    authority: str,
    tmp_path: Path,
) -> None:
    payload = _valid_payload(tmp_path)
    field = f"{authority}SourceAuthority"
    sources = [dict(item) for item in cast(tuple[Mapping[str, object], ...], payload[field])]
    sources[0]["sha256"] = "b" * 64
    payload[field] = sources

    assert signed_ai_attestation_source_contract_is_valid(payload) is False

    payload = _valid_payload(tmp_path)
    payload[f"{authority}SourceAuthorityDigest"] = "b" * 64
    assert signed_ai_attestation_source_contract_is_valid(payload) is False


@pytest.mark.parametrize(
    "check",
    [
        "timezoneAwareGeneratedAtUtc",
        "consumerSourceAuthorityDigestBound",
        "producerSourceAuthorityDigestBound",
        "producerClaimsDeclared",
        "producerSigningDeclared",
        "producerIssuanceFailClosed",
        "consumerVerificationDeclared",
        "consumerReplayPersistenceDeclared",
        "evidenceClassMatchesBlockers",
    ],
)
def test_rejects_false_contract_check(check: str, tmp_path: Path) -> None:
    payload = _valid_payload(tmp_path)
    checks = dict(cast(Mapping[str, object], payload["contractChecks"]))
    checks[check] = False
    payload["contractChecks"] = checks

    assert signed_ai_attestation_source_contract_is_valid(payload) is False


def _valid_payload(tmp_path: Path) -> dict[str, Any]:
    return build_ai_attestation_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        lotus_ai_root=write_lotus_ai_attestation_source(tmp_path / "lotus-ai"),
    )
