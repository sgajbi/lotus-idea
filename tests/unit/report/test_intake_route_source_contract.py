from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.report_intake_route_proof import (
    REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS,
    build_report_intake_route_proof_payload,
    report_intake_route_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_report_intake_route_proof(tmp_path: Path) -> None:
    proof = _valid_report_intake_route_proof(tmp_path)

    assert proof["schemaVersion"] == REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "lotus_report_idea_evidence_intake_route_contract"
    assert proof["proofScope"] == "source_safe_report_intake_route_only"
    assert proof["reportIntakeRouteProofValid"] is True
    assert proof["targetRoute"] == REPORT_INTAKE_ROUTE
    assert tuple(proof["aggregateBlockersCleared"]) == REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED
    assert tuple(proof["evidenceRefs"]) == REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS
    )
    assert proof["reportMaterializationProven"] is False
    assert proof["renderedOutputCreated"] is False
    assert proof["archiveRecordCreated"] is False
    assert proof["clientPublicationAuthorityGranted"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert report_intake_route_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def test_rejects_report_intake_route_proof_when_report_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_report_intake_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        report_root=tmp_path,
    )

    assert proof["reportIntakeRouteProofValid"] is False
    assert report_intake_route_proof_is_valid(proof) is False


def test_rejects_report_intake_route_proof_when_route_blocker_is_still_present(
    tmp_path: Path,
) -> None:
    report_root = _write_report_fixture(tmp_path)
    contract_path = (
        report_root
        / "contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["certification_blockers"] = [
        "lotus_report_live_intake_route_proof_missing",
        *REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    ]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    proof = build_report_intake_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        report_root=report_root,
    )

    assert proof["reportIntakeRouteProofValid"] is False
    assert report_intake_route_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-report"),
        ("proofType", "route"),
        ("proofScope", "materialization"),
        ("reportIntakeRouteProofValid", False),
        ("targetRoute", "planned:lotus-report-idea-evidence-pack-intake"),
        ("reportMaterializationProven", True),
        ("renderedOutputCreated", True),
        ("archiveRecordCreated", True),
        ("clientPublicationAuthorityGranted", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_report_intake_route_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_report_intake_route_proof(tmp_path)
    proof[field_name] = bad_value

    assert report_intake_route_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_report_intake_route_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_report_intake_route_proof(tmp_path)
    proof[field_name] = bad_value

    assert report_intake_route_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "reportContractProvesRoute",
        "reportContractPreservesNonProofBoundaries",
        "reportContractRetainsMaterializationBlockers",
    ],
)
def test_rejects_report_intake_route_proof_with_invalid_proof_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_report_intake_route_proof(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert report_intake_route_proof_is_valid(proof) is False


def test_report_intake_route_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    report_root = _write_report_fixture(tmp_path)
    output_path = tmp_path / "proof" / "report-intake-route-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--report-root",
            str(report_root),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert report_intake_route_proof_is_valid(proof) is True


def test_report_intake_route_proof_cli_allows_missing_sibling_evidence_for_default_readiness(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "report-intake-route-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--report-root",
            str(tmp_path / "missing-lotus-report"),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["reportIntakeRouteProofValid"] is False
    assert proof["proofChecks"]["fileEvidencePresent"] is False
    assert report_intake_route_proof_is_valid(proof) is False


def test_report_intake_route_proof_cli_still_fails_contract_drift_when_evidence_exists(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    report_root = _write_report_fixture(tmp_path)
    contract_path = (
        report_root
        / "contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["supported_feature_promoted"] = True
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    output_path = tmp_path / "proof" / "report-intake-route-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--report-root",
            str(report_root),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 1
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["proofChecks"]["fileEvidencePresent"] is True
    assert proof["proofChecks"]["reportContractProvesRoute"] is False


def test_report_intake_route_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def _valid_report_intake_route_proof(tmp_path: Path) -> dict[str, Any]:
    return build_report_intake_route_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        report_root=_write_report_fixture(tmp_path),
    )


def _write_report_fixture(tmp_path: Path) -> Path:
    report_root = tmp_path / "lotus-report"
    required_files = [
        report_root
        / "contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json",
        report_root / "src/app/idea_evidence_intake/models.py",
        report_root / "src/app/idea_evidence_intake/service.py",
        report_root / "src/app/routers/idea_evidence_intake.py",
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
        "contract_id": "lotus-report-idea-evidence-pack-intake",
        "repository": "lotus-report",
        "approved_producer_repository": "lotus-idea",
        "approved_producer_product": "lotus-idea:IdeaEvidencePacket:v1",
        "owned_product": "lotus-report:ClientReportEvidencePack:v1",
        "lifecycle_status": "implemented",
        "supportability_status": "not_certified",
        "route_existence_proven": True,
        "materialization_proven": False,
        "supported_feature_promoted": False,
        "target_route": "POST /reports/idea-evidence-packs",
        "non_proof_boundaries": [
            "Proves only a live lotus-report intake route for source-safe lotus-idea evidence-pack handoff.",
            "Does not create a report job, render package, rendered document, archive record, or client-ready publication.",
            "Does not grant suitability, advisory, mandate, execution, or client-communication authority.",
            "Does not promote a supported feature in lotus-report or lotus-idea.",
        ],
        "certification_blockers": list(REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS),
    }


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_report_intake_route_proof.py"
    spec = importlib.util.spec_from_file_location("generate_report_intake_route_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "report_intake_route_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "report_intake_route_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
