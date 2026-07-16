from __future__ import annotations

from typing import Any

from app.application.runtime_evidence import format_utc, identity_hash, sha256_json

from .scope import AdvisePolicyRuntimeEvidenceScope


def build_advise_policy_request_receipt(
    scope: AdvisePolicyRuntimeEvidenceScope,
    *,
    policy_version: str,
) -> dict[str, Any]:
    material = {
        "tenantIdHash": identity_hash(scope.tenant_id),
        "bookIdHash": identity_hash(scope.book_id),
        "portfolioIdHash": identity_hash(scope.portfolio_id),
        "clientIdHash": identity_hash(scope.client_id),
        "evaluationIdHash": identity_hash(scope.evaluation_id),
        "asOfDate": scope.as_of_date.isoformat(),
        "evaluatedAtUtc": format_utc(scope.evaluated_at_utc),
        "consumerSystem": "lotus-idea",
        "correlationIdHash": identity_hash(scope.correlation_id or ""),
        "traceIdHash": identity_hash(scope.trace_id or ""),
        "policyVersion": policy_version,
    }
    return {**material, "requestDigest": sha256_json(material)}
