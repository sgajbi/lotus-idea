from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

from app.application.runtime_evidence import (
    RuntimeEvidenceScope,
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
    source_ref_receipt,
)
from app.domain import EvidenceFreshness, SourceSystem
from app.domain.proof_evidence import EvidenceClass
from app.ports.core_sources import (
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
    CorePortfolioStateSourcePort,
)

CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF"
CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.core-portfolio-state.runtime-execution.v2"
)
CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS = ("portfolio_state", "portfolio_totals")
CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_core_portfolio_state_source_ref_missing",
)
CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS = (
    "opportunity_archetype_portfolio_scoped_manage_source_proof_missing",
    "opportunity_archetype_mandate_performance_health_source_ref_missing",
    "opportunity_archetype_mandate_risk_health_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
CORE_PORTFOLIO_STATE_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/core_portfolio_state_runtime_evidence/runtime_execution.py",
    "src/app/application/core_portfolio_state_runtime_evidence/contract.py",
    "src/app/application/runtime_evidence/receipts.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "scripts/core_portfolio_state_runtime_evidence/generate_runtime_execution.py",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "make core-portfolio-state-live-proof-contract-gate",
)

_PRODUCT_ID = "lotus-core:PortfolioStateSnapshot:v1"
_PRODUCT_NAME = "PortfolioStateSnapshot"
_PRODUCT_VERSION = "v1"
_SNAPSHOT_MODE = "BASELINE"
_CONSUMER_SYSTEM = "lotus-idea"
_COMPLETE = "COMPLETE"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluateCorePortfolioStateReadiness(RuntimeEvidenceScope):
    pass


@dataclass(frozen=True)
class CorePortfolioStateReadinessResult:
    command: EvaluateCorePortfolioStateReadiness
    evidence: CorePortfolioStateEvidence


def evaluate_core_portfolio_state_readiness(
    command: EvaluateCorePortfolioStateReadiness,
    *,
    core_source: CorePortfolioStateSourcePort,
) -> CorePortfolioStateReadinessResult:
    evidence = core_source.fetch_portfolio_state_evidence(
        CorePortfolioStateEvidenceRequest(
            tenant_id=command.tenant_id,
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
    )
    return CorePortfolioStateReadinessResult(command=command, evidence=evidence)


def build_core_portfolio_state_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: CorePortfolioStateReadinessResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    command, evidence = result.command, result.evidence
    blockers = _qualification_blockers(
        command,
        evidence,
        evidence_observed_at_utc=generated_at_utc,
    )
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="completed",
        source_receipt=_source_receipt(evidence),
        diagnostic_code=evidence.portfolio_state_diagnostic or "core_portfolio_state_unknown",
        qualification_blockers=blockers,
    )


def build_blocked_core_portfolio_state_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateCorePortfolioStateReadiness,
    error_code: str,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="blocked",
        source_receipt=None,
        diagnostic_code=error_code,
        qualification_blockers=("core_portfolio_state_source_execution_blocked", error_code),
    )


def _payload(
    *,
    generated_at_utc: datetime,
    command: EvaluateCorePortfolioStateReadiness,
    status: str,
    source_receipt: dict[str, Any] | None,
    diagnostic_code: str,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    return {
        "schemaVersion": CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "core_portfolio_state",
        "proofType": "lotus_core_baseline_portfolio_state_read",
        "sourceAuthority": SourceSystem.LOTUS_CORE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
            "requestReceipt": _request_receipt(command),
            "sourceReceipt": source_receipt,
            "diagnosticCode": diagnostic_code,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS),
        "evidenceRefs": list(CORE_PORTFOLIO_STATE_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "portfolioStateOwned": "lotus-core",
            "portfolioStateMutated": False,
            "portfolioAccountingAuthorityTransferred": False,
            "reconciliationAuthorityTransferred": False,
            "rebalanceConstructed": False,
            "orderExecutionReady": False,
            "riskMethodologyCertified": False,
            "performanceMethodologyCertified": False,
            "suitabilityCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _qualification_blockers(
    command: EvaluateCorePortfolioStateReadiness,
    evidence: CorePortfolioStateEvidence,
    *,
    evidence_observed_at_utc: datetime,
) -> tuple[str, ...]:
    ref = evidence.portfolio_state_ref
    blockers: list[str] = []
    if (
        ref is None
        or ref.source_system is not SourceSystem.LOTUS_CORE
        or ref.product_id != _PRODUCT_ID
    ):
        blockers.append("core_portfolio_state_source_ref_missing")
    elif ref.as_of_date != command.as_of_date:
        blockers.append("core_portfolio_state_scope_mismatch")
    elif ref.generated_at_utc > evidence_observed_at_utc:
        blockers.append("core_portfolio_state_source_time_invalid")
    elif ref.freshness is not EvidenceFreshness.CURRENT:
        blockers.append("core_portfolio_state_evidence_not_current")
    if not evidence.entitlement_allowed:
        blockers.append("core_portfolio_state_entitlement_denied")
    if not evidence.source_evidence_available:
        blockers.append("core_portfolio_state_evidence_unavailable")
    if (
        evidence.response_product_name != _PRODUCT_NAME
        or evidence.response_product_version != _PRODUCT_VERSION
    ):
        blockers.append("core_portfolio_state_product_identity_mismatch")
    if (
        evidence.response_tenant_id != command.tenant_id
        or evidence.response_portfolio_id != command.portfolio_id
    ):
        blockers.append("core_portfolio_state_response_scope_mismatch")
    if evidence.snapshot_mode != _SNAPSHOT_MODE:
        blockers.append("core_portfolio_state_non_baseline_snapshot")
    if (
        evidence.applied_sections != CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS
        or evidence.dropped_sections
    ):
        blockers.append("core_portfolio_state_section_governance_mismatch")
    if not evidence.request_fingerprint:
        blockers.append("core_portfolio_state_request_fingerprint_missing")
    if not evidence.snapshot_id:
        blockers.append("core_portfolio_state_snapshot_identity_missing")
    if not evidence.restatement_version:
        blockers.append("core_portfolio_state_restatement_version_missing")
    if not evidence.policy_version:
        blockers.append("core_portfolio_state_policy_version_missing")
    if not _source_hashes_reconcile(evidence):
        blockers.append("core_portfolio_state_source_digest_mismatch")
    if (evidence.reconciliation_status or "").upper() != _COMPLETE:
        blockers.append("core_portfolio_state_reconciliation_incomplete")
    if ref is None or ref.data_quality_status.upper() != _COMPLETE:
        blockers.append("core_portfolio_state_data_quality_incomplete")
    if not evidence.source_evidence_current:
        blockers.append("core_portfolio_state_source_current_posture_missing")
    if (
        evidence.latest_evidence_at_utc is None
        or evidence.latest_evidence_at_utc > evidence_observed_at_utc
        or (ref is not None and evidence.latest_evidence_at_utc > ref.generated_at_utc)
    ):
        blockers.append("core_portfolio_state_latest_evidence_time_invalid")
    if (
        command.correlation_id is None
        or evidence.source_correlation_id is None
        or command.correlation_id != evidence.source_correlation_id
    ):
        blockers.append("core_portfolio_state_correlation_binding_missing")
    return tuple(dict.fromkeys(blockers))


def _request_receipt(command: EvaluateCorePortfolioStateReadiness) -> dict[str, Any]:
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "asOfDate": command.as_of_date.isoformat(),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "consumerSystem": _CONSUMER_SYSTEM,
        "snapshotMode": _SNAPSHOT_MODE,
        "requestedSections": list(CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS),
        "correlationIdHash": (
            identity_hash(command.correlation_id) if command.correlation_id is not None else None
        ),
    }
    return {**material, "requestDigest": sha256_json(material)}


def _source_receipt(evidence: CorePortfolioStateEvidence) -> dict[str, Any] | None:
    base = source_ref_receipt(evidence.portfolio_state_ref)
    if base is None:
        return None
    material = {key: value for key, value in base.items() if key != "receiptDigest"}
    material.update(
        {
            "responseProductName": evidence.response_product_name,
            "responseProductVersion": evidence.response_product_version,
            "responseTenantIdHash": (
                identity_hash(evidence.response_tenant_id)
                if evidence.response_tenant_id is not None
                else None
            ),
            "responsePortfolioIdHash": (
                identity_hash(evidence.response_portfolio_id)
                if evidence.response_portfolio_id is not None
                else None
            ),
            "snapshotMode": evidence.snapshot_mode,
            "requestFingerprint": evidence.request_fingerprint,
            "snapshotId": evidence.snapshot_id,
            "sourceBatchFingerprint": evidence.source_batch_fingerprint,
            "responseContentHash": evidence.response_content_hash,
            "responseSourceDigest": evidence.response_source_digest,
            "restatementVersion": evidence.restatement_version,
            "reconciliationStatus": evidence.reconciliation_status,
            "latestEvidenceAtUtc": (
                format_utc(evidence.latest_evidence_at_utc)
                if evidence.latest_evidence_at_utc is not None
                else None
            ),
            "sourceEvidenceCurrent": evidence.source_evidence_current,
            "policyVersion": evidence.policy_version,
            "sourceCorrelationIdHash": (
                identity_hash(evidence.source_correlation_id)
                if evidence.source_correlation_id is not None
                else None
            ),
            "appliedSections": list(evidence.applied_sections),
            "droppedSections": list(evidence.dropped_sections),
        }
    )
    return {**material, "receiptDigest": sha256_json(material)}


def _source_hashes_reconcile(evidence: CorePortfolioStateEvidence) -> bool:
    ref = evidence.portfolio_state_ref
    values = (
        ref.content_hash if ref is not None else None,
        evidence.source_batch_fingerprint,
        evidence.response_content_hash,
        evidence.response_source_digest,
    )
    return (
        all(isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) for value in values)
        and len(set(values)) == 1
    )
