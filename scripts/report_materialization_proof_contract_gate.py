from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.report_materialization_proof import (  # noqa: E402
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
    build_report_materialization_proof_payload,
    report_materialization_proof_is_valid,
)

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


def validate_report_materialization_proof_contract() -> list[str]:
    errors: list[str] = []
    with TemporaryDirectory(prefix="lotus-idea-report-materialization-proof-") as temp_dir:
        proof = build_report_materialization_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            report_root=_write_report_fixture(Path(temp_dir)),
        )
    if proof.get("schemaVersion") != REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION:
        errors.append(
            "report materialization proof schema must be "
            f"{REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS:
        errors.append("report materialization proof evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        REPORT_MATERIALIZATION_BLOCKERS_CLEARED
    ):
        errors.append("report materialization proof must clear only materialization blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_REPORT_MATERIALIZATION_BLOCKERS
    ):
        errors.append("report materialization proof must retain publication blockers")
    if not report_materialization_proof_is_valid(proof):
        errors.append("report materialization proof must validate against report contract truth")
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
    errors = validate_report_materialization_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Report materialization proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
