# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.report.intake_route_source_contract import (  # noqa: E402
    REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
    build_report_intake_route_source_contract_proof_payload,
    report_intake_route_source_contract_proof_is_valid,
)
from app.domain.proof_evidence import EvidenceClass  # noqa: E402

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


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_report_intake_route_source_contract() -> list[str]:
    errors: list[str] = []
    with TemporaryDirectory(prefix="lotus-idea-report-intake-proof-") as temp_dir:
        proof = build_report_intake_route_source_contract_proof_payload(
            generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            report_root=_write_report_fixture(Path(temp_dir)),
        )
    if proof.get("schemaVersion") != REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION:
        errors.append(
            "Report intake-route source-contract proof schema must be "
            f"{REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION}"
        )
    if proof.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("Report intake-route proof must declare source_contract evidence")
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        errors.append("Report intake-route source-contract evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        errors.append("Report intake-route source-contract proof must clear no blocker")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS
    ):
        errors.append("Report intake-route source contract must retain runtime blockers")
    if not report_intake_route_source_contract_proof_is_valid(proof):
        errors.append("Report intake-route source contract must validate against declaration truth")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


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
            "lotus_report_live_intake_route_proof_missing",
            "report_evidence_pack_live_materialization_proof_missing",
            "rendered_output_creation_missing",
            "archive_record_creation_missing",
            "client_publication_authority_blocked",
        ],
    }


def main() -> int:
    errors = validate_report_intake_route_source_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Report intake-route source-contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
