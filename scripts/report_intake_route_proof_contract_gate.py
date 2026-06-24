from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from app.application.report_intake_route_proof import (
    REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS,
    build_report_intake_route_proof_payload,
    report_intake_route_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "contentHash",
    "correlationId",
    "holdingId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "account_id",
    "candidate_id",
    "client_id",
    "content_hash",
    "correlation_id",
    "holding_id",
    "portfolio_id",
    "request-body",
    "response-body",
    "/source-owned/",
}


def validate_report_intake_route_proof_contract() -> list[str]:
    errors: list[str] = []
    with TemporaryDirectory(prefix="lotus-idea-report-intake-proof-") as temp_dir:
        proof = build_report_intake_route_proof_payload(
            generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            report_root=_write_report_fixture(Path(temp_dir)),
        )
    if proof.get("schemaVersion") != REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION:
        errors.append(
            f"report intake route proof schema must be {REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS:
        errors.append("report intake route proof evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED):
        errors.append("report intake route proof must clear only the live route blocker")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS
    ):
        errors.append("report intake route proof must retain materialization blockers")
    if not report_intake_route_proof_is_valid(proof):
        errors.append("report intake route proof must validate against report contract truth")
    _validate_forbidden_content(proof, errors)
    return errors


def _validate_forbidden_content(value: object, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text in FORBIDDEN_KEYS:
                errors.append(f"{next_path}: forbidden source-sensitive key is present")
            _validate_forbidden_content(nested, errors, next_path)
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def _write_report_fixture(temp_root: Path) -> Path:
    report_root = temp_root / "lotus-report"
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
        "certification_blockers": [
            "report_evidence_pack_live_materialization_proof_missing",
            "rendered_output_creation_missing",
            "archive_record_creation_missing",
            "client_publication_authority_blocked",
        ],
    }


def main() -> int:
    errors = validate_report_intake_route_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Report intake route proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
