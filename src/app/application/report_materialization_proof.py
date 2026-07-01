from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text

_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text

REPORT_MATERIALIZATION_PROOF_ENV = "LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF"
REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION = "lotus-idea.report-materialization-proof.v1"

REPORT_MATERIALIZATION_BLOCKERS_CLEARED = (
    "report_evidence_pack_live_materialization_proof_missing",
    "rendered_output_creation_missing",
    "archive_record_creation_missing",
)

REMAINING_REPORT_MATERIALIZATION_BLOCKERS = ("client_publication_authority_blocked",)

REPORT_MATERIALIZATION_ROUTE = "POST /reports/idea-evidence-packs/materializations"

REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS = (
    "../lotus-report/contracts/idea-evidence-materialization/"
    "lotus-report-idea-evidence-pack-materialization.v1.json",
    "../lotus-report/src/app/idea_evidence_intake/models.py",
    "../lotus-report/src/app/idea_evidence_intake/service.py",
    "../lotus-report/src/app/routers/idea_evidence_intake.py",
    "../lotus-report/src/app/reporting_lineage/capture_service.py",
    "../lotus-report/src/app/reporting_render/package_builder.py",
    "../lotus-report/tests/unit/test_idea_evidence_materialization_contract.py",
    "../lotus-report/tests/unit/test_idea_evidence_intake_service.py",
    "../lotus-report/tests/integration/test_idea_evidence_intake_api.py",
    "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
    "GET /api/v1/downstream-realization/readiness",
    "GET /api/v1/implementation-proof/readiness",
)


def build_report_materialization_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    report_root: Path | None = None,
) -> dict[str, Any]:
    report_root = report_root or repository_root.parent / "lotus-report"
    contract = _optional_json(
        report_root / "contracts/idea-evidence-materialization/"
        "lotus-report-idea-evidence-pack-materialization.v1.json"
    )
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        report_root=report_root,
        evidence_refs=REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
    )
    report_contract_proves_materialization = _report_contract_proves_materialization(contract)
    report_contract_preserves_non_proof_boundaries = (
        _report_contract_preserves_non_proof_boundaries(contract)
    )
    report_contract_retains_publication_blocker = _report_contract_retains_publication_blocker(
        contract
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and report_contract_proves_materialization
        and report_contract_preserves_non_proof_boundaries
        and report_contract_retains_publication_blocker
    )
    return {
        "schemaVersion": REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_report_idea_evidence_materialization_contract",
        "proofScope": "source_safe_report_render_archive_materialization",
        "reportMaterializationProofValid": proof_valid,
        "aggregateBlockersCleared": REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "reportContractProvesMaterialization": report_contract_proves_materialization,
            "reportContractPreservesNonProofBoundaries": (
                report_contract_preserves_non_proof_boundaries
            ),
            "reportContractRetainsPublicationBlocker": (
                report_contract_retains_publication_blocker
            ),
        },
        "remainingCertificationBlockers": REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
        "reportMaterializationProven": True,
        "renderedOutputCreated": True,
        "archiveRecordCreated": True,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def report_materialization_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "lotus_report_idea_evidence_materialization_contract":
        return False
    if payload.get("proofScope") != "source_safe_report_render_archive_materialization":
        return False
    if payload.get("reportMaterializationProofValid") is not True:
        return False
    if payload.get("targetRoute") != REPORT_MATERIALIZATION_ROUTE:
        return False
    if payload.get("reportMaterializationProven") is not True:
        return False
    if payload.get("renderedOutputCreated") is not True:
        return False
    if payload.get("archiveRecordCreated") is not True:
        return False
    if payload.get("clientPublicationAuthorityGranted") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        REPORT_MATERIALIZATION_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_REPORT_MATERIALIZATION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "reportContractProvesMaterialization",
            "reportContractPreservesNonProofBoundaries",
            "reportContractRetainsPublicationBlocker",
        )
    )


def load_report_materialization_proof_from_env() -> tuple[dict[str, Any] | None, str | None]:
    path_value = os.getenv(REPORT_MATERIALIZATION_PROOF_ENV)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{REPORT_MATERIALIZATION_PROOF_ENV} must reference a JSON object")
    return payload, _source_safe_artifact_ref(path)


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _source_safe_artifact_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return "report materialization proof artifact"


def _report_contract_proves_materialization(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    return (
        payload.get("contract_id") == "lotus-report-idea-evidence-pack-materialization"
        and payload.get("repository") == "lotus-report"
        and payload.get("approved_producer_repository") == "lotus-idea"
        and payload.get("approved_producer_product") == "lotus-idea:IdeaEvidencePacket:v1"
        and payload.get("owned_product") == "lotus-report:ClientReportEvidencePack:v1"
        and payload.get("lifecycle_status") == "implemented"
        and payload.get("supportability_status") == "not_certified"
        and payload.get("route_existence_proven") is True
        and payload.get("materialization_proven") is True
        and payload.get("rendered_output_creation_proven") is True
        and payload.get("archive_record_creation_proven") is True
        and payload.get("client_publication_authority_granted") is False
        and payload.get("supported_feature_promoted") is False
        and payload.get("target_route") == REPORT_MATERIALIZATION_ROUTE
    )


def _report_contract_preserves_non_proof_boundaries(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    boundaries = " ".join(str(boundary) for boundary in payload.get("non_proof_boundaries", ()))
    required_fragments = (
        "Proves report-owned materialization",
        "Does not grant suitability",
        "Does not recompute lotus-idea evidence",
        "Does not promote a supported feature",
    )
    return all(fragment in boundaries for fragment in required_fragments)


def _report_contract_retains_publication_blocker(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    blockers = set(payload.get("certification_blockers", ()))
    return blockers == {
        "client_publication_authority_blocked",
        "supported_feature_promotion_missing",
    }


def _required_file_evidence_present(
    *,
    repository_root: Path,
    report_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(("GET ", "POST ", "make ")):
            continue
        if ref.startswith("../lotus-report/"):
            path = report_root / ref.removeprefix("../lotus-report/")
        else:
            path = repository_root / ref
        if not path.is_file():
            return False
    return True
