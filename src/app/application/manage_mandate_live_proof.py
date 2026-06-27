from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import SignalEvaluationOutcome


MANAGE_MANDATE_LIVE_PROOF_ENV = "LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF"
MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.manage-mandate.live-proof.v1"

MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_portfolio_scoped_manage_source_proof_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_mandate_performance_health_source_ref_missing",
    "opportunity_archetype_mandate_risk_health_source_ref_missing",
    "opportunity_archetype_core_portfolio_state_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

MANAGE_MANDATE_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_manage_mandate_live_proof.py",
    "src/app/domain/signal_evaluation.py",
    "src/app/application/mandate_health_signal.py",
    "src/app/infrastructure/lotus_manage_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
)

NON_PROOF_BOUNDARIES = (
    "no_rebalance_action_creation",
    "no_order_execution",
    "no_mandate_compliance_certification",
    "no_client_publication_approval",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_supported_feature_promotion",
)


def build_manage_mandate_live_proof_payload(
    *,
    generated_at_utc: datetime,
    evaluation_summary: Mapping[str, Any],
    live_manage_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(evaluation_summary)
    evaluation_outcome = _text(evaluation_summary.get("evaluationOutcome"), "")
    proof_blockers = _proof_blockers(
        evaluation_summary=evaluation_summary,
        live_manage_source_attempted=live_manage_source_attempted,
    )
    return {
        "schemaVersion": MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "allocation-drift-mandate-review",
        "sourceAuthority": _text(evaluation_summary.get("sourceAuthority"), "lotus-manage"),
        "sourceProductId": _text(
            evaluation_summary.get("sourceProductId"),
            "lotus-manage:PortfolioActionRegister:v1",
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveManageSourceAttempted": live_manage_source_attempted,
        "runStatus": run_status,
        "evaluationOutcome": evaluation_outcome,
        "candidateGenerated": _candidate_generated(evaluation_outcome),
        "sourceEvidenceCurrent": bool(evaluation_summary.get("sourceEvidenceCurrent")),
        "portfolioScopeConfirmed": bool(evaluation_summary.get("portfolioScopeConfirmed")),
        "manageActionRegisterReady": bool(evaluation_summary.get("manageActionRegisterReady")),
        "workflowDecisionCount": _non_negative_int_or_zero(
            evaluation_summary.get("workflowDecisionCount")
        ),
        "lineageEdgeCount": _non_negative_int_or_zero(evaluation_summary.get("lineageEdgeCount")),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("sourceDiagnosticCodes")))
        ),
        "reasonCodes": list(dict.fromkeys(_text_sequence(evaluation_summary.get("reasonCodes")))),
        "unsupportedReasons": list(
            dict.fromkeys(_text_sequence(evaluation_summary.get("unsupportedReasons")))
        ),
        "rebalanceExecutionAuthorityGranted": False,
        "orderExecutionReady": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(MANAGE_MANDATE_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def manage_mandate_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "allocation-drift-mandate-review"
        and payload.get("sourceAuthority") == "lotus-manage"
        and payload.get("sourceProductId") == "lotus-manage:PortfolioActionRegister:v1"
        and payload.get("liveManageSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("candidateGenerated") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("portfolioScopeConfirmed") is True
        and payload.get("manageActionRegisterReady") is True
        and _positive_int(payload.get("workflowDecisionCount"))
        and _positive_int(payload.get("lineageEdgeCount"))
        and payload.get("rebalanceExecutionAuthorityGranted") is False
        and payload.get("orderExecutionReady") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "manage_portfolio_scoped_source_proof_missing"
        not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    evaluation_summary: Mapping[str, Any],
    live_manage_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_manage_source_attempted:
        blockers.append("manage_portfolio_scoped_source_proof_missing")
    if _run_status(evaluation_summary) != "completed":
        blockers.append("manage_source_run_blocked")
        error_code = _text(evaluation_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evaluation_summary.get("sourceEvidenceCurrent")):
        blockers.append("manage_source_evidence_not_current")
    if not bool(evaluation_summary.get("portfolioScopeConfirmed")):
        blockers.append("manage_portfolio_scope_not_confirmed")
    if not bool(evaluation_summary.get("manageActionRegisterReady")):
        blockers.append("manage_action_register_not_ready")
    if not _positive_int(evaluation_summary.get("workflowDecisionCount")):
        blockers.append("manage_workflow_decision_evidence_missing")
    if not _positive_int(evaluation_summary.get("lineageEdgeCount")):
        blockers.append("manage_lineage_evidence_missing")
    if not _candidate_generated(_text(evaluation_summary.get("evaluationOutcome"), "")):
        blockers.append("no_allocation_drift_mandate_candidate_generated")
    return list(dict.fromkeys(blockers))


def _run_status(summary: Mapping[str, Any]) -> str:
    explicit_status = _text(summary.get("runStatus") or summary.get("status"), "")
    if explicit_status:
        return explicit_status
    return "completed" if summary else "unknown"


def _candidate_generated(evaluation_outcome: str) -> bool:
    return evaluation_outcome == SignalEvaluationOutcome.CANDIDATE_CREATED.value


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_negative_int_or_zero(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


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
