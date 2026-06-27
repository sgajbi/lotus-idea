from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.report_materialization_proof import (
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_PROOF_ENV,
    REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION,
    REPORT_MATERIALIZATION_ROUTE,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
    build_report_materialization_proof_payload,
    load_report_materialization_proof_from_env,
    report_materialization_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_report_materialization_proof(tmp_path: Path) -> None:
    proof = _valid_report_materialization_proof(tmp_path)

    assert proof["schemaVersion"] == REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "lotus_report_idea_evidence_materialization_contract"
    assert proof["proofScope"] == "source_safe_report_render_archive_materialization"
    assert proof["reportMaterializationProofValid"] is True
    assert proof["targetRoute"] == REPORT_MATERIALIZATION_ROUTE
    assert tuple(proof["aggregateBlockersCleared"]) == REPORT_MATERIALIZATION_BLOCKERS_CLEARED
    assert tuple(proof["evidenceRefs"]) == REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_REPORT_MATERIALIZATION_BLOCKERS
    )
    assert proof["reportMaterializationProven"] is True
    assert proof["renderedOutputCreated"] is True
    assert proof["archiveRecordCreated"] is True
    assert proof["clientPublicationAuthorityGranted"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert report_materialization_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def test_rejects_report_materialization_proof_when_report_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_report_materialization_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        report_root=tmp_path,
    )

    assert proof["reportMaterializationProofValid"] is False
    assert report_materialization_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-report"),
        ("proofType", "route"),
        ("proofScope", "publication"),
        ("reportMaterializationProofValid", False),
        ("targetRoute", "planned:lotus-report-idea-evidence-pack-materialization"),
        ("reportMaterializationProven", False),
        ("renderedOutputCreated", False),
        ("archiveRecordCreated", False),
        ("clientPublicationAuthorityGranted", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_report_materialization_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_report_materialization_proof(tmp_path)
    proof[field_name] = bad_value

    assert report_materialization_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", ("wrong",)),
        ("evidenceRefs", ("wrong",)),
        ("remainingCertificationBlockers", ("wrong",)),
        ("proofChecks", None),
        ("generatedAtUtc", ""),
    ],
)
def test_rejects_report_materialization_proof_with_invalid_collections(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_report_materialization_proof(tmp_path)
    proof[field_name] = bad_value

    assert report_materialization_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "reportContractProvesMaterialization",
        "reportContractPreservesNonProofBoundaries",
        "reportContractRetainsPublicationBlocker",
    ],
)
def test_rejects_report_materialization_proof_with_invalid_proof_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_report_materialization_proof(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert report_materialization_proof_is_valid(proof) is False


def test_report_materialization_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    report_root = _write_report_fixture(tmp_path)
    output_path = tmp_path / "proof" / "report-materialization-proof.json"

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
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert report_materialization_proof_is_valid(proof) is True


def test_report_materialization_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_load_report_materialization_proof_from_env_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(REPORT_MATERIALIZATION_PROOF_ENV, raising=False)

    assert load_report_materialization_proof_from_env() == (None, None)


def test_load_report_materialization_proof_from_env_requires_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(REPORT_MATERIALIZATION_PROOF_ENV, str(proof_path))

    with pytest.raises(ValueError, match="must reference a JSON object"):
        load_report_materialization_proof_from_env()


def test_load_report_materialization_proof_from_env_returns_source_safe_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "proof.json"
    proof_path.write_text(
        json.dumps(_valid_report_materialization_proof(tmp_path)), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(REPORT_MATERIALIZATION_PROOF_ENV, str(proof_path))

    proof, proof_ref = load_report_materialization_proof_from_env()

    assert proof is not None
    assert report_materialization_proof_is_valid(proof) is True
    assert proof_ref == "proof.json"


def test_load_report_materialization_proof_from_env_hides_foreign_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    proof_path = tmp_path / "outside" / "proof.json"
    proof_path.parent.mkdir()
    proof_path.write_text(
        json.dumps(_valid_report_materialization_proof(tmp_path)), encoding="utf-8"
    )
    monkeypatch.chdir(cwd)
    monkeypatch.setenv(REPORT_MATERIALIZATION_PROOF_ENV, str(proof_path))

    proof, proof_ref = load_report_materialization_proof_from_env()

    assert proof is not None
    assert proof_ref == "report materialization proof artifact"


def _valid_report_materialization_proof(tmp_path: Path) -> dict[str, Any]:
    return build_report_materialization_proof_payload(
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
    script_path = ROOT / "scripts" / "generate_report_materialization_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_report_materialization_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "report_materialization_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "report_materialization_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
