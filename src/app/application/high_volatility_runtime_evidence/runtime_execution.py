from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.application.high_volatility_signal import (
    EvaluateAndPersistHighVolatilityFromRiskCommand,
    HighVolatilitySignalPersistenceResult,
)
from app.application.risk_runtime_evidence import build_runtime_receipts, sha256_json
from app.domain import EvidenceFreshness, OpportunityFamily, SourceRef, SourceSystem
from app.domain.proof_evidence import EvidenceClass

HIGH_VOLATILITY_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF"
HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.high-volatility.runtime-execution.v2"
)
HIGH_VOLATILITY_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_risk_volatility_source_proof_missing",
)
HIGH_VOLATILITY_REMAINING_BLOCKERS = (
    "opportunity_archetype_drawdown_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
    "deployment_certification_missing",
    "production_certification_missing",
)
HIGH_VOLATILITY_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/high_volatility_runtime_evidence/runtime_execution.py",
    "src/app/application/high_volatility_runtime_evidence/contract.py",
    "src/app/application/high_volatility_signal.py",
    "src/app/application/risk_runtime_evidence/receipts.py",
    "src/app/ports/risk_sources.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "scripts/high_volatility_runtime_evidence/generate_runtime_execution.py",
    "make high-volatility-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-risk:RiskMetricsReport:v1"


def build_high_volatility_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistHighVolatilityFromRiskCommand,
    result: HighVolatilitySignalPersistenceResult,
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


def build_blocked_high_volatility_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistHighVolatilityFromRiskCommand,
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
    command: EvaluateAndPersistHighVolatilityFromRiskCommand,
    status: str,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    request = command.evaluation
    return {
        "schemaVersion": HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "high_volatility",
        "proofType": "lotus_risk_high_volatility_candidate_persistence",
        "sourceAuthority": SourceSystem.LOTUS_RISK.value,
        "generatedAtUtc": _format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "durableStorageBacked": durable_storage_backed,
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "asOfDate": request.as_of_date.isoformat(),
            "periodName": request.period_name,
            "requestFingerprint": _request_fingerprint(command),
            "sourceReceipt": source_receipt,
            "persistenceReceipt": persistence_receipt,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(HIGH_VOLATILITY_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(HIGH_VOLATILITY_REMAINING_BLOCKERS),
        "evidenceRefs": list(HIGH_VOLATILITY_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "officialRiskCalculationOwned": "lotus-risk",
            "drawdownRuntimeCertified": False,
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
    command: EvaluateAndPersistHighVolatilityFromRiskCommand,
    result: HighVolatilitySignalPersistenceResult,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    return build_runtime_receipts(
        candidate=result.evaluation.candidate,
        persistence=result.persistence,
        expected_family=OpportunityFamily.HIGH_VOLATILITY,
        expected_portfolio_id=command.evaluation.portfolio_id,
        request_fingerprint=_request_fingerprint(command),
        source_ref_is_authoritative=lambda source_ref: _source_ref_matches_command(
            source_ref,
            command=command,
        ),
    )


def _qualification_blockers(
    *,
    result: HighVolatilitySignalPersistenceResult,
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
    command: EvaluateAndPersistHighVolatilityFromRiskCommand,
) -> bool:
    request = command.evaluation
    return bool(
        source_ref.product_id == _PRODUCT_ID
        and source_ref.source_system is SourceSystem.LOTUS_RISK
        and source_ref.as_of_date == request.as_of_date
        and source_ref.generated_at_utc <= request.evaluated_at_utc
        and source_ref.freshness is EvidenceFreshness.CURRENT
    )


def _request_fingerprint(command: EvaluateAndPersistHighVolatilityFromRiskCommand) -> str:
    request = command.evaluation
    return sha256_json(
        {
            "portfolioId": request.portfolio_id,
            "asOfDate": request.as_of_date.isoformat(),
            "periodName": request.period_name,
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
