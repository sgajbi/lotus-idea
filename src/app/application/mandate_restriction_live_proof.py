from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import SignalEvaluationOutcome


MANDATE_RESTRICTION_LIVE_PROOF_ENV = "LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF"
MANDATE_RESTRICTION_LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.mandate-restriction.live-proof.v1"

MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_live_restriction_source_proof_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_typed_restriction_source_product_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MANDATE_RESTRICTION_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_mandate_restriction_live_proof.py",
    "src/app/domain/mandate_restriction_signal.py",
    "src/app/application/mandate_restriction_signal.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
)

NON_PROOF_BOUNDARIES = (
    "no_mandate_state_change",
    "no_restriction_clearance",
    "no_suitability_approval",
    "no_policy_approval",
    "no_proposal_approval",
    "no_rebalance_authority",
    "no_order_authority",
    "no_client_publication_approval",
    "no_typed_restriction_source_product_certification",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_supported_feature_promotion",
)


def build_mandate_restriction_live_proof_payload(
    *,
    generated_at_utc: datetime,
    evaluation_summary: Mapping[str, Any],
    live_advise_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(evaluation_summary)
    evaluation_outcome = _text(evaluation_summary.get("evaluationOutcome"), "")
    proof_blockers = _proof_blockers(
        evaluation_summary=evaluation_summary,
        live_advise_source_attempted=live_advise_source_attempted,
    )
    return {
        "schemaVersion": MANDATE_RESTRICTION_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "mandate-restriction-review",
        "sourceAuthority": _text(evaluation_summary.get("sourceAuthority"), "lotus-advise"),
        "sourceProductId": _text(
            evaluation_summary.get("sourceProductId"),
            "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveAdviseSourceAttempted": live_advise_source_attempted,
        "runStatus": run_status,
        "evaluationOutcome": evaluation_outcome,
        "candidateGenerated": _candidate_generated(evaluation_outcome),
        "sourceEvidenceCurrent": bool(evaluation_summary.get("sourceEvidenceCurrent")),
        "restrictionReviewReady": bool(evaluation_summary.get("restrictionReviewReady")),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("sourceDiagnosticCodes")))
        ),
        "reasonCodes": list(dict.fromkeys(_text_sequence(evaluation_summary.get("reasonCodes")))),
        "unsupportedReasons": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("unsupportedReasons")))
        ),
        "mandateStateChanged": False,
        "restrictionCleared": False,
        "suitabilityAuthorityGranted": False,
        "policyApprovalGranted": False,
        "proposalApprovalGranted": False,
        "rebalanceAuthorityGranted": False,
        "orderAuthorityGranted": False,
        "clientPublicationReady": False,
        "typedRestrictionSourceProductCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MANDATE_RESTRICTION_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def mandate_restriction_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == MANDATE_RESTRICTION_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "mandate-restriction-review"
        and payload.get("sourceAuthority") == "lotus-advise"
        and payload.get("sourceProductId") == "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
        and payload.get("liveAdviseSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("candidateGenerated") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("restrictionReviewReady") is True
        and payload.get("mandateStateChanged") is False
        and payload.get("restrictionCleared") is False
        and payload.get("suitabilityAuthorityGranted") is False
        and payload.get("policyApprovalGranted") is False
        and payload.get("proposalApprovalGranted") is False
        and payload.get("rebalanceAuthorityGranted") is False
        and payload.get("orderAuthorityGranted") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("typedRestrictionSourceProductCertified") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "restriction_live_source_proof_missing"
        not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    evaluation_summary: Mapping[str, Any],
    live_advise_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_advise_source_attempted:
        blockers.append("restriction_live_source_proof_missing")
    if _run_status(evaluation_summary) != "completed":
        blockers.append("restriction_source_run_blocked")
        error_code = _text(evaluation_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evaluation_summary.get("sourceEvidenceCurrent")):
        blockers.append("restriction_source_evidence_not_current")
    if not bool(evaluation_summary.get("restrictionReviewReady")):
        blockers.append("restriction_review_source_diagnostic_missing")
    if not _candidate_generated(_text(evaluation_summary.get("evaluationOutcome"), "")):
        blockers.append("no_mandate_restriction_candidate_generated")
    return list(dict.fromkeys(blockers))


def _run_status(summary: Mapping[str, Any]) -> str:
    explicit_status = _text(summary.get("runStatus") or summary.get("status"), "")
    if explicit_status:
        return explicit_status
    return "completed" if summary else "unknown"


def _candidate_generated(evaluation_outcome: str) -> bool:
    return evaluation_outcome == SignalEvaluationOutcome.CANDIDATE_CREATED.value


def _text_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
