from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import (
    non_authority_claims_are_valid,
    sha256_json,
)
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

from .workflow import reconcile_advise_policy_workflow_receipts

ADVISE_POLICY_RUNTIME_TOP_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "evidenceClass",
        "proofFamily",
        "proofType",
        "sourceAuthority",
        "generatedAtUtc",
        "execution",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "evidenceRefs",
        "nonProofClaims",
    }
)
ADVISE_POLICY_RUNTIME_EXECUTION_KEYS = frozenset(
    {
        "status",
        "evaluatedAtUtc",
        "requestReceipt",
        "workflowReceipt",
        "evaluationReceipt",
        "qualificationBlockers",
    }
)
ADVISE_POLICY_REQUEST_RECEIPT_KEYS = frozenset(
    {
        "tenantIdHash",
        "bookIdHash",
        "portfolioIdHash",
        "clientIdHash",
        "evaluationIdHash",
        "asOfDate",
        "evaluatedAtUtc",
        "consumerSystem",
        "correlationIdHash",
        "traceIdHash",
        "policyVersion",
        "requestDigest",
    }
)
ADVISE_POLICY_WORKFLOW_RECEIPT_KEYS = frozenset(
    {
        "productId",
        "sourceSystem",
        "productVersion",
        "routeTemplate",
        "evaluationIdHash",
        "tenantScopeHash",
        "portfolioIdHash",
        "sourceCorrelationIdHash",
        "sourceTraceIdHash",
        "asOfDate",
        "generatedAtUtc",
        "contentHash",
        "sourceEvidenceHash",
        "policyContentHash",
        "policyPackId",
        "policyVersion",
        "evaluationStatus",
        "openRequirementCount",
        "blockedRequirementCount",
        "signOffStatus",
        "signOffBlockerCount",
        "clientReadyPublication",
        "dataQualityStatus",
        "freshness",
        "adviseDiagnostic",
        "receiptDigest",
    }
)

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ValidatedAdvisePolicyRuntimeEnvelope:
    request: Mapping[str, Any]
    workflow: Mapping[str, Any]
    evaluation: Mapping[str, Any]
    evaluated_at_utc: datetime


def validate_advise_policy_runtime_envelope(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    proof_family: str,
    evaluation_keys: frozenset[str],
    claim_keys: frozenset[str],
) -> ValidatedAdvisePolicyRuntimeEnvelope | None:
    if set(payload) not in (
        ADVISE_POLICY_RUNTIME_TOP_KEYS,
        ADVISE_POLICY_RUNTIME_TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY},
    ):
        return None
    if (
        payload.get("schemaVersion") != schema_version
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != proof_family
        or payload.get("proofType") != "lotus_advise_policy_workflow_evaluation"
        or payload.get("sourceAuthority") != "lotus-advise"
    ):
        return None
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    if (
        generated is None
        or not _mapping_has_exact_keys(execution, ADVISE_POLICY_RUNTIME_EXECUTION_KEYS)
        or not _mapping_has_exact_keys(claims, claim_keys)
    ):
        return None
    assert isinstance(execution, Mapping)
    assert isinstance(claims, Mapping)
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    request = execution.get("requestReceipt")
    workflow = execution.get("workflowReceipt")
    evaluation = execution.get("evaluationReceipt")
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or evaluated is None
        or generated < evaluated
        or not _mapping_has_exact_keys(request, ADVISE_POLICY_REQUEST_RECEIPT_KEYS)
        or not _mapping_has_exact_keys(workflow, ADVISE_POLICY_WORKFLOW_RECEIPT_KEYS)
        or not _mapping_has_exact_keys(evaluation, evaluation_keys)
        or not non_authority_claims_are_valid(
            claims,
            owners={
                "policyWorkflowOwned": "lotus-advise",
                "opportunityDetectionOwned": "lotus-idea",
            },
        )
    ):
        return None
    assert isinstance(request, Mapping)
    assert isinstance(workflow, Mapping)
    assert isinstance(evaluation, Mapping)
    if not _common_receipts_are_valid(request, workflow, evaluation, evaluated):
        return None
    return ValidatedAdvisePolicyRuntimeEnvelope(request, workflow, evaluation, evaluated)


def _common_receipts_are_valid(
    request: Mapping[str, Any],
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    evaluated_at_utc: datetime,
) -> bool:
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except (TypeError, ValueError):
        return False
    for receipt, digest_key in (
        (request, "requestDigest"),
        (workflow, "receiptDigest"),
        (evaluation, "evaluationDigest"),
    ):
        material = {key: value for key, value in receipt.items() if key != digest_key}
        if receipt.get(digest_key) != sha256_json(material):
            return False
    hashes = (
        *(request.get(key) for key in _REQUEST_HASH_KEYS),
        *(workflow.get(key) for key in _WORKFLOW_HASH_KEYS),
        evaluation.get("sourceRefsDigest"),
        evaluation.get("evaluationDigest"),
    )
    return (
        all(_is_sha256(value) for value in hashes)
        and reconcile_advise_policy_workflow_receipts(
            request,
            workflow,
            evaluated_at_utc=evaluated_at_utc,
        )
        and request.get("policyVersion") == evaluation.get("policyVersion")
        and evaluation.get("sourceRefsDigest") == sha256_json([dict(workflow)])
        and str(workflow.get("clientReadyPublication", "")).upper() == "BLOCKED"
    )


def _mapping_has_exact_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == keys


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


_REQUEST_HASH_KEYS = (
    "tenantIdHash",
    "bookIdHash",
    "portfolioIdHash",
    "clientIdHash",
    "evaluationIdHash",
    "correlationIdHash",
    "traceIdHash",
    "requestDigest",
)
_WORKFLOW_HASH_KEYS = (
    "tenantScopeHash",
    "portfolioIdHash",
    "evaluationIdHash",
    "sourceCorrelationIdHash",
    "sourceTraceIdHash",
    "contentHash",
    "sourceEvidenceHash",
    "policyContentHash",
    "receiptDigest",
)
