from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import EvidenceFreshness


LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_ENV = "LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF"
LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION = (
    "lotus-idea.low-income-core-cashflow.live-proof.v1"
)

LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_live_core_cashflow_source_proof_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_low_income_core_cashflow_live_proof.py",
    "src/app/application/low_income_signal.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
)

NON_PROOF_BOUNDARIES = (
    "no_client_income_needs_inference",
    "no_funding_advice",
    "no_treasury_instruction",
    "no_suitability_or_planning_objective_proof",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_client_publication_approval",
    "no_supported_feature_promotion",
)


def build_low_income_core_cashflow_live_proof_payload(
    *,
    generated_at_utc: datetime,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> dict[str, Any]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    run_status = _run_status(evidence_summary)
    proof_blockers = _proof_blockers(
        evidence_summary=evidence_summary,
        live_core_source_attempted=live_core_source_attempted,
    )
    return {
        "schemaVersion": LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "low-income-core-cashflow",
        "sourceAuthority": _text(evidence_summary.get("sourceAuthority"), "lotus-core"),
        "sourceProductIds": [
            "lotus-core:PortfolioCashflowProjection:v1",
            "lotus-core:PortfolioCashMovementSummary:v1",
        ],
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveCoreSourceAttempted": live_core_source_attempted,
        "runStatus": run_status,
        "cashMovementRefPresent": bool(evidence_summary.get("cashMovementRefPresent")),
        "cashflowProjectionRefPresent": bool(evidence_summary.get("cashflowProjectionRefPresent")),
        "cashMovementCountPresent": bool(evidence_summary.get("cashMovementCountPresent")),
        "projectedCumulativeCashflowPresent": bool(
            evidence_summary.get("projectedCumulativeCashflowPresent")
        ),
        "sourceEvidenceCurrent": bool(evidence_summary.get("sourceEvidenceCurrent")),
        "cashflowDiagnostic": _text(evidence_summary.get("cashflowDiagnostic"), "unknown"),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evidence_summary.get("sourceDiagnosticCodes")))
        ),
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def low_income_core_cashflow_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "low-income-core-cashflow"
        and payload.get("sourceAuthority") == "lotus-core"
        and tuple(payload.get("sourceProductIds", ()))
        == (
            "lotus-core:PortfolioCashflowProjection:v1",
            "lotus-core:PortfolioCashMovementSummary:v1",
        )
        and payload.get("liveCoreSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("cashMovementRefPresent") is True
        and payload.get("cashflowProjectionRefPresent") is True
        and payload.get("cashMovementCountPresent") is True
        and payload.get("projectedCumulativeCashflowPresent") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("cashflowDiagnostic") == "core_cashflow_liquidity_evidence_ready"
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "core_cashflow_source_proof_missing" not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED
    )


def _proof_blockers(
    *,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_core_source_attempted:
        blockers.append("core_cashflow_source_proof_missing")
    if _run_status(evidence_summary) != "completed":
        blockers.append("core_cashflow_source_run_blocked")
        error_code = _text(evidence_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evidence_summary.get("cashMovementRefPresent")):
        blockers.append("core_cash_movement_source_ref_missing")
    if not bool(evidence_summary.get("cashflowProjectionRefPresent")):
        blockers.append("core_cashflow_projection_source_ref_missing")
    if not bool(evidence_summary.get("cashMovementCountPresent")):
        blockers.append("core_cash_movement_count_missing")
    if not bool(evidence_summary.get("projectedCumulativeCashflowPresent")):
        blockers.append("core_projected_cumulative_cashflow_missing")
    if not bool(evidence_summary.get("sourceEvidenceCurrent")):
        blockers.append("core_cashflow_evidence_not_current")
    if (
        _text(evidence_summary.get("cashflowDiagnostic"), "")
        != "core_cashflow_liquidity_evidence_ready"
    ):
        blockers.append("core_cashflow_liquidity_evidence_not_ready")
    return list(dict.fromkeys(blockers))


def core_cashflow_source_refs_are_current(
    cash_movement_ref: object,
    cashflow_projection_ref: object,
) -> bool:
    return (
        getattr(cash_movement_ref, "freshness", None) is EvidenceFreshness.CURRENT
        and getattr(cashflow_projection_ref, "freshness", None) is EvidenceFreshness.CURRENT
    )


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
