from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain import EvidenceFreshness


BOND_MATURITY_LIVE_PROOF_ENV = "LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF"
BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION = "lotus-idea.bond-maturity.live-proof.v1"

BOND_MATURITY_LIVE_BLOCKERS_CLEARED = (
    "opportunity_archetype_maturity_live_core_source_proof_missing",
)

REMAINING_CERTIFICATION_BLOCKERS = (
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
)

BOND_MATURITY_LIVE_PROOF_EVIDENCE_REFS = (
    "scripts/generate_bond_maturity_live_proof.py",
    "src/app/application/bond_maturity_signal.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-05-deterministic-signal-evaluation-and-candidate-generation.md",
)

NON_PROOF_BOUNDARIES = (
    "no_product_recommendation",
    "no_reinvestment_advice",
    "no_cashflow_forecast",
    "no_suitability_or_risk_approval",
    "no_data_mesh_certification",
    "no_workbench_product_proof",
    "no_client_publication_approval",
    "no_supported_feature_promotion",
)


def build_bond_maturity_live_proof_payload(
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
        "schemaVersion": BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofFamily": "bond-maturity",
        "sourceAuthority": _text(evidence_summary.get("sourceAuthority"), "lotus-core"),
        "sourceProductIds": ["lotus-core:HoldingsAsOf:v1"],
        "generatedAtUtc": _format_utc(generated_at_utc),
        "liveCoreSourceAttempted": live_core_source_attempted,
        "runStatus": run_status,
        "holdingsRefPresent": bool(evidence_summary.get("holdingsRefPresent")),
        "maturityFactRefPresent": bool(evidence_summary.get("maturityFactRefPresent")),
        "nextMaturityDatePresent": bool(evidence_summary.get("nextMaturityDatePresent")),
        "maturingPositionCountPresent": bool(evidence_summary.get("maturingPositionCountPresent")),
        "sourceEvidenceCurrent": bool(evidence_summary.get("sourceEvidenceCurrent")),
        "maturityDiagnostic": _text(evidence_summary.get("maturityDiagnostic"), "unknown"),
        "sourceDiagnosticCodes": list(
            dict.fromkeys(_text_sequence(evidence_summary.get("sourceDiagnosticCodes")))
        ),
        "supportedFeaturePromoted": False,
        "proofClosed": False,
        "aggregateBlockersCleared": list(BOND_MATURITY_LIVE_BLOCKERS_CLEARED),
        "proofBlockers": proof_blockers,
        "remainingCertificationBlockers": list(REMAINING_CERTIFICATION_BLOCKERS),
        "evidenceRefs": list(BOND_MATURITY_LIVE_PROOF_EVIDENCE_REFS),
        "nonProofBoundaries": list(NON_PROOF_BOUNDARIES),
    }


def bond_maturity_live_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("schemaVersion") == BOND_MATURITY_LIVE_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("proofFamily") == "bond-maturity"
        and payload.get("sourceAuthority") == "lotus-core"
        and tuple(payload.get("sourceProductIds", ())) == ("lotus-core:HoldingsAsOf:v1",)
        and payload.get("liveCoreSourceAttempted") is True
        and payload.get("runStatus") == "completed"
        and payload.get("holdingsRefPresent") is True
        and payload.get("maturityFactRefPresent") is True
        and payload.get("nextMaturityDatePresent") is True
        and payload.get("maturingPositionCountPresent") is True
        and payload.get("sourceEvidenceCurrent") is True
        and payload.get("maturityDiagnostic") == "core_maturity_evidence_ready"
        and payload.get("supportedFeaturePromoted") is False
        and payload.get("proofClosed") is False
        and isinstance(payload.get("proofBlockers"), list | tuple)
        and "core_maturity_source_proof_missing" not in _text_sequence(payload.get("proofBlockers"))
        and tuple(payload.get("aggregateBlockersCleared", ()))
        == BOND_MATURITY_LIVE_BLOCKERS_CLEARED
    )


def core_maturity_source_refs_are_current(
    holdings_ref: object,
    maturity_fact_ref: object,
) -> bool:
    return (
        getattr(holdings_ref, "freshness", None) is EvidenceFreshness.CURRENT
        and getattr(maturity_fact_ref, "freshness", None) is EvidenceFreshness.CURRENT
    )


def _proof_blockers(
    *,
    evidence_summary: Mapping[str, Any],
    live_core_source_attempted: bool,
) -> list[str]:
    blockers: list[str] = []
    if not live_core_source_attempted:
        blockers.append("core_maturity_source_proof_missing")
    if _run_status(evidence_summary) != "completed":
        blockers.append("core_maturity_source_run_blocked")
        error_code = _text(evidence_summary.get("errorCode"), "")
        if error_code:
            blockers.append(f"source_error_{error_code}")
    if not bool(evidence_summary.get("holdingsRefPresent")):
        blockers.append("core_holdings_source_ref_missing")
    if not bool(evidence_summary.get("maturityFactRefPresent")):
        blockers.append("core_maturity_fact_source_ref_missing")
    if not bool(evidence_summary.get("nextMaturityDatePresent")):
        blockers.append("core_next_maturity_date_missing")
    if not bool(evidence_summary.get("maturingPositionCountPresent")):
        blockers.append("core_maturing_position_count_missing")
    if not bool(evidence_summary.get("sourceEvidenceCurrent")):
        blockers.append("core_maturity_evidence_not_current")
    if _text(evidence_summary.get("maturityDiagnostic"), "") != "core_maturity_evidence_ready":
        blockers.append("core_maturity_evidence_not_ready")
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
