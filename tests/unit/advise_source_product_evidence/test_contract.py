from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
from typing import Any

import pytest

from app.application.advise_source_product_evidence import (
    MANDATE_RESTRICTION_PROFILE,
    MISSING_RISK_PROFILE,
    PROFILES,
    advise_source_product_source_contract_is_valid,
    build_advise_source_product_source_contract,
)
from app.application.source_authority import source_authority_records_digest
from app.domain.proof_evidence import EvidenceClass


ROOT = Path(__file__).resolve().parents[3]
ADVISE_FIXTURE_ROOT = ROOT / "tests/fixtures/advise_source_product_evidence/lotus-advise"
GENERATED_AT = datetime(2026, 7, 16, 10, 10, tzinfo=UTC)


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_source_contract_binds_current_advise_authority_without_promoting_runtime(
    capability: str,
) -> None:
    profile = PROFILES[capability]
    payload = _payload(capability)

    assert payload["schemaVersion"] == "lotus-idea.advise-source-product-evidence.v2"
    assert payload["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert payload["sourceContractValid"] is True
    assert payload["sourceContractBlockersSatisfied"] == list(profile.blockers_satisfied)
    assert payload["requiredBlockerEvidenceClasses"] == {
        blocker: EvidenceClass.SOURCE_CONTRACT.value for blocker in profile.blockers_satisfied
    }
    assert payload["sourceRepository"] == "lotus-advise"
    assert payload["sourceProductId"] == ("lotus-advise:AdvisoryPolicyEvaluationRecord:v1")
    assert len(payload["sourceAuthority"]) == 2
    assert payload["sourceAuthorityDigest"] == source_authority_records_digest(
        payload["sourceAuthority"]
    )
    assert payload["contractChecks"] == {
        "timezoneAwareGeneratedAtUtc": True,
        "sourceAuthorityDigestBound": True,
        "producerDeclarationValid": True,
        "producerApprovesLotusIdeaConsumer": True,
        "producerTrustTelemetryIdentityValid": True,
        "producerTrustTelemetryBlockedPosturePreserved": True,
        "requiredDiagnosticsDefined": True,
        "ideaAuthorityBoundaryPreserved": True,
    }
    assert payload["diagnosticContract"]["requiredDiagnostics"] == list(
        profile.required_diagnostics
    )
    assert not any(payload["authorityClaims"].values())
    assert advise_source_product_source_contract_is_valid(payload, profile=profile)
    serialized = json.dumps(payload)
    for forbidden in (
        "portfolioId",
        "clientId",
        "candidateId",
        "evaluationId",
        "PB_SG_GLOBAL_BAL_001",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_source_contract_fails_closed_without_authoritative_advise_sources(
    capability: str,
    tmp_path: Path,
) -> None:
    profile = PROFILES[capability]
    payload = build_advise_source_product_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        advise_root=tmp_path,
        profile=profile,
    )

    assert payload["sourceContractValid"] is False
    assert payload["sourceAuthorityDigest"] is None
    assert not advise_source_product_source_contract_is_valid(payload, profile=profile)


@pytest.mark.parametrize(
    ("mutation_path", "value"),
    (
        (("evidenceClass",), EvidenceClass.RUNTIME_EXECUTION.value),
        (("sourceContractBlockersSatisfied",), ()),
        (("sourceProductId",), "lotus-idea:AdvisoryPolicyEvaluationRecord:v1"),
        (("authorityClaims", "riskProfileApprovalGranted"), True),
        (("contractChecks", "producerTrustTelemetryBlockedPosturePreserved"), False),
        (("diagnosticContract", "diagnosticsOwnedBy"), "lotus-idea"),
    ),
)
@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_source_contract_rejects_claim_and_semantic_tampering(
    capability: str,
    mutation_path: tuple[str, ...],
    value: object,
) -> None:
    profile = PROFILES[capability]
    payload = _payload(capability)
    target: dict[str, object] = payload
    for key in mutation_path[:-1]:
        nested = target[key]
        assert isinstance(nested, dict)
        target = nested
    target[mutation_path[-1]] = value
    payload["sourceAuthorityDigest"] = source_authority_records_digest(payload["sourceAuthority"])

    assert not advise_source_product_source_contract_is_valid(payload, profile=profile)


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_source_contract_rejects_unknown_top_level_and_nested_fields(
    capability: str,
) -> None:
    profile = PROFILES[capability]
    top_level = _payload(capability)
    top_level["runtimeCertified"] = True
    nested = _payload(capability)
    nested["authorityClaims"]["unknownAuthority"] = False

    assert not advise_source_product_source_contract_is_valid(top_level, profile=profile)
    assert not advise_source_product_source_contract_is_valid(nested, profile=profile)


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_source_contract_rejects_source_authority_digest_tampering(capability: str) -> None:
    profile = PROFILES[capability]
    payload = _payload(capability)
    payload["sourceAuthority"][0]["sha256"] = "0" * 64

    assert not advise_source_product_source_contract_is_valid(payload, profile=profile)


@pytest.mark.parametrize(
    ("capability", "contract_mutation"),
    (
        (
            MANDATE_RESTRICTION_PROFILE.capability,
            ("lifecycle_status", "proposed"),
        ),
        (
            MISSING_RISK_PROFILE.capability,
            ("approved_consumers", ["lotus-gateway"]),
        ),
    ),
)
def test_source_contract_rejects_changed_producer_declaration(
    capability: str,
    contract_mutation: tuple[str, object],
    tmp_path: Path,
) -> None:
    advise_root = tmp_path / "lotus-advise"
    shutil.copytree(ADVISE_FIXTURE_ROOT, advise_root)
    contract_path = advise_root / "contracts/domain-data-products/lotus-advise-products.v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["products"][0][contract_mutation[0]] = contract_mutation[1]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    profile = PROFILES[capability]
    payload = build_advise_source_product_source_contract(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        advise_root=advise_root,
        profile=profile,
    )

    assert payload["sourceContractValid"] is False
    assert not advise_source_product_source_contract_is_valid(payload, profile=profile)


def _payload(capability: str) -> dict[str, Any]:
    return deepcopy(
        build_advise_source_product_source_contract(
            generated_at_utc=GENERATED_AT,
            repository_root=ROOT,
            advise_root=ADVISE_FIXTURE_ROOT,
            profile=PROFILES[capability],
        )
    )
