from __future__ import annotations

from datetime import timedelta
from typing import Callable

from app.application.runtime_evidence import identity_hash
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.advise_sources import (
    ADVISE_POLICY_EVALUATION_PRODUCT_ID,
    ADVISE_POLICY_EVALUATION_PRODUCT_VERSION,
    ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdvisePolicyEvaluationRuntimeEvidence,
)

EVALUATION_HASH = "sha256:" + "a" * 64
SOURCE_EVIDENCE_HASH = "sha256:" + "b" * 64
POLICY_CONTENT_HASH = "sha256:" + "c" * 64


class AuthoritativeAdvisePolicyEvaluationSource:
    def __init__(
        self,
        *,
        diagnostic: str,
        workflow_review_required: bool,
        tenant_id: str = "tenant-a",
        portfolio_id: str = "portfolio-a",
        runtime_mutation: Callable[
            [AdvisePolicyEvaluationRuntimeEvidence], AdvisePolicyEvaluationRuntimeEvidence
        ]
        | None = None,
    ) -> None:
        self.diagnostic = diagnostic
        self.workflow_review_required = workflow_review_required
        self.tenant_id = tenant_id
        self.portfolio_id = portfolio_id
        self.runtime_mutation = runtime_mutation
        self.requests: list[AdvisePolicyEvaluationEvidenceRequest] = []

    def close(self) -> None:
        return None

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        self.requests.append(request)
        generated_at = request.evaluated_at_utc - timedelta(minutes=1)
        route = ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE.format(
            evaluation_id=request.evaluation_id
        )
        runtime = AdvisePolicyEvaluationRuntimeEvidence(
            product_id=ADVISE_POLICY_EVALUATION_PRODUCT_ID,
            product_version=ADVISE_POLICY_EVALUATION_PRODUCT_VERSION,
            route=route,
            evaluation_id=request.evaluation_id,
            tenant_scope_hash=identity_hash(self.tenant_id),
            portfolio_id=self.portfolio_id,
            correlation_id=request.correlation_id,
            trace_id=request.trace_id,
            as_of_date=request.as_of_date,
            generated_at_utc=generated_at,
            content_hash=EVALUATION_HASH,
            source_evidence_hash=SOURCE_EVIDENCE_HASH,
            policy_content_hash=POLICY_CONTENT_HASH,
            policy_pack_id="global-advisory-policy",
            policy_version="2026.07",
            evaluation_status=("PENDING_REVIEW" if self.workflow_review_required else "READY"),
            open_requirement_count=1 if self.workflow_review_required else 0,
            blocked_requirement_count=0,
            sign_off_status=("PENDING_REVIEW" if self.workflow_review_required else "SIGNED_OFF"),
            sign_off_blocker_count=1 if self.workflow_review_required else 0,
            client_ready_publication="BLOCKED",
            data_quality_status="quality_passed",
            freshness="current",
        )
        if self.runtime_mutation is not None:
            runtime = self.runtime_mutation(runtime)
        return AdvisePolicyEvaluationEvidence(
            evaluation_status=runtime.evaluation_status,
            open_requirement_count=runtime.open_requirement_count,
            blocked_requirement_count=runtime.blocked_requirement_count,
            sign_off_status=runtime.sign_off_status,
            sign_off_blocker_count=runtime.sign_off_blocker_count,
            client_ready_publication=runtime.client_ready_publication,
            policy_ref=SourceRef(
                product_id=ADVISE_POLICY_EVALUATION_PRODUCT_ID,
                source_system=SourceSystem.LOTUS_ADVISE,
                product_version=ADVISE_POLICY_EVALUATION_PRODUCT_VERSION,
                route=route,
                as_of_date=request.as_of_date,
                generated_at_utc=generated_at,
                content_hash=EVALUATION_HASH,
                data_quality_status="quality_passed",
                freshness=EvidenceFreshness.CURRENT,
            ),
            workflow_runtime=runtime,
            advise_diagnostic=self.diagnostic,
        )
