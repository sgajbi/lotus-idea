from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from app.application.advise_policy_runtime_evidence import (
    validate_advise_policy_runtime_envelope,
)
from app.application.runtime_evidence import score_receipt_is_valid
from app.domain import (
    RiskProfilePosture,
    missing_risk_profile_review_required_from_diagnostic,
    risk_profile_posture_from_advise_diagnostic,
)

from .runtime_execution import (
    ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS,
    ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED,
    ADVISE_MISSING_RISK_PROFILE_RUNTIME_EVIDENCE_REFS,
    ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_SCHEMA_VERSION,
)

_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "reasonCodes",
        "unsupportedReasons",
        "policyVersion",
        "candidateScore",
        "scoreReasonCodes",
        "scoreComponents",
        "scoreConflictPenaltyApplied",
        "riskProfilePosture",
        "riskProfileReviewRequired",
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
        "riskProfileApproved",
        "suitabilityApproved",
        "policyApproved",
        "proposalApproved",
        "signOffApproved",
        "clientPublicationApproved",
        "typedRiskProfileSourceProductCertified",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
        "ideaPersistenceRequired",
    }
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def advise_missing_risk_profile_runtime_execution_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    envelope = validate_advise_policy_runtime_envelope(
        payload,
        schema_version=ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        proof_family="missing_risk_profile",
        evaluation_keys=_EVALUATION_KEYS,
        claim_keys=_CLAIM_KEYS,
    )
    if envelope is None:
        return False
    return (
        _evaluation_receipt_is_valid(envelope.workflow, envelope.evaluation)
        and tuple(payload.get("aggregateBlockersSatisfied") or ())
        == ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ())
        == ADVISE_MISSING_RISK_PROFILE_RUNTIME_EVIDENCE_REFS
    )


def _evaluation_receipt_is_valid(
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    diagnostic = workflow.get("adviseDiagnostic")
    posture = risk_profile_posture_from_advise_diagnostic(
        diagnostic if isinstance(diagnostic, str) else None
    )
    review_required_value = missing_risk_profile_review_required_from_diagnostic(
        diagnostic if isinstance(diagnostic, str) else None
    )
    if not isinstance(review_required_value, bool):
        return False
    review_required: bool = review_required_value
    if (
        posture is None
        or evaluation.get("family") != "missing_risk_profile"
        or evaluation.get("unsupportedReasons") != []
        or evaluation.get("riskProfilePosture") != posture.value
        or evaluation.get("riskProfileReviewRequired") is not review_required
    ):
        return False
    if not score_receipt_is_valid(evaluation, candidate_expected=review_required):
        return False
    if review_required:
        return (
            posture is not RiskProfilePosture.CURRENT
            and evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and _is_sha256(evaluation.get("evidencePacketIdHash"))
            and tuple(evaluation.get("reasonCodes") or ())
            == ("missing_risk_profile", "review_required")
        )
    return (
        posture is RiskProfilePosture.CURRENT
        and evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and evaluation.get("evidencePacketIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
