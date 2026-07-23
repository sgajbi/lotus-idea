from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from app.application.opportunity_archetype_evidence_pack import (
    CANONICAL_PORTFOLIO_REF,
    build_canonical_opportunity_archetype_evidence_pack,
    validate_opportunity_archetype_evidence_pack_payload,
)

ROOT = Path(__file__).resolve().parents[2]
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_canonical_opportunity_archetype_evidence_pack_is_source_safe_and_bounded() -> None:
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )

    assert validate_opportunity_archetype_evidence_pack_payload(payload, repository_root=ROOT) == []
    serialized = json.dumps(payload, sort_keys=True)
    assert CANONICAL_PORTFOLIO_REF not in serialized
    assert payload["evidenceClass"] == "source_contract"
    assert payload["claimBoundary"]["demoReady"] is False
    assert payload["claimBoundary"]["clientPublicationReady"] is False
    assert payload["claimBoundary"]["dataMeshCertified"] is False
    assert payload["claimBoundary"]["supportedFeaturePromoted"] is False
    assert payload["packSummary"]["archetypeCount"] == 11
    assert payload["packSummary"]["supportedCount"] == 0
    assert "opportunity_archetype_evidence_pack.py" in " ".join(payload["evidenceRefs"])


def test_canonical_opportunity_archetype_evidence_pack_covers_required_families() -> None:
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )

    archetypes = {item["archetypeId"]: item for item in payload["archetypeEvidence"]}

    assert set(archetypes) == {
        "high-cash-idle-liquidity",
        "concentration-risk-review",
        "underperformance-review",
        "allocation-drift-mandate-review",
        "bond-maturity-reinvestment",
        "high-volatility-drawdown-review",
        "missing-suitability-context",
        "mandate-restriction-review",
        "missing-risk-profile-review",
        "low-income-liquidity-shortfall",
        "missing-benchmark-review",
    }
    assert archetypes["concentration-risk-review"]["classification"] == "bounded_foundation"
    assert (
        "lotus-risk:ConcentrationRiskReport:v1"
        in (archetypes["concentration-risk-review"]["sourceProducts"])
    )
    assert (
        "live_risk_source_proof_missing"
        in (archetypes["concentration-risk-review"]["blockerIssueRefs"])
    )
    assert (
        "sgajbi/lotus-risk#211"
        in (
            archetypes["concentration-risk-review"]["blockerIssueRefs"][
                "live_risk_source_proof_missing"
            ]
        )
    )
    assert (
        "performance_benchmark_readiness_source_ref_missing"
        in (archetypes["missing-benchmark-review"]["remainingBlockers"])
    )


def test_canonical_opportunity_archetype_evidence_pack_rejects_overclaiming() -> None:
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )
    payload["claimBoundary"]["supportedFeaturePromoted"] = True
    payload["archetypeEvidence"][0]["classification"] = "supported"

    errors = validate_opportunity_archetype_evidence_pack_payload(payload, repository_root=ROOT)

    assert "claimBoundary.supportedFeaturePromoted must be false" in errors
    assert "high-cash-idle-liquidity: classification must not be supported" in errors


def test_canonical_opportunity_archetype_evidence_pack_rejects_stale_contract_projection() -> None:
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )
    payload["archetypeEvidence"][0]["blockerIssueRefs"]["live_core_source_proof_missing"] = [
        "sgajbi/lotus-idea#999"
    ]

    errors = validate_opportunity_archetype_evidence_pack_payload(payload, repository_root=ROOT)

    assert (
        "high-cash-idle-liquidity: blockerIssueRefs missing or mismatched for "
        "live_core_source_proof_missing"
    ) in errors
