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

from app.application.report.materialization_source_contract import (  # noqa: E402
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
    build_report_materialization_source_contract_payload,
    report_materialization_source_contract_is_valid,
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


def validate_report_materialization_source_contract() -> list[str]:
    errors: list[str] = []
    with TemporaryDirectory(prefix="lotus-idea-report-materialization-source-") as temp_dir:
        artifact = build_report_materialization_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            report_root=_write_report_fixture(Path(temp_dir)),
        )
    if artifact.get("schemaVersion") != REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION:
        errors.append(
            "report materialization source-contract schema must be "
            f"{REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION}"
        )
    if artifact.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("report materialization artifact must declare source_contract evidence")
    if tuple(artifact.get("evidenceRefs") or ()) != REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS:
        errors.append("report materialization source-contract refs must match the contract")
    if tuple(artifact.get("aggregateBlockersCleared") or ()) != (
        REPORT_MATERIALIZATION_BLOCKERS_CLEARED
    ):
        errors.append("report materialization source contract must clear no blockers")
    if tuple(artifact.get("remainingCertificationBlockers") or ()) != (
        REMAINING_REPORT_MATERIALIZATION_BLOCKERS
    ):
        errors.append("report materialization source contract must retain runtime blockers")
    if not report_materialization_source_contract_is_valid(artifact):
        errors.append("report materialization artifact must validate as a source contract")
    validate_forbidden_content(artifact, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def _write_report_fixture(temp_root: Path) -> Path:
    report_root = temp_root / "lotus-report"
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


def main() -> int:
    errors = validate_report_materialization_source_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Report materialization source contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
