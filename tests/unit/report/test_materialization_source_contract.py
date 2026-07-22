from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.report.materialization_source_contract import (
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_OWNER_PROOF_REF,
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV,
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
    REPORT_MATERIALIZATION_ROUTE,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
    build_report_materialization_source_contract_payload,
    load_report_materialization_source_contract_from_env,
    report_materialization_source_contract_is_valid,
)
from app.domain.proof_evidence import EvidenceClass

ROOT = Path(__file__).resolve().parents[3]


def test_builds_source_safe_report_materialization_source_contract(tmp_path: Path) -> None:
    artifact = _valid_report_materialization_source_contract(tmp_path)

    assert artifact["schemaVersion"] == REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION
    assert artifact["repository"] == "lotus-idea"
    assert artifact["proofType"] == "lotus_report_idea_evidence_materialization_source_contract"
    assert artifact["proofScope"] == "report_materialization_declaration_and_contract_compatibility"
    assert artifact["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert artifact["sourceContractValid"] is True
    assert artifact["targetRoute"] == REPORT_MATERIALIZATION_ROUTE
    assert tuple(artifact["aggregateBlockersCleared"]) == REPORT_MATERIALIZATION_BLOCKERS_CLEARED
    assert tuple(artifact["evidenceRefs"]) == REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS
    assert REPORT_MATERIALIZATION_OWNER_PROOF_REF in artifact["evidenceRefs"]
    assert tuple(artifact["remainingCertificationBlockers"]) == (
        REMAINING_REPORT_MATERIALIZATION_BLOCKERS
    )
    assert artifact["reportOwnerMaterializationContractConsumed"] is True
    assert artifact["reportOwnerProofRef"] == REPORT_MATERIALIZATION_OWNER_PROOF_REF
    assert artifact["reportMaterializationProven"] is False
    assert artifact["renderedOutputCreated"] is False
    assert artifact["archiveRecordCreated"] is False
    assert artifact["clientPublicationAuthorityGranted"] is False
    assert artifact["supportedFeaturePromoted"] is False
    assert artifact["certificationClosed"] is False
    assert report_materialization_source_contract_is_valid(artifact) is True
    serialized = json.dumps(artifact)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


@pytest.mark.parametrize(
    "inflated_claim",
    [
        "runtimeExecutionProven",
        "deploymentCertified",
        "productionCertified",
        "clientPublicationReady",
        "retentionAuthorityGranted",
    ],
)
def test_rejects_additional_runtime_or_authority_claims(
    inflated_claim: str,
    tmp_path: Path,
) -> None:
    artifact = _valid_report_materialization_source_contract(tmp_path)
    artifact[inflated_claim] = True

    assert report_materialization_source_contract_is_valid(artifact) is False


def test_does_not_infer_runtime_execution_from_report_contract_declarations(
    tmp_path: Path,
) -> None:
    artifact = _valid_report_materialization_source_contract(tmp_path)

    assert _report_contract_payload()["materialization_proven"] is True
    assert artifact["reportMaterializationProven"] is False
    assert artifact["renderedOutputCreated"] is False
    assert artifact["archiveRecordCreated"] is False
    assert tuple(artifact["aggregateBlockersCleared"]) == ()


def test_rejects_source_contract_when_report_contract_evidence_is_missing(
    tmp_path: Path,
) -> None:
    artifact = build_report_materialization_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        report_root=tmp_path,
    )

    assert artifact["sourceContractValid"] is False
    assert report_materialization_source_contract_is_valid(artifact) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-report"),
        ("proofType", "route"),
        ("proofScope", "publication"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("sourceContractValid", False),
        ("targetRoute", "planned:lotus-report-idea-evidence-pack-materialization"),
        ("reportOwnerMaterializationContractConsumed", False),
        ("reportOwnerProofRef", "sgajbi/lotus-report#999999"),
        ("reportMaterializationProven", True),
        ("renderedOutputCreated", True),
        ("archiveRecordCreated", True),
        ("clientPublicationAuthorityGranted", True),
        ("supportedFeaturePromoted", True),
        ("certificationClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_source_contract_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    artifact = _valid_report_materialization_source_contract(tmp_path)
    artifact[field_name] = bad_value

    assert report_materialization_source_contract_is_valid(artifact) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", ("rendered_output_creation_missing",)),
        ("evidenceRefs", ("wrong",)),
        ("remainingCertificationBlockers", ("wrong",)),
        ("contractChecks", None),
        ("generatedAtUtc", ""),
    ],
)
def test_rejects_source_contract_with_invalid_collections(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    artifact = _valid_report_materialization_source_contract(tmp_path)
    artifact[field_name] = bad_value

    assert report_materialization_source_contract_is_valid(artifact) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "reportContractDeclaresMaterialization",
        "reportContractPreservesNonProofBoundaries",
        "reportOwnerProofRefLinked",
    ],
)
def test_rejects_source_contract_with_invalid_contract_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    artifact = _valid_report_materialization_source_contract(tmp_path)
    contract_checks = dict(cast(Mapping[str, object], artifact["contractChecks"]))
    contract_checks[check_name] = False
    artifact["contractChecks"] = contract_checks

    assert report_materialization_source_contract_is_valid(artifact) is False


def test_source_contract_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    report_root = _write_report_fixture(tmp_path)
    output_path = tmp_path / "report" / "materialization-source-contract-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-27T00:00:00Z",
            "--report-root",
            str(report_root),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert report_materialization_source_contract_is_valid(artifact) is True


def test_source_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_load_source_contract_from_env_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV, raising=False)

    assert load_report_materialization_source_contract_from_env() == (None, None)


def test_load_source_contract_from_env_requires_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV, str(proof_path))

    with pytest.raises(ValueError, match="must reference a JSON object"):
        load_report_materialization_source_contract_from_env()


def test_load_source_contract_from_env_returns_source_safe_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "proof.json"
    proof_path.write_text(
        json.dumps(_valid_report_materialization_source_contract(tmp_path)), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV, str(proof_path))

    artifact, artifact_ref = load_report_materialization_source_contract_from_env()

    assert artifact is not None
    assert report_materialization_source_contract_is_valid(artifact) is True
    assert artifact_ref == "proof.json"


def test_load_source_contract_from_env_hides_foreign_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    proof_path = tmp_path / "outside" / "proof.json"
    proof_path.parent.mkdir()
    proof_path.write_text(
        json.dumps(_valid_report_materialization_source_contract(tmp_path)), encoding="utf-8"
    )
    monkeypatch.chdir(cwd)
    monkeypatch.setenv(REPORT_MATERIALIZATION_SOURCE_CONTRACT_ENV, str(proof_path))

    artifact, artifact_ref = load_report_materialization_source_contract_from_env()

    assert artifact is not None
    assert artifact_ref == "report materialization source contract artifact"


def _valid_report_materialization_source_contract(tmp_path: Path) -> dict[str, Any]:
    return build_report_materialization_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        report_root=_write_report_fixture(tmp_path),
    )


def _write_report_fixture(tmp_path: Path) -> Path:
    report_root = tmp_path / "lotus-report"
    required_files = [
        report_root / "contracts/idea-evidence-materialization/"
        "lotus-report-idea-evidence-pack-materialization.v1.json",
        report_root / "src/app/idea_evidence_intake/models.py",
        report_root / "src/app/idea_evidence_intake/service.py",
        report_root / "src/app/routers/idea_evidence_intake.py",
        report_root / "src/app/reporting_lineage/capture_service.py",
        report_root / "src/app/reporting_render/package_builder.py",
        report_root / "tests/unit/test_idea_evidence_materialization_contract.py",
        report_root / "tests/unit/test_idea_evidence_intake_service.py",
        report_root / "tests/integration/test_idea_evidence_intake_api.py",
    ]
    for path in required_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".py":
            path.write_text("# source-safe fixture\n", encoding="utf-8")
    required_files[0].write_text(json.dumps(_report_contract_payload()), encoding="utf-8")
    return report_root


def _report_contract_payload() -> dict[str, object]:
    return {
        "contract_id": "lotus-report-idea-evidence-pack-materialization",
        "repository": "lotus-report",
        "approved_producer_repository": "lotus-idea",
        "approved_producer_product": "lotus-idea:IdeaEvidencePacket:v1",
        "owned_product": "lotus-report:ClientReportEvidencePack:v1",
        "lifecycle_status": "implemented",
        "supportability_status": "not_certified",
        "route_existence_proven": True,
        "materialization_proven": True,
        "rendered_output_creation_proven": True,
        "archive_record_creation_proven": True,
        "client_publication_authority_granted": False,
        "supported_feature_promoted": False,
        "target_route": "POST /reports/idea-evidence-packs/materializations",
        "non_proof_boundaries": [
            "Proves report-owned materialization, rendered output creation, and archive record creation through the governed report job pipeline.",
            "Does not grant suitability, advisory proposal approval, mandate approval, order, execution, settlement, distribution, or client-publication authority.",
            "Does not recompute lotus-idea evidence or upstream portfolio, holding, performance, risk, mandate, or transaction facts.",
            "Does not promote a supported feature in lotus-report or lotus-idea.",
        ],
        "certification_blockers": [
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        ],
    }


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "report" / "generate_materialization_source_contract.py"
    spec = importlib.util.spec_from_file_location(
        "generate_materialization_source_contract",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "report" / "materialization_source_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "materialization_source_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
