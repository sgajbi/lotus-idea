from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.application.high_volatility_signal import (
    EvaluateAndPersistHighVolatilityFromRiskCommand,
    HighVolatilitySignalPersistenceResult,
)
from app.application.risk_runtime_evidence import (
    SourceRuntimeExecutionBuilder,
    build_risk_runtime_command_fingerprint,
    build_runtime_receipts,
    source_ref_matches_risk_request,
)
from app.domain import OpportunityFamily, SourceSystem
from app.domain.proof_evidence import EvidenceClass

HIGH_VOLATILITY_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF"
HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION = "lotus-idea.high-volatility.runtime-execution.v2"
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
    "src/app/application/source_runtime_evidence/contract.py",
    "src/app/application/risk_runtime_evidence/request_identity.py",
    "src/app/application/source_runtime_evidence/receipts.py",
    "src/app/ports/risk_sources.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "scripts/high_volatility_runtime_evidence/generate_runtime_execution.py",
    "make high-volatility-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-risk:RiskMetricsReport:v1"


def _payload(
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
            "requestFingerprint": build_risk_runtime_command_fingerprint(command),
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


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


_RUNTIME_EXECUTION_BUILDER: SourceRuntimeExecutionBuilder[
    EvaluateAndPersistHighVolatilityFromRiskCommand,
    HighVolatilitySignalPersistenceResult,
] = SourceRuntimeExecutionBuilder(
    build_receipts=lambda command, result: build_runtime_receipts(
        candidate=result.evaluation.candidate,
        persistence=result.persistence,
        expected_family=OpportunityFamily.HIGH_VOLATILITY,
        expected_portfolio_id=command.evaluation.portfolio_id,
        request_fingerprint=build_risk_runtime_command_fingerprint(command),
        source_ref_is_authoritative=lambda source_ref: source_ref_matches_risk_request(
            source_ref,
            product_id=_PRODUCT_ID,
            as_of_date=command.evaluation.as_of_date,
            evaluated_at_utc=command.evaluation.evaluated_at_utc,
        ),
    ),
    build_payload=_payload,
    read_diagnostics=lambda result: result.source_diagnostic_codes,
    blocking_diagnostic_codes=frozenset(
        {"risk_source_unavailable", "risk_source_entitlement_denied"}
    ),
    source_execution_blocker="risk_source_execution_blocked",
    default_source_error="risk_source_unavailable",
)
build_high_volatility_runtime_execution = _RUNTIME_EXECUTION_BUILDER.build_completed
build_blocked_high_volatility_runtime_execution = _RUNTIME_EXECUTION_BUILDER.build_blocked
