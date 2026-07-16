from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.advise_policy_runtime_evidence import (
    validate_advise_policy_runtime_envelope,
)
from app.application.mandate_restriction_signal import (
    mandate_restriction_review_ready_from_advise_diagnostic,
)

from .runtime_execution import (
    ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_EVIDENCE_REFS,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
)

_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "reasonCodes",
        "unsupportedReasons",
        "policyVersion",
        "candidateScore",
        "restrictionReviewRequired",
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
        "restrictionCleared",
        "suitabilityApproved",
        "policyApproved",
        "proposalApproved",
        "rebalanceAuthorized",
        "orderAuthorized",
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


def advise_mandate_restriction_runtime_execution_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    envelope = validate_advise_policy_runtime_envelope(
        payload,
        schema_version=ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        proof_family="mandate_restriction_review",
        evaluation_keys=_EVALUATION_KEYS,
        claim_keys=_CLAIM_KEYS,
    )
    if envelope is None:
        return False
    return (
        _evaluation_receipt_is_valid(envelope.workflow, envelope.evaluation)
        and tuple(payload.get("aggregateBlockersSatisfied") or ())
        == ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ())
        == ADVISE_MANDATE_RESTRICTION_RUNTIME_EVIDENCE_REFS
    )


def _evaluation_receipt_is_valid(
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    try:
        score = Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    if (
        score < Decimal("0")
        or score > Decimal("100")
        or evaluation.get("family") != "mandate_restriction"
        or evaluation.get("unsupportedReasons") != []
    ):
        return False
    review_required = mandate_restriction_review_ready_from_advise_diagnostic(
        _optional_text(workflow.get("adviseDiagnostic"))
    )
    if evaluation.get("restrictionReviewRequired") is not review_required:
        return False
    if review_required:
        return (
            evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and _is_sha256(evaluation.get("evidencePacketIdHash"))
            and tuple(evaluation.get("reasonCodes") or ())
            == ("mandate_restriction_review", "review_required")
        )
    return (
        evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and evaluation.get("evidencePacketIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
