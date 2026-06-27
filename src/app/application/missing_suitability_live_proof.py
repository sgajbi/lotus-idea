from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import SignalEvaluationOutcome


MISSING_SUITABILITY_LIVE_PROOF_ENV = "LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF"
MISSING_SUITABILITY_LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.missing-suitability.live-proof.v1"

MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_advise_policy_live_source_proof_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MISSING_SUITABILITY_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_missing_suitability_live_proof.py",
    "src/app/domain/missing_suitability_signal.py",
    "src/app/application/missing_suitability_signal.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
)

NON_PROOF_BOUNDARIES = (
    "no_suitability_approval",
    "no_policy_approval",
    "no_proposal_approval",
    "no_client_publication_approval",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_supported_feature_promotion",
)


def build_missing_suitability_live_proof_payload(
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
        "schemaVersion": MISSING_SUITABILITY_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "missing-suitability-context",
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
        "clientReadyPublicationBlocked": bool(
            evaluation_summary.get("clientReadyPublicationBlocked")
        ),
        "advisePolicyWorkflowReady": bool(evaluation_summary.get("advisePolicyWorkflowReady")),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("sourceDiagnosticCodes")))
        ),
        "reasonCodes": list(dict.fromkeys(_text_sequence(evaluation_summary.get("reasonCodes")))),
        "unsupportedReasons": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("unsupportedReasons")))
        ),
        "suitabilityAuthorityGranted": False,
        "policyApprovalGranted": False,
        "proposalApprovalGranted": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MISSING_SUITABILITY_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def missing_suitability_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == MISSING_SUITABILITY_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "missing-suitability-context"
        and payload.get("sourceAuthority") == "lotus-advise"
        and payload.get("sourceProductId") == "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
        and payload.get("liveAdviseSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("candidateGenerated") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("clientReadyPublicationBlocked") is True
        and payload.get("advisePolicyWorkflowReady") is True
        and payload.get("suitabilityAuthorityGranted") is False
        and payload.get("policyApprovalGranted") is False
        and payload.get("proposalApprovalGranted") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "advise_policy_live_source_proof_missing"
        not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    evaluation_summary: Mapping[str, Any],
    live_advise_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_advise_source_attempted:
        blockers.append("advise_policy_live_source_proof_missing")
    if _run_status(evaluation_summary) != "completed":
        blockers.append("advise_policy_source_run_blocked")
        error_code = _text(evaluation_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evaluation_summary.get("sourceEvidenceCurrent")):
        blockers.append("advise_policy_source_evidence_not_current")
    if not bool(evaluation_summary.get("clientReadyPublicationBlocked")):
        blockers.append("client_publication_boundary_not_blocked")
    if not bool(evaluation_summary.get("advisePolicyWorkflowReady")):
        blockers.append("advise_policy_workflow_not_ready")
    if not _candidate_generated(_text(evaluation_summary.get("evaluationOutcome"), "")):
        blockers.append("no_missing_suitability_context_candidate_generated")
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
