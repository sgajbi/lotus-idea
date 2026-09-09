from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from app.domain.evidence_digest import is_sha256_digest
from app.application.runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    score_receipt,
    sha256_json,
    source_ref_receipt,
)
from app.application.low_income_signal import (
    DEFAULT_LOW_INCOME_POLICY,
    EvaluateAndPersistLowIncomeFromCoreCommand,
    EvaluateLowIncomeFromCoreCommand,
    LowIncomeSignalPersistenceResult,
    evaluate_and_persist_low_income_signal_from_core,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    LowIncomeSignalPolicy,
    ReviewAccessScope,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceSystem,
)
from app.domain.evidence_hashing import evidence_hash_for_source_refs
from app.domain.source_revision import source_cut_posture, source_revision_vector_digest
from app.domain.proof_evidence import EvidenceClass
from app.ports.core_sources import (
    CoreCashMovementSummaryEvidence,
    CoreCashflowProjectionEvidence,
    CoreLowIncomeEvidence,
    CoreLowIncomeSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
    CoreSourceProductRuntimeEvidence,
)
from app.ports.idea_repository import CandidateEvaluationRepository

LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF"
LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.low-income-cashflow.runtime-execution.v3"
)
LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_core_cashflow_source_proof_missing",
)
LOW_INCOME_CASHFLOW_REMAINING_BLOCKERS = (
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
LOW_INCOME_CASHFLOW_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/low_income_cashflow_runtime_evidence/runtime_execution.py",
    "src/app/application/low_income_cashflow_runtime_evidence/contract.py",
    "src/app/application/runtime_evidence/receipts.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "scripts/low_income_cashflow_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make low-income-core-cashflow-live-proof-contract-gate",
)

_MOVEMENT_PRODUCT_ID = "lotus-core:PortfolioCashMovementSummary:v1"
_MOVEMENT_PRODUCT_NAME = "PortfolioCashMovementSummary"
_MOVEMENT_ROUTE = "/portfolios/{portfolio_id}/cash-movement-summary"
_PROJECTION_PRODUCT_ID = "lotus-core:PortfolioCashflowProjection:v1"
_PROJECTION_PRODUCT_NAME = "PortfolioCashflowProjection"
_PROJECTION_ROUTE = "/portfolios/{portfolio_id}/cashflow-projection"
_PRODUCT_VERSION = "v1"
_COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class EvaluateLowIncomeCashflowReadiness:
    tenant_id: str
    book_id: str
    portfolio_id: str
    client_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    accepted_at_utc: datetime
    idempotency_key: str
    actor_subject: str
    horizon_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.tenant_id,
                self.book_id,
                self.portfolio_id,
                self.client_id,
                self.idempotency_key,
                self.actor_subject,
            )
        ):
            raise ValueError("authoritative scope, idempotency_key, and actor_subject are required")
        if self.horizon_days < 1 or self.horizon_days > 366:
            raise ValueError("horizon_days must be between 1 and 366")
        require_aware(self.evaluated_at_utc, "evaluated_at_utc")
        require_aware(self.accepted_at_utc, "accepted_at_utc")
        if self.correlation_id is not None and not self.correlation_id.strip():
            raise ValueError("correlation_id must not be blank")


@dataclass(frozen=True)
class LowIncomeCashflowReadinessResult:
    command: EvaluateLowIncomeCashflowReadiness
    evidence: CoreLowIncomeEvidence
    signal_result: LowIncomeSignalPersistenceResult
    policy: LowIncomeSignalPolicy

    @property
    def evaluation(self) -> SignalEvaluationResult:
        return self.signal_result.evaluation


def evaluate_low_income_cashflow_readiness(
    command: EvaluateLowIncomeCashflowReadiness,
    *,
    core_source: CoreLowIncomeSourcePort,
    repository: CandidateEvaluationRepository,
    policy: LowIncomeSignalPolicy = DEFAULT_LOW_INCOME_POLICY,
) -> LowIncomeCashflowReadinessResult:
    signal_result = evaluate_and_persist_low_income_signal_from_core(
        EvaluateAndPersistLowIncomeFromCoreCommand(
            evaluation=EvaluateLowIncomeFromCoreCommand(
                tenant_id=command.tenant_id,
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                horizon_days=command.horizon_days,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            ),
            access_scope=ReviewAccessScope(
                tenant_id=command.tenant_id,
                book_id=command.book_id,
                portfolio_id=command.portfolio_id,
                client_id=command.client_id,
            ),
            idempotency_key=command.idempotency_key,
            actor_subject=command.actor_subject,
            accepted_at_utc=command.accepted_at_utc,
        ),
        core_source=core_source,
        repository=repository,
        policy=policy,
    )
    if signal_result.source_evidence is None:
        diagnostic = next(iter(signal_result.source_diagnostic_codes), "")
        if diagnostic == "core_source_entitlement_denied":
            raise CoreSourceEntitlementDenied
        raise CoreSourceUnavailable(code=diagnostic or "core_cashflow_source_unavailable")
    return LowIncomeCashflowReadinessResult(
        command=command,
        evidence=signal_result.source_evidence,
        signal_result=signal_result,
        policy=policy,
    )


def build_low_income_cashflow_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: LowIncomeCashflowReadinessResult,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    blockers = _qualification_blockers(result)
    persistence_receipt = _persistence_receipt(result)
    if result.signal_result.evaluation.candidate is None:
        blockers = (
            *blockers,
            f"candidate_evaluation_{result.signal_result.evaluation.outcome.value}",
        )
    if not durable_storage_backed:
        blockers = (*blockers, "durable_repository_not_configured")
    if persistence_receipt is None:
        blockers = (*blockers, "persistence_receipt_missing")
    return _payload(
        generated_at_utc=generated_at_utc,
        command=result.command,
        status="completed",
        movement_receipt=_movement_receipt(result.evidence),
        projection_receipt=_projection_receipt(result.evidence),
        evaluation_receipt=_evaluation_receipt(result),
        persistence_receipt=persistence_receipt,
        durable_storage_backed=durable_storage_backed,
        qualification_blockers=blockers,
    )


def build_blocked_low_income_cashflow_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateLowIncomeCashflowReadiness,
    error_code: str,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="blocked",
        movement_receipt=None,
        projection_receipt=None,
        evaluation_receipt=None,
        persistence_receipt=None,
        durable_storage_backed=durable_storage_backed,
        qualification_blockers=(
            "core_cashflow_source_execution_blocked",
            error_code,
            *(("durable_repository_not_configured",) if not durable_storage_backed else ()),
            "persistence_receipt_missing",
        ),
    )


def _payload(
    *,
    generated_at_utc: datetime,
    command: EvaluateLowIncomeCashflowReadiness,
    status: str,
    movement_receipt: dict[str, Any] | None,
    projection_receipt: dict[str, Any] | None,
    evaluation_receipt: dict[str, Any] | None,
    persistence_receipt: dict[str, Any] | None,
    durable_storage_backed: bool,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    return {
        "schemaVersion": LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "low_income_cashflow",
        "proofType": "lotus_core_cashflow_candidate_persistence",
        "sourceAuthority": SourceSystem.LOTUS_CORE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "durableStorageBacked": durable_storage_backed,
            "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
            "requestReceipt": _request_receipt(command),
            "cashMovementReceipt": movement_receipt,
            "cashflowProjectionReceipt": projection_receipt,
            "evaluationReceipt": evaluation_receipt,
            "persistenceReceipt": persistence_receipt,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(LOW_INCOME_CASHFLOW_REMAINING_BLOCKERS),
        "evidenceRefs": list(LOW_INCOME_CASHFLOW_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "cashflowFactsOwned": "lotus-core",
            "opportunityDetectionOwned": "lotus-idea",
            "clientIncomeNeedInferred": False,
            "incomePlanProduced": False,
            "fundingAdviceProduced": False,
            "liquidityAdviceProduced": False,
            "treasuryInstructionProduced": False,
            "suitabilityCertified": False,
            "complianceApproved": False,
            "executionReady": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": True,
        },
    }


def _qualification_blockers(result: LowIncomeCashflowReadinessResult) -> tuple[str, ...]:
    command = result.command
    evidence = result.evidence
    blockers: list[str] = []
    _validate_source_ref(
        blockers,
        evidence.cash_movement_ref,
        product_id=_MOVEMENT_PRODUCT_ID,
        as_of_date=command.as_of_date,
        prefix="core_cash_movement",
    )
    _validate_source_ref(
        blockers,
        evidence.cashflow_projection_ref,
        product_id=_PROJECTION_PRODUCT_ID,
        as_of_date=command.as_of_date,
        prefix="core_cashflow_projection",
    )
    movement = evidence.cash_movement_product
    projection = evidence.cashflow_projection_product
    if movement is None:
        blockers.append("core_cash_movement_receipt_missing")
    else:
        blockers.extend(_movement_blockers(command, movement, evidence.cash_movement_ref))
    if projection is None:
        blockers.append("core_cashflow_projection_receipt_missing")
    else:
        blockers.extend(_projection_blockers(command, projection, evidence.cashflow_projection_ref))
    if not evidence.entitlement_allowed:
        blockers.append("core_cashflow_entitlement_denied")
    if evidence.cashflow_diagnostic != "core_cashflow_liquidity_evidence_ready":
        blockers.append("core_cashflow_diagnostic_not_ready")
    expected_min = _minimum_cumulative(projection)
    if evidence.source_reported_min_projected_cumulative_cashflow != expected_min:
        blockers.append("core_cashflow_minimum_mismatch")
    if evidence.cash_movement_count != (movement.cashflow_count if movement else None):
        blockers.append("core_cash_movement_count_mismatch")
    blockers.extend(_evaluation_blockers(result, expected_min))
    return tuple(dict.fromkeys(blockers))


def _validate_source_ref(
    blockers: list[str],
    ref: Any,
    *,
    product_id: str,
    as_of_date: date,
    prefix: str,
) -> None:
    if (
        ref is None
        or ref.source_system is not SourceSystem.LOTUS_CORE
        or ref.product_id != product_id
    ):
        blockers.append(f"{prefix}_source_ref_missing")
    elif ref.as_of_date != as_of_date:
        blockers.append(f"{prefix}_scope_mismatch")
    elif ref.freshness is not EvidenceFreshness.CURRENT:
        blockers.append(f"{prefix}_evidence_not_current")


def _movement_blockers(
    command: EvaluateLowIncomeCashflowReadiness,
    product: CoreCashMovementSummaryEvidence,
    ref: Any,
) -> tuple[str, ...]:
    blockers = _runtime_metadata_blockers(
        command, product.runtime, ref, _MOVEMENT_PRODUCT_NAME, "core_cash_movement"
    )
    if product.start_date != command.as_of_date or product.end_date != command.as_of_date:
        blockers.append("core_cash_movement_window_mismatch")
    counts = [bucket.cashflow_count for bucket in product.buckets]
    valid_counts = [value for value in counts if isinstance(value, int) and value >= 0]
    if (
        not isinstance(product.cashflow_count, int)
        or product.cashflow_count < 0
        or len(valid_counts) != len(counts)
        or sum(valid_counts) != product.cashflow_count
    ):
        blockers.append("core_cash_movement_counts_invalid")
    keys: set[tuple[object, ...]] = set()
    for bucket in product.buckets:
        key = (
            bucket.classification,
            bucket.timing,
            bucket.currency,
            bucket.is_position_flow,
            bucket.is_portfolio_flow,
        )
        if key in keys or not all(isinstance(value, str) and value for value in key[:3]):
            blockers.append("core_cash_movement_buckets_invalid")
            break
        keys.add(key)
        if not _movement_direction_reconciles(bucket.total_amount, bucket.movement_direction):
            blockers.append("core_cash_movement_direction_mismatch")
            break
    return tuple(blockers)


def _projection_blockers(
    command: EvaluateLowIncomeCashflowReadiness,
    product: CoreCashflowProjectionEvidence,
    ref: Any,
) -> tuple[str, ...]:
    blockers = _runtime_metadata_blockers(
        command, product.runtime, ref, _PROJECTION_PRODUCT_NAME, "core_cashflow_projection"
    )
    expected_end = command.as_of_date + timedelta(days=command.horizon_days)
    if (
        product.range_start_date != command.as_of_date
        or product.range_end_date != expected_end
        or product.include_projected is not True
        or product.projection_days != command.horizon_days
        or not isinstance(product.portfolio_currency, str)
        or not product.portfolio_currency.strip()
    ):
        blockers.append("core_cashflow_projection_scope_mismatch")
    if not _projection_series_reconciles(command, product):
        blockers.append("core_cashflow_projection_series_invalid")
    return tuple(blockers)


def _runtime_metadata_blockers(
    command: EvaluateLowIncomeCashflowReadiness,
    runtime: CoreSourceProductRuntimeEvidence,
    ref: Any,
    product_name: str,
    prefix: str,
) -> list[str]:
    blockers: list[str] = []
    if (
        runtime.product_name != product_name
        or runtime.product_version != _PRODUCT_VERSION
        or runtime.tenant_id != command.tenant_id
        or runtime.portfolio_id != command.portfolio_id
        or runtime.as_of_date != command.as_of_date
    ):
        blockers.append(f"{prefix}_response_scope_mismatch")
    if (
        runtime.generated_at_utc is None
        or runtime.generated_at_utc > command.evaluated_at_utc
        or runtime.latest_evidence_at_utc is None
        or runtime.latest_evidence_at_utc > runtime.generated_at_utc
    ):
        blockers.append(f"{prefix}_evidence_time_invalid")
    hashes = (
        getattr(ref, "content_hash", None),
        runtime.source_batch_fingerprint,
        runtime.content_hash,
        runtime.source_digest,
    )
    if not all(_is_sha256(value) for value in hashes) or len(set(hashes)) != 1:
        blockers.append(f"{prefix}_source_digest_mismatch")
    if (
        (runtime.reconciliation_status or "").upper() != _COMPLETE
        or (runtime.data_quality_status or "").upper() != _COMPLETE
        or runtime.degradation_status != "NONE"
        or runtime.degradation_reason_codes
        or runtime.degradation_detail_count != 0
        or not runtime.source_evidence_current
        or (runtime.freshness_status or "").upper() != "CURRENT"
    ):
        blockers.append(f"{prefix}_supportability_incomplete")
    if not runtime.restatement_version or not runtime.policy_version or not runtime.snapshot_id:
        blockers.append(f"{prefix}_governance_identity_missing")
    if (
        command.correlation_id is None
        or runtime.correlation_id is None
        or command.correlation_id != runtime.correlation_id
    ):
        blockers.append(f"{prefix}_correlation_binding_missing")
    return blockers


def _projection_series_reconciles(
    command: EvaluateLowIncomeCashflowReadiness,
    product: CoreCashflowProjectionEvidence,
) -> bool:
    if len(product.points) != command.horizon_days + 1:
        return False
    running = Decimal("0")
    booked_total = Decimal("0")
    projected_total = Decimal("0")
    for index, point in enumerate(product.points):
        values = (
            point.booked_net_cashflow,
            point.projected_settlement_cashflow,
            point.net_cashflow,
            point.projected_cumulative_cashflow,
        )
        if point.projection_date != command.as_of_date + timedelta(days=index) or any(
            not isinstance(value, Decimal) for value in values
        ):
            return False
        booked, projected, net, cumulative = cast(tuple[Decimal, Decimal, Decimal, Decimal], values)
        if booked + projected != net:
            return False
        running += net
        booked_total += booked
        projected_total += projected
        if cumulative != running:
            return False
    return (
        product.booked_total_net_cashflow == booked_total
        and product.projected_settlement_total_cashflow == projected_total
        and product.total_net_cashflow == running
    )


def _minimum_cumulative(product: CoreCashflowProjectionEvidence | None) -> Decimal | None:
    if product is None or not product.points:
        return None
    values = [point.projected_cumulative_cashflow for point in product.points]
    if any(not isinstance(value, Decimal) for value in values):
        return None
    return min(value for value in values if isinstance(value, Decimal))


def _evaluation_blockers(
    result: LowIncomeCashflowReadinessResult,
    minimum: Decimal | None,
) -> tuple[str, ...]:
    evaluation = result.signal_result.evaluation
    if evaluation.family.value != "low_income" or minimum is None:
        return ("low_income_evaluation_invalid",)
    should_create = minimum <= result.policy.projected_cumulative_cashflow_threshold
    if should_create:
        if evaluation.outcome is not SignalEvaluationOutcome.CANDIDATE_CREATED:
            return ("low_income_candidate_outcome_mismatch",)
        if evaluation.candidate is None or evaluation.signal is None:
            return ("low_income_candidate_identity_missing",)
    elif (
        evaluation.outcome is not SignalEvaluationOutcome.NOT_ELIGIBLE
        or evaluation.candidate is not None
        or evaluation.signal is not None
    ):
        return ("low_income_no_opportunity_outcome_mismatch",)
    return ()


def _request_receipt(command: EvaluateLowIncomeCashflowReadiness) -> dict[str, Any]:
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "bookIdHash": identity_hash(command.book_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "clientIdHash": identity_hash(command.client_id),
        "asOfDate": command.as_of_date.isoformat(),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "acceptedAtUtc": format_utc(command.accepted_at_utc),
        "idempotencyKeyHash": identity_hash(command.idempotency_key),
        "actorSubjectHash": identity_hash(command.actor_subject),
        "consumerSystem": "lotus-idea",
        "horizonDays": command.horizon_days,
        "includeProjected": True,
        "correlationIdHash": (
            identity_hash(command.correlation_id) if command.correlation_id is not None else None
        ),
    }
    return {**material, "requestDigest": sha256_json(material)}


def _movement_receipt(evidence: CoreLowIncomeEvidence) -> dict[str, Any] | None:
    product = evidence.cash_movement_product
    base = source_ref_receipt(evidence.cash_movement_ref)
    if product is None or base is None:
        return None
    material = {key: value for key, value in base.items() if key != "receiptDigest"}
    material.update(
        {
            **_runtime_receipt(product.runtime),
            "startDate": _date_text(product.start_date),
            "endDate": _date_text(product.end_date),
            "cashflowCount": product.cashflow_count,
            "bucketDigest": sha256_json([_bucket_material(bucket) for bucket in product.buckets]),
        }
    )
    return {**material, "receiptDigest": sha256_json(material)}


def _projection_receipt(evidence: CoreLowIncomeEvidence) -> dict[str, Any] | None:
    product = evidence.cashflow_projection_product
    base = source_ref_receipt(evidence.cashflow_projection_ref)
    if product is None or base is None:
        return None
    material = {key: value for key, value in base.items() if key != "receiptDigest"}
    material.update(
        {
            **_runtime_receipt(product.runtime),
            "rangeStartDate": _date_text(product.range_start_date),
            "rangeEndDate": _date_text(product.range_end_date),
            "includeProjected": product.include_projected,
            "portfolioCurrency": product.portfolio_currency,
            "projectionDays": product.projection_days,
            "pointCount": len(product.points),
            "minimumProjectedCumulativeCashflow": _decimal_text(
                evidence.source_reported_min_projected_cumulative_cashflow
            ),
            "bookedTotalNetCashflow": _decimal_text(product.booked_total_net_cashflow),
            "projectedSettlementTotalCashflow": _decimal_text(
                product.projected_settlement_total_cashflow
            ),
            "totalNetCashflow": _decimal_text(product.total_net_cashflow),
            "pointDigest": sha256_json([_point_material(point) for point in product.points]),
        }
    )
    return {**material, "receiptDigest": sha256_json(material)}


def _runtime_receipt(runtime: CoreSourceProductRuntimeEvidence) -> dict[str, Any]:
    return {
        "responseProductName": runtime.product_name,
        "responseProductVersion": runtime.product_version,
        "responseTenantIdHash": identity_hash(runtime.tenant_id) if runtime.tenant_id else None,
        "responsePortfolioIdHash": (
            identity_hash(runtime.portfolio_id) if runtime.portfolio_id else None
        ),
        "responseGeneratedAtUtc": (
            format_utc(runtime.generated_at_utc) if runtime.generated_at_utc else None
        ),
        "restatementVersion": runtime.restatement_version,
        "reconciliationStatus": runtime.reconciliation_status,
        "latestEvidenceAtUtc": (
            format_utc(runtime.latest_evidence_at_utc) if runtime.latest_evidence_at_utc else None
        ),
        "sourceBatchFingerprint": runtime.source_batch_fingerprint,
        "snapshotId": runtime.snapshot_id,
        "responseContentHash": runtime.content_hash,
        "responseSourceDigest": runtime.source_digest,
        "sourceRefsDigest": sha256_json(runtime.source_refs),
        "sourceLineageDigest": sha256_json(runtime.source_lineage),
        "degradationStatus": runtime.degradation_status,
        "degradationReasonCodes": list(runtime.degradation_reason_codes),
        "degradationDetailCount": runtime.degradation_detail_count,
        "sourceEvidenceCurrent": runtime.source_evidence_current,
        "freshnessStatus": runtime.freshness_status,
        "policyVersion": runtime.policy_version,
        "sourceCorrelationIdHash": (
            identity_hash(runtime.correlation_id) if runtime.correlation_id else None
        ),
    }


def _evaluation_receipt(result: LowIncomeCashflowReadinessResult) -> dict[str, Any]:
    evaluation = result.signal_result.evaluation
    candidate = evaluation.candidate
    material = {
        "family": evaluation.family.value,
        "outcome": evaluation.outcome.value,
        "reasonCodes": [code.value for code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "policyVersion": result.policy.policy_version,
        "projectedCumulativeCashflowThreshold": str(
            result.policy.projected_cumulative_cashflow_threshold
        ),
        **score_receipt(candidate.score if candidate is not None else None),
        "candidateIdHash": (
            identity_hash(evaluation.candidate.candidate_id) if evaluation.candidate else None
        ),
        "signalIdHash": identity_hash(evaluation.signal.signal_id) if evaluation.signal else None,
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _persistence_receipt(result: LowIncomeCashflowReadinessResult) -> dict[str, Any] | None:
    evaluation = result.signal_result.evaluation
    persistence = result.signal_result.persistence
    candidate = evaluation.candidate
    if (
        candidate is None
        or persistence is None
        or persistence.record is None
        or persistence.decision
        not in {CandidatePersistenceDecision.ACCEPTED, CandidatePersistenceDecision.REPLAYED}
        or persistence.record.candidate != candidate
    ):
        return None
    source_refs = candidate.evidence_packet.source_refs
    if (
        len(source_refs) != 2
        or persistence.record.evidence_hash != evidence_hash_for_source_refs(source_refs)
        or candidate.access_scope is None
        or not candidate.access_scope.is_authoritative
    ):
        return None
    movement = _movement_receipt(result.evidence)
    projection = _projection_receipt(result.evidence)
    if movement is None or projection is None:
        return None
    source_receipts_digest = sha256_json(
        {
            "cashMovementReceiptDigest": movement["receiptDigest"],
            "cashflowProjectionReceiptDigest": projection["receiptDigest"],
        }
    )
    material = {
        "decision": persistence.decision.value,
        "candidateFamily": candidate.family.value,
        "candidateLifecycleStatus": candidate.lifecycle_status.value,
        "sourceReceiptsDigest": source_receipts_digest,
        "sourceEvidenceHash": persistence.record.evidence_hash,
        "sourceRevisionVectorDigest": source_revision_vector_digest(source_refs),
        "sourceCutPosture": source_cut_posture(source_refs).value,
        "scopeFingerprint": sha256_json(
            {
                "tenantId": candidate.access_scope.tenant_id,
                "bookId": candidate.access_scope.book_id,
                "portfolioId": candidate.access_scope.portfolio_id,
                "clientId": candidate.access_scope.client_id,
                "requestDigest": _request_receipt(result.command)["requestDigest"],
            }
        ),
        "persistedAtUtc": format_utc(persistence.record.persisted_at_utc),
    }
    return {**material, "receiptDigest": sha256_json(material)}


def _bucket_material(bucket: Any) -> dict[str, Any]:
    return {
        "classification": bucket.classification,
        "timing": bucket.timing,
        "currency": bucket.currency,
        "isPositionFlow": bucket.is_position_flow,
        "isPortfolioFlow": bucket.is_portfolio_flow,
        "cashflowCount": bucket.cashflow_count,
        "totalAmount": _decimal_text(bucket.total_amount),
        "movementDirection": bucket.movement_direction,
    }


def _point_material(point: Any) -> dict[str, Any]:
    return {
        "projectionDate": _date_text(point.projection_date),
        "bookedNetCashflow": _decimal_text(point.booked_net_cashflow),
        "projectedSettlementCashflow": _decimal_text(point.projected_settlement_cashflow),
        "netCashflow": _decimal_text(point.net_cashflow),
        "projectedCumulativeCashflow": _decimal_text(point.projected_cumulative_cashflow),
    }


def _movement_direction_reconciles(amount: Decimal | None, direction: str | None) -> bool:
    if not isinstance(amount, Decimal):
        return False
    expected = "INFLOW" if amount > 0 else "OUTFLOW" if amount < 0 else "FLAT"
    return direction == expected


def _is_sha256(value: object) -> bool:
    return is_sha256_digest(value)


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
