from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import EvidenceFreshness


CORE_PORTFOLIO_STATE_LIVE_PROOF_ENV = "LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF"
CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.core-portfolio-state.live-proof.v1"

CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_core_portfolio_state_source_ref_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_portfolio_scoped_manage_source_proof_missing",
    "opportunity_archetype_mandate_performance_health_source_ref_missing",
    "opportunity_archetype_mandate_risk_health_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

CORE_PORTFOLIO_STATE_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_core_portfolio_state_live_proof.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-16-demo-readiness-archetype-scenarios-and-commercial-proof.md",
)

NON_PROOF_BOUNDARIES = (
    "no_mandate_performance_health_proof",
    "no_mandate_risk_health_proof",
    "no_manage_action_register_proof",
    "no_rebalance_action_creation",
    "no_order_execution",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_client_publication_approval",
    "no_supported_feature_promotion",
)


def build_core_portfolio_state_live_proof_payload(
    *,
    generated_at_utc: datetime,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    proof_blockers = _proof_blockers(
        evidence_summary=evidence_summary,
        live_core_source_attempted=live_core_source_attempted,
    )
    return {
        "schemaVersion": CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "core-portfolio-state",
        "sourceAuthority": _text(evidence_summary.get("sourceAuthority"), "lotus-core"),
        "sourceProductId": _text(
            evidence_summary.get("sourceProductId"),
            "lotus-core:PortfolioStateSnapshot:v1",
        ),
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveCoreSourceAttempted": live_core_source_attempted,
        "runStatus": _run_status(evidence_summary),
        "portfolioStateRefPresent": bool(evidence_summary.get("portfolioStateRefPresent")),
        "sourceEvidenceCurrent": bool(evidence_summary.get("sourceEvidenceCurrent")),
        "sourceEvidenceAvailable": bool(evidence_summary.get("sourceEvidenceAvailable")),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evidence_summary.get("sourceDiagnosticCodes")))
        ),
        "rebalanceExecutionAuthorityGranted": False,
        "orderExecutionReady": False,
        "clientPublicationReady": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(CORE_PORTFOLIO_STATE_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def core_portfolio_state_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "core-portfolio-state"
        and payload.get("sourceAuthority") == "lotus-core"
        and payload.get("sourceProductId") == "lotus-core:PortfolioStateSnapshot:v1"
        and payload.get("liveCoreSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("portfolioStateRefPresent") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("sourceEvidenceAvailable") is True
        and payload.get("rebalanceExecutionAuthorityGranted") is False
        and payload.get("orderExecutionReady") is False
        and payload.get("clientPublicationReady") is False
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "core_portfolio_state_source_proof_missing"
        not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED
    )


def core_source_ref_is_current(value: object) -> bool:
    return getattr(value, "freshness", None) is EvidenceFreshness.CURRENT


def _proof_blockers(
    *,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_core_source_attempted:
        blockers.append("core_portfolio_state_source_proof_missing")
    if _run_status(evidence_summary) != "completed":
        blockers.append("core_portfolio_state_source_run_blocked")
        error_code = _text(evidence_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evidence_summary.get("portfolioStateRefPresent")):
        blockers.append("core_portfolio_state_source_ref_missing")
    if not bool(evidence_summary.get("sourceEvidenceAvailable")):
        blockers.append("core_portfolio_state_evidence_unavailable")
    if not bool(evidence_summary.get("sourceEvidenceCurrent")):
        blockers.append("core_portfolio_state_evidence_not_current")
    return list(dict.fromkeys(blockers))


def _run_status(summary: Mapping[str, Any]) -> str:
    explicit_status = _text(summary.get("runStatus") or summary.get("status"), "")
    if explicit_status:
        return explicit_status
    return "completed" if summary else "unknown"


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
