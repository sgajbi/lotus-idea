from __future__ import annotations

from dataclasses import replace
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


class AuthoritativeAdviseMissingSuitabilitySource:
    def __init__(
        self,
        *,
        tenant_id: str = "tenant-a",
        portfolio_id: str = "portfolio-a",
        context_missing: bool = True,
        runtime_mutation: Callable[
            [AdvisePolicyEvaluationRuntimeEvidence], AdvisePolicyEvaluationRuntimeEvidence
        ]
        | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.portfolio_id = portfolio_id
        self.context_missing = context_missing
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
            policy_pack_id="global-suitability",
            policy_version="2026.07",
            evaluation_status="PENDING_REVIEW" if self.context_missing else "READY",
            open_requirement_count=1 if self.context_missing else 0,
            blocked_requirement_count=0,
            sign_off_status="PENDING_REVIEW" if self.context_missing else "SIGNED_OFF",
            sign_off_blocker_count=1 if self.context_missing else 0,
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
            advise_diagnostic=(
                "advise_policy_requirements_open"
                if self.context_missing
                else "advise_policy_context_available"
            ),
        )


def without_runtime_field(
    field_name: str,
) -> Callable[[AdvisePolicyEvaluationRuntimeEvidence], AdvisePolicyEvaluationRuntimeEvidence]:
    return lambda runtime: replace(runtime, **{field_name: None})
