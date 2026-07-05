from __future__ import annotations

from typing import Any


ALLOWED_CONSUMPTION_MODES = {"api_read", "supportability_lookup"}
REQUIRED_CONSUMER_TRUST_METADATA = {"product_name", "product_version", "correlation_id"}
FRESHNESS_METADATA = {"as_of_date", "generated_at"}
PROVENANCE_METADATA = {
    "lineage_bundle_id",
    "lineage_version",
    "request_fingerprint",
    "snapshot_id",
    "source_batch_fingerprint",
    "source_services",
}

PROVENANCE_REQUIRED_PRODUCTS = {
    ("lotus-core", "PortfolioStateSnapshot"),
    ("lotus-core", "HoldingsAsOf"),
    ("lotus-core", "PortfolioCashMovementSummary"),
    ("lotus-core", "PortfolioCashflowProjection"),
    ("lotus-core", "BenchmarkAssignment"),
    ("lotus-performance", "MandatePerformanceHealthContext"),
    ("lotus-risk", "RiskMetricsReport"),
    ("lotus-risk", "ConcentrationRiskReport"),
    ("lotus-risk", "MandateRiskHealthContext"),
    ("lotus-risk", "RegimeScenarioPackEvaluation"),
    ("lotus-manage", "PortfolioActionRegister"),
    ("lotus-report", "ClientReportEvidencePack"),
}


def validate_consumer_dependency_semantics(
    dependency: dict[str, Any],
    dependency_id: str,
) -> list[str]:
    errors: list[str] = []
    if dependency.get("required_product_version") != "v1":
        errors.append(f"{dependency_id}: required_product_version must be v1")
    if dependency.get("consumption_mode") not in ALLOWED_CONSUMPTION_MODES:
        errors.append(f"{dependency_id}: consumption_mode is invalid")

    trust_metadata = dependency.get("required_trust_metadata")
    if not isinstance(trust_metadata, list):
        errors.append(f"{dependency_id}: required_trust_metadata must be a list")
        return errors

    metadata = set(trust_metadata)
    missing_metadata = sorted(REQUIRED_CONSUMER_TRUST_METADATA - metadata)
    if missing_metadata:
        errors.append(
            f"{dependency_id}: required_trust_metadata missing {', '.join(missing_metadata)}"
        )
    if not FRESHNESS_METADATA & metadata:
        errors.append(f"{dependency_id}: required_trust_metadata must include freshness metadata")
    if _provenance_required(dependency) and not PROVENANCE_METADATA & metadata:
        errors.append(f"{dependency_id}: required_trust_metadata must include provenance metadata")
    return errors


def _provenance_required(dependency: dict[str, Any]) -> bool:
    return (
        str(dependency.get("producer_repository", "")),
        str(dependency.get("product_name", "")),
    ) in PROVENANCE_REQUIRED_PRODUCTS
