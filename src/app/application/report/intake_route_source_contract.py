from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
)
from app.domain.proof_evidence import EvidenceClass

_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text
_required_file_evidence_present = required_file_evidence_present


REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV = (
    "LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF"
)
REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.report-intake-route-source-contract-proof.v2"
)

REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED: tuple[str, ...] = ()

REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS = (
    "lotus_report_live_intake_route_proof_missing",
    "report_evidence_pack_live_materialization_proof_missing",
    "rendered_output_creation_missing",
    "archive_record_creation_missing",
    "client_publication_authority_blocked",
)

REPORT_INTAKE_ROUTE = "POST /reports/idea-evidence-packs"

REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS = (
    "src/app/application/report/intake_route_source_contract.py",
    "scripts/report/generate_intake_route_source_contract.py",
    "scripts/report/intake_route_source_contract_gate.py",
    "../lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json",
    "../lotus-report/src/app/idea_evidence_intake/models.py",
    "../lotus-report/src/app/idea_evidence_intake/service.py",
    "../lotus-report/src/app/routers/idea_evidence_intake.py",
    "../lotus-report/tests/unit/test_idea_evidence_intake_service.py",
    "../lotus-report/tests/integration/test_idea_evidence_intake_api.py",
    "contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md",
    "GET /api/v1/downstream-realization/readiness",
    "GET /api/v1/implementation-proof/readiness",
    "make report-intake-route-source-contract-proof-gate",
)


def build_report_intake_route_source_contract_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    report_root: Path | None = None,
) -> dict[str, Any]:
    report_root = report_root or repository_root.parent / "lotus-report"
    contract = _optional_json(
        report_root
        / "contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json"
    )
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={"../lotus-report/": report_root},
        evidence_refs=REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
        non_file_ref_prefixes=("GET ", "POST ", "make "),
    )
    report_contract_declares_compatible_route = _report_contract_declares_compatible_route(contract)
    report_contract_preserves_non_proof_boundaries = (
        _report_contract_preserves_non_proof_boundaries(contract)
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and report_contract_declares_compatible_route
        and report_contract_preserves_non_proof_boundaries
    )
    return {
        "schemaVersion": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_report_idea_evidence_intake_route_source_contract",
        "proofScope": "report_intake_route_declaration_and_contract_compatibility",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "reportIntakeRouteSourceContractValid": proof_valid,
        "aggregateBlockersCleared": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
        "targetRoute": REPORT_INTAKE_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "reportContractDeclaresCompatibleRoute": report_contract_declares_compatible_route,
            "reportContractPreservesNonProofBoundaries": (
                report_contract_preserves_non_proof_boundaries
            ),
        },
        "remainingCertificationBlockers": REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
        "reportRouteServingObserved": False,
        "requestAuthorizationObserved": False,
        "tenantIsolationObserved": False,
        "runtimeExecutionObserved": False,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def report_intake_route_source_contract_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "lotus_report_idea_evidence_intake_route_source_contract":
        return False
    if payload.get("proofScope") != "report_intake_route_declaration_and_contract_compatibility":
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("reportIntakeRouteSourceContractValid") is not True:
        return False
    if payload.get("targetRoute") != REPORT_INTAKE_ROUTE:
        return False
    if any(
        payload.get(field) is not False
        for field in (
            "reportRouteServingObserved",
            "requestAuthorizationObserved",
            "tenantIsolationObserved",
            "runtimeExecutionObserved",
            "reportMaterializationProven",
            "renderedOutputCreated",
            "archiveRecordCreated",
            "clientPublicationAuthorityGranted",
            "supportedFeaturePromoted",
            "proofClosed",
        )
    ):
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS
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
            "reportContractDeclaresCompatibleRoute",
            "reportContractPreservesNonProofBoundaries",
        )
    )


def load_report_intake_route_source_contract_proof_from_env() -> tuple[
    dict[str, Any] | None, str | None
]:
    path_value = os.getenv(REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV)
    if not path_value:
        return None, None
    path = Path(path_value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"{REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV} must reference a JSON object"
        )
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
        return "report intake route source contract proof artifact"


def _report_contract_declares_compatible_route(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    return (
        payload.get("contract_id") == "lotus-report-idea-evidence-pack-intake"
        and payload.get("repository") == "lotus-report"
        and payload.get("approved_producer_repository") == "lotus-idea"
        and payload.get("approved_producer_product") == "lotus-idea:IdeaEvidencePacket:v1"
        and payload.get("owned_product") == "lotus-report:ClientReportEvidencePack:v1"
        and payload.get("lifecycle_status") == "implemented"
        and payload.get("supportability_status") == "not_certified"
        and payload.get("materialization_proven") is False
        and payload.get("supported_feature_promoted") is False
        and payload.get("target_route") == REPORT_INTAKE_ROUTE
    )


def _report_contract_preserves_non_proof_boundaries(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    boundaries = " ".join(str(boundary) for boundary in payload.get("non_proof_boundaries", ()))
    required_fragments = (
        "Does not create a report job",
        "Does not grant suitability",
        "Does not promote a supported feature",
    )
    return all(fragment in boundaries for fragment in required_fragments)
