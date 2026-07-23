from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil

import pytest

from app.application.opportunity_archetype_evidence_pack import (
    CANONICAL_PORTFOLIO_REF,
    build_canonical_opportunity_archetype_evidence_pack,
    opportunity_archetype_evidence_pack_is_valid,
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


def test_canonical_opportunity_archetype_evidence_pack_rejects_malformed_payload() -> None:
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )
    payload["unexpectedField"] = True
    payload["debugPortfolioRef"] = CANONICAL_PORTFOLIO_REF
    payload.pop("repository")
    payload["generatedAtUtc"] = "not-a-timestamp"
    payload["schemaVersion"] = "lotus-idea.opportunity-archetype.evidence-pack.v0"
    payload["rfc"] = "RFC-9999"
    payload["rfcSlice"] = "slice-99"
    payload["evidenceClass"] = "operational_receipt"
    payload["proofFamily"] = "demo"
    payload["proofType"] = "client_publication_pack"
    payload["claimBoundary"] = "certified"
    payload["canonicalPortfolioScope"] = "PB_SG_GLOBAL_BAL_001"
    payload["archetypeEvidence"] = "not-a-list"

    errors = validate_opportunity_archetype_evidence_pack_payload(payload, repository_root=ROOT)

    assert opportunity_archetype_evidence_pack_is_valid(payload) is False
    assert "unexpected evidence pack fields: debugPortfolioRef, unexpectedField" in errors
    assert "missing evidence pack fields: repository" in errors
    assert "forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present" in errors
    assert "generatedAtUtc must be timezone-aware" in errors
    assert "schemaVersion must be lotus-idea.opportunity-archetype.evidence-pack.v1" in errors
    assert "repository must be lotus-idea" in errors
    assert "evidence pack must be bound to RFC-0002 slice-16" in errors
    assert "evidenceClass must be source_contract" in errors
    assert "proofFamily must be opportunity_archetype" in errors
    assert "proofType must be canonical_archetype_evidence_pack" in errors
    assert "claimBoundary must be an object" in errors
    assert "canonicalPortfolioScope must be an object" in errors
    assert "archetypeEvidence must be a list" in errors


def test_canonical_opportunity_archetype_evidence_pack_rejects_boundary_drift() -> None:
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )
    payload["claimBoundary"]["demoReady"] = True
    payload["claimBoundary"]["clientPublicationReady"] = True
    payload["claimBoundary"]["dataMeshCertified"] = True
    payload["claimBoundary"]["productionIdentityCertified"] = True
    payload["claimBoundary"]["supportabilityStatus"] = "certified"
    payload["claimBoundary"]["readinessStatus"] = "ready"
    payload["canonicalPortfolioScope"]["sourceRefSha256"] = "wrong-hash"
    payload["canonicalPortfolioScope"]["governedDatasetRefs"] = []
    payload["archetypeEvidence"][0]["sourceProducts"] = []
    payload["archetypeEvidence"][0]["evidenceRefs"] = []
    payload["archetypeEvidence"][0]["remainingBlockers"] = []
    payload["archetypeEvidence"][0]["blockerIssueRefs"] = []

    errors = validate_opportunity_archetype_evidence_pack_payload(payload, repository_root=ROOT)

    assert "claimBoundary.demoReady must be false" in errors
    assert "claimBoundary.clientPublicationReady must be false" in errors
    assert "claimBoundary.dataMeshCertified must be false" in errors
    assert "claimBoundary.productionIdentityCertified must be false" in errors
    assert "claimBoundary.supportabilityStatus must be not_certified" in errors
    assert "claimBoundary.readinessStatus must be blocked" in errors
    assert "canonicalPortfolioScope.sourceRefSha256 does not match canonical scope" in errors
    assert "canonicalPortfolioScope.governedDatasetRefs must be a non-empty list" in errors
    assert "high-cash-idle-liquidity: sourceProducts do not match contract" in errors
    assert "high-cash-idle-liquidity: evidenceRefs do not match contract" in errors
    assert "high-cash-idle-liquidity: remainingBlockers do not match contract" in errors
    assert "high-cash-idle-liquidity: blockerIssueRefs must be an object" in errors


def test_canonical_opportunity_archetype_evidence_pack_rejects_contract_overclaims(
    tmp_path: Path,
) -> None:
    repo_root = _copy_opportunity_archetype_contract_repo(tmp_path)
    contract_path = (
        repo_root / "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["demo_ready"] = True
    contract["supported_feature_promoted"] = True
    contract["canonical_portfolio_ref"] = "PB_SG_UNGOVERNED_999"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
    )

    errors = validate_opportunity_archetype_evidence_pack_payload(
        payload,
        repository_root=repo_root,
    )

    assert "source contract must not claim demo or client-publication readiness" in errors
    assert "source contract must not claim supported-feature or data-mesh certification" in errors
    assert "source contract canonical portfolio ref is unexpected" in errors


def test_canonical_opportunity_archetype_evidence_pack_build_rejects_wrong_scope(
    tmp_path: Path,
) -> None:
    repo_root = _copy_opportunity_archetype_contract_repo(tmp_path)
    contract_path = (
        repo_root / "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["canonical_portfolio_ref"] = "PB_SG_UNGOVERNED_999"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="opportunity archetype contract is not bound to the canonical portfolio",
    ):
        build_canonical_opportunity_archetype_evidence_pack(
            generated_at_utc=GENERATED_AT,
            repository_root=repo_root,
        )


def test_canonical_opportunity_archetype_evidence_pack_build_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_canonical_opportunity_archetype_evidence_pack(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            repository_root=ROOT,
        )


def _copy_opportunity_archetype_contract_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    contract_dir = repo_root / "contracts" / "opportunity-archetypes"
    contract_dir.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
        contract_dir / "lotus-idea-opportunity-archetypes.v1.json",
    )
    return repo_root
