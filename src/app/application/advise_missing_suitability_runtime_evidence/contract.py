from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.advise_policy_runtime_evidence import (
    validate_advise_policy_runtime_envelope,
)
from app.domain import missing_suitability_review_required_from_workflow

from .runtime_execution import (
    ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS,
    ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED,
    ADVISE_MISSING_SUITABILITY_RUNTIME_EVIDENCE_REFS,
    ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
)

_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "reasonCodes",
        "unsupportedReasons",
        "policyVersion",
        "minimumOpenRequirementCount",
        "candidateScore",
        "suitabilityContextMissing",
        "candidateIdHash",
        "signalIdHash",
        "evidencePacketIdHash",
        "sourceRefsDigest",
        "evaluationDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "policyWorkflowOwned",
        "opportunityDetectionOwned",
        "suitabilityApproved",
        "policyApproved",
        "proposalApproved",
        "signOffApproved",
        "clientPublicationApproved",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
        "ideaPersistenceRequired",
    }
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def advise_missing_suitability_runtime_execution_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    envelope = validate_advise_policy_runtime_envelope(
        payload,
        schema_version=ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
        proof_family="missing_suitability_context",
        evaluation_keys=_EVALUATION_KEYS,
        claim_keys=_CLAIM_KEYS,
    )
    if envelope is None:
        return False
    return (
        _evaluation_receipt_is_valid(envelope.workflow, envelope.evaluation)
        and tuple(payload.get("aggregateBlockersSatisfied") or ())
        == ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ())
        == ADVISE_MISSING_SUITABILITY_RUNTIME_EVIDENCE_REFS
    )


def _evaluation_receipt_is_valid(
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    try:
        score = Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    minimum_open = evaluation.get("minimumOpenRequirementCount")
    if (
        not isinstance(minimum_open, int)
        or isinstance(minimum_open, bool)
        or minimum_open < 0
        or score < Decimal("0")
        or score > Decimal("100")
        or evaluation.get("family") != "missing_suitability_context"
        or evaluation.get("unsupportedReasons") != []
    ):
        return False
    values = (
        workflow.get("evaluationStatus"),
        workflow.get("openRequirementCount"),
        workflow.get("blockedRequirementCount"),
        workflow.get("signOffStatus"),
        workflow.get("signOffBlockerCount"),
    )
    if not (
        isinstance(values[0], str)
        and isinstance(values[1], int)
        and not isinstance(values[1], bool)
        and isinstance(values[2], int)
        and not isinstance(values[2], bool)
        and isinstance(values[3], str)
        and isinstance(values[4], int)
        and not isinstance(values[4], bool)
    ):
        return False
    context_missing = missing_suitability_review_required_from_workflow(
        evaluation_status=values[0],
        open_requirement_count=values[1],
        blocked_requirement_count=values[2],
        sign_off_status=values[3],
        sign_off_blocker_count=values[4],
        minimum_open_requirement_count=minimum_open,
    )
    if evaluation.get("suitabilityContextMissing") is not context_missing:
        return False
    if context_missing:
        return (
            evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and _is_sha256(evaluation.get("evidencePacketIdHash"))
            and tuple(evaluation.get("reasonCodes") or ())
            == ("suitability_context_missing", "review_required")
        )
    return (
        evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and evaluation.get("evidencePacketIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
