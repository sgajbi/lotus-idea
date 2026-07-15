from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.application.drawdown_review_signal import (
    DrawdownReviewSignalPersistenceResult,
    EvaluateAndPersistDrawdownReviewFromRiskCommand,
)
from app.application.risk_runtime_evidence import (
    RiskRuntimeExecutionBuilder,
    build_runtime_receipts,
    sha256_json,
)
from app.domain import EvidenceFreshness, OpportunityFamily, SourceRef, SourceSystem
from app.domain.proof_evidence import EvidenceClass

RISK_DRAWDOWN_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF"
RISK_DRAWDOWN_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.risk-drawdown.runtime-execution.v2"
)
RISK_DRAWDOWN_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_drawdown_source_proof_missing",
)
RISK_DRAWDOWN_REMAINING_BLOCKERS = (
    "opportunity_archetype_live_risk_volatility_source_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
    "deployment_certification_missing",
    "production_certification_missing",
)
RISK_DRAWDOWN_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/risk_drawdown_runtime_evidence/runtime_execution.py",
    "src/app/application/risk_drawdown_runtime_evidence/contract.py",
    "src/app/application/drawdown_review_signal.py",
    "src/app/application/risk_runtime_evidence/receipts.py",
    "src/app/ports/risk_sources.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "scripts/risk_drawdown_runtime_evidence/generate_runtime_execution.py",
    "make risk-drawdown-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-risk:DrawdownAnalyticsReport:v1"


def _payload(
    generated_at_utc: datetime,
    command: EvaluateAndPersistDrawdownReviewFromRiskCommand,
    status: str,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    request = command.evaluation
    return {
        "schemaVersion": RISK_DRAWDOWN_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "risk_drawdown",
        "proofType": "lotus_risk_drawdown_review_candidate_persistence",
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
            list(RISK_DRAWDOWN_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(RISK_DRAWDOWN_REMAINING_BLOCKERS),
        "evidenceRefs": list(RISK_DRAWDOWN_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "officialRiskCalculationOwned": "lotus-risk",
            "volatilityRuntimeCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
        },
    }


def _receipts(
    command: EvaluateAndPersistDrawdownReviewFromRiskCommand,
    result: DrawdownReviewSignalPersistenceResult,
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


def _source_ref_matches_command(
    source_ref: SourceRef,
    *,
    command: EvaluateAndPersistDrawdownReviewFromRiskCommand,
) -> bool:
    request = command.evaluation
    return bool(
        source_ref.product_id == _PRODUCT_ID
        and source_ref.source_system is SourceSystem.LOTUS_RISK
        and source_ref.as_of_date == request.as_of_date
        and source_ref.generated_at_utc <= request.evaluated_at_utc
        and source_ref.freshness is EvidenceFreshness.CURRENT
    )


def _request_fingerprint(command: EvaluateAndPersistDrawdownReviewFromRiskCommand) -> str:
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


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


_RUNTIME_EXECUTION_BUILDER = RiskRuntimeExecutionBuilder(
    build_receipts=_receipts,
    build_payload=_payload,
    read_diagnostics=lambda result: result.source_diagnostic_codes,
)
build_risk_drawdown_runtime_execution = _RUNTIME_EXECUTION_BUILDER.build_completed
build_blocked_risk_drawdown_runtime_execution = _RUNTIME_EXECUTION_BUILDER.build_blocked
