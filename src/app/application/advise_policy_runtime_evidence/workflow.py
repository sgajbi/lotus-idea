from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any
from urllib.parse import quote

from app.application.runtime_evidence import format_utc, identity_hash, sha256_json
from app.domain import SourceSystem
from app.domain.proof_evidence import parse_timezone_aware_datetime
from app.ports.advise_sources import (
    ADVISE_POLICY_EVALUATION_PRODUCT_ID,
    ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationRuntimeEvidence,
)

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class AdvisePolicyWorkflowScope:
    tenant_id: str
    portfolio_id: str
    evaluation_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str
    trace_id: str


def build_advise_policy_workflow_receipt(
    runtime: AdvisePolicyEvaluationRuntimeEvidence | None,
    *,
    evidence: AdvisePolicyEvaluationEvidence | None,
) -> dict[str, Any] | None:
    if runtime is None:
        return None
    material = {
        "productId": runtime.product_id,
        "sourceSystem": SourceSystem.LOTUS_ADVISE.value,
        "productVersion": runtime.product_version,
        "routeTemplate": ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE,
        "evaluationIdHash": identity_hash(runtime.evaluation_id) if runtime.evaluation_id else None,
        "tenantScopeHash": runtime.tenant_scope_hash,
        "portfolioIdHash": identity_hash(runtime.portfolio_id) if runtime.portfolio_id else None,
        "sourceCorrelationIdHash": (
            identity_hash(runtime.correlation_id) if runtime.correlation_id else None
        ),
        "sourceTraceIdHash": identity_hash(runtime.trace_id) if runtime.trace_id else None,
        "asOfDate": runtime.as_of_date.isoformat() if runtime.as_of_date else None,
        "generatedAtUtc": (
            format_utc(runtime.generated_at_utc) if runtime.generated_at_utc else None
        ),
        "contentHash": runtime.content_hash,
        "sourceEvidenceHash": runtime.source_evidence_hash,
        "policyContentHash": runtime.policy_content_hash,
        "policyPackId": runtime.policy_pack_id,
        "policyVersion": runtime.policy_version,
        "evaluationStatus": runtime.evaluation_status,
        "openRequirementCount": runtime.open_requirement_count,
        "blockedRequirementCount": runtime.blocked_requirement_count,
        "signOffStatus": runtime.sign_off_status,
        "signOffBlockerCount": runtime.sign_off_blocker_count,
        "clientReadyPublication": runtime.client_ready_publication,
        "dataQualityStatus": runtime.data_quality_status,
        "freshness": runtime.freshness,
        "adviseDiagnostic": evidence.advise_diagnostic if evidence is not None else None,
    }
    return {**material, "receiptDigest": sha256_json(material)}


def advise_policy_workflow_qualification_blockers(
    *,
    scope: AdvisePolicyWorkflowScope,
    evidence: AdvisePolicyEvaluationEvidence | None,
    source_error_code: str | None,
) -> tuple[str, ...]:
    if evidence is None:
        return (source_error_code or "advise_source_evidence_missing",)
    runtime = evidence.workflow_runtime
    if runtime is None:
        return ("advise_workflow_runtime_receipt_missing",)

    blockers: list[str] = []
    required = {
        "advise_evaluation_identity_missing": runtime.evaluation_id,
        "advise_tenant_scope_missing": runtime.tenant_scope_hash,
        "advise_portfolio_scope_missing": runtime.portfolio_id,
        "advise_source_correlation_missing": runtime.correlation_id,
        "advise_source_trace_missing": runtime.trace_id,
        "advise_as_of_date_missing": runtime.as_of_date,
        "advise_generated_at_missing": runtime.generated_at_utc,
        "advise_evaluation_hash_missing": runtime.content_hash,
        "advise_source_evidence_hash_missing": runtime.source_evidence_hash,
        "advise_policy_content_hash_missing": runtime.policy_content_hash,
        "advise_policy_pack_identity_missing": runtime.policy_pack_id,
        "advise_policy_version_missing": runtime.policy_version,
        "advise_evaluation_status_missing": runtime.evaluation_status,
        "advise_sign_off_status_missing": runtime.sign_off_status,
        "advise_client_publication_posture_missing": runtime.client_ready_publication,
    }
    blockers.extend(code for code, value in required.items() if value is None)
    if runtime.evaluation_id and runtime.evaluation_id != scope.evaluation_id:
        blockers.append("advise_evaluation_scope_mismatch")
    if runtime.tenant_scope_hash and runtime.tenant_scope_hash != identity_hash(scope.tenant_id):
        blockers.append("advise_tenant_scope_mismatch")
    if runtime.portfolio_id and runtime.portfolio_id != scope.portfolio_id:
        blockers.append("advise_portfolio_scope_mismatch")
    if runtime.correlation_id and runtime.correlation_id != scope.correlation_id:
        blockers.append("advise_source_correlation_mismatch")
    if runtime.trace_id and runtime.trace_id != scope.trace_id:
        blockers.append("advise_source_trace_mismatch")
    if runtime.as_of_date and runtime.as_of_date != scope.as_of_date:
        blockers.append("advise_as_of_date_mismatch")
    if runtime.generated_at_utc and runtime.generated_at_utc > scope.evaluated_at_utc:
        blockers.append("advise_evidence_from_future")
    if runtime.product_id != ADVISE_POLICY_EVALUATION_PRODUCT_ID:
        blockers.append("advise_source_product_mismatch")
    if runtime.product_version != "v1":
        blockers.append("advise_source_product_version_mismatch")
    expected_route = ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE.format(
        evaluation_id=quote(scope.evaluation_id, safe="")
    )
    if runtime.route != expected_route:
        blockers.append("advise_source_route_mismatch")
    if evidence.policy_ref is None:
        blockers.append("advise_policy_source_ref_missing")
    elif not _source_ref_matches_runtime(evidence, runtime):
        blockers.append("advise_policy_source_ref_mismatch")
    if runtime.freshness != "current":
        blockers.append("advise_source_evidence_not_current")
    if runtime.data_quality_status.lower() not in {"ready", "complete", "quality_passed"}:
        blockers.append("advise_source_quality_not_ready")
    if any(
        not _is_sha256(value)
        for value in (
            runtime.content_hash,
            runtime.source_evidence_hash,
            runtime.policy_content_hash,
        )
    ):
        blockers.append("advise_workflow_hash_invalid")
    counts: tuple[object, ...] = (
        runtime.open_requirement_count,
        runtime.blocked_requirement_count,
        runtime.sign_off_blocker_count,
    )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        blockers.append("advise_workflow_counts_invalid")
    elif not _workflow_posture_matches_evidence(evidence, runtime):
        blockers.append("advise_workflow_posture_mismatch")
    return tuple(dict.fromkeys(blockers))


def reconcile_advise_policy_workflow_receipts(
    request: Mapping[str, Any],
    workflow: Mapping[str, Any],
    *,
    evaluated_at_utc: datetime,
) -> bool:
    source_generated = parse_timezone_aware_datetime(workflow.get("generatedAtUtc"))
    expected_evaluated = format_utc(evaluated_at_utc)
    if (
        request.get("consumerSystem") != "lotus-idea"
        or request.get("evaluatedAtUtc") != expected_evaluated
        or request.get("evaluationIdHash") != workflow.get("evaluationIdHash")
        or request.get("tenantIdHash") != workflow.get("tenantScopeHash")
        or request.get("portfolioIdHash") != workflow.get("portfolioIdHash")
        or request.get("correlationIdHash") != workflow.get("sourceCorrelationIdHash")
        or request.get("traceIdHash") != workflow.get("sourceTraceIdHash")
        or request.get("asOfDate") != workflow.get("asOfDate")
        or source_generated is None
        or source_generated > evaluated_at_utc
        or workflow.get("productId") != ADVISE_POLICY_EVALUATION_PRODUCT_ID
        or workflow.get("sourceSystem") != SourceSystem.LOTUS_ADVISE.value
        or workflow.get("productVersion") != "v1"
        or workflow.get("routeTemplate") != ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE
        or workflow.get("freshness") != "current"
        or str(workflow.get("dataQualityStatus", "")).lower()
        not in {"ready", "complete", "quality_passed"}
    ):
        return False
    counts = (
        workflow.get("openRequirementCount"),
        workflow.get("blockedRequirementCount"),
        workflow.get("signOffBlockerCount"),
    )
    return not any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts
    )


def _source_ref_matches_runtime(
    evidence: AdvisePolicyEvaluationEvidence,
    runtime: AdvisePolicyEvaluationRuntimeEvidence,
) -> bool:
    ref = evidence.policy_ref
    assert ref is not None
    return (
        ref.product_id == runtime.product_id
        and ref.route == runtime.route
        and ref.as_of_date == runtime.as_of_date
        and ref.generated_at_utc == runtime.generated_at_utc
        and ref.content_hash == runtime.content_hash
        and ref.freshness.value == runtime.freshness
        and ref.data_quality_status == runtime.data_quality_status
    )


def _workflow_posture_matches_evidence(
    evidence: AdvisePolicyEvaluationEvidence,
    runtime: AdvisePolicyEvaluationRuntimeEvidence,
) -> bool:
    return (
        evidence.open_requirement_count == runtime.open_requirement_count
        and evidence.blocked_requirement_count == runtime.blocked_requirement_count
        and evidence.sign_off_blocker_count == runtime.sign_off_blocker_count
        and evidence.evaluation_status == runtime.evaluation_status
        and evidence.sign_off_status == runtime.sign_off_status
        and evidence.client_ready_publication == runtime.client_ready_publication
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
