from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.application.concentration_risk_signal import (
    ConcentrationRiskSignalPersistenceResult,
    EvaluateAndPersistConcentrationRiskFromRiskCommand,
)
from app.domain import (
    EvidenceFreshness,
    OpportunityFamily,
    SourceRef,
    SourceSystem,
)
from app.domain.proof_evidence import EvidenceClass
from app.application.risk_runtime_evidence import (
    build_runtime_receipts,
    sha256_json,
)

RISK_CONCENTRATION_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF"
RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.risk-concentration.runtime-execution.v2"
)
RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_risk_source_proof_missing",
)
RISK_CONCENTRATION_REMAINING_BLOCKERS = (
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
    "deployment_certification_missing",
    "production_certification_missing",
)
RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/risk_concentration_runtime_evidence/runtime_execution.py",
    "src/app/application/risk_concentration_runtime_evidence/contract.py",
    "src/app/application/concentration_risk_signal.py",
    "src/app/ports/risk_sources.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "scripts/risk_concentration_runtime_evidence/generate_runtime_execution.py",
    "make risk-concentration-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-risk:ConcentrationRiskReport:v1"


def build_risk_concentration_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    result: ConcentrationRiskSignalPersistenceResult,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    source_receipt, persistence_receipt = _receipts(command=command, result=result)
    blockers = _qualification_blockers(
        result=result,
        durable_storage_backed=durable_storage_backed,
        source_receipt=source_receipt,
        persistence_receipt=persistence_receipt,
    )
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="completed",
        durable_storage_backed=durable_storage_backed,
        source_receipt=source_receipt,
        persistence_receipt=persistence_receipt,
        qualification_blockers=blockers,
    )


def build_blocked_risk_concentration_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    error_code: str,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    blockers = [f"source_error_{error_code.strip() or 'risk_source_unavailable'}"]
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    blockers.extend(("authoritative_source_receipt_missing", "persistence_receipt_missing"))
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="blocked",
        durable_storage_backed=durable_storage_backed,
        source_receipt=None,
        persistence_receipt=None,
        qualification_blockers=tuple(blockers),
    )


def _payload(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    status: str,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    request = command.evaluation
    return {
        "schemaVersion": RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "risk_concentration",
        "proofType": "lotus_risk_concentration_candidate_persistence",
        "sourceAuthority": SourceSystem.LOTUS_RISK.value,
        "generatedAtUtc": _format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "durableStorageBacked": durable_storage_backed,
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "asOfDate": request.as_of_date.isoformat(),
            "requestFingerprint": _request_fingerprint(command),
            "sourceReceipt": source_receipt,
            "persistenceReceipt": persistence_receipt,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(RISK_CONCENTRATION_REMAINING_BLOCKERS),
        "evidenceRefs": list(RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "officialRiskCalculationOwned": "lotus-risk",
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
        },
    }


def _receipts(
    *,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    result: ConcentrationRiskSignalPersistenceResult,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    candidate = result.evaluation.candidate
    return build_runtime_receipts(
        candidate=candidate,
        persistence=result.persistence,
        expected_family=OpportunityFamily.CONCENTRATION,
        expected_portfolio_id=command.evaluation.portfolio_id,
        request_fingerprint=_request_fingerprint(command),
        source_ref_is_authoritative=lambda source_ref: _source_ref_matches_command(
            source_ref,
            command=command,
        ),
    )


def _qualification_blockers(
    *,
    result: ConcentrationRiskSignalPersistenceResult,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    if source_receipt is None:
        blockers.append("authoritative_source_receipt_missing")
    if persistence_receipt is None:
        blockers.append("persistence_receipt_missing")
    if result.source_diagnostic_codes and any(
        code in {"risk_source_unavailable", "risk_source_entitlement_denied"}
        for code in result.source_diagnostic_codes
    ):
        blockers.append("risk_source_execution_blocked")
    return tuple(blockers)


def _source_ref_matches_command(
    source_ref: SourceRef,
    *,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
) -> bool:
    return bool(
        source_ref.product_id == _PRODUCT_ID
        and source_ref.source_system is SourceSystem.LOTUS_RISK
        and source_ref.as_of_date == command.evaluation.as_of_date
        and source_ref.generated_at_utc <= command.evaluation.evaluated_at_utc
        and source_ref.freshness is EvidenceFreshness.CURRENT
    )


def _request_fingerprint(command: EvaluateAndPersistConcentrationRiskFromRiskCommand) -> str:
    request = command.evaluation
    return sha256_json(
        {
            "portfolioId": request.portfolio_id,
            "asOfDate": request.as_of_date.isoformat(),
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "idempotencyKey": command.idempotency_key,
            "actorSubject": command.actor_subject,
        }
    )


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
