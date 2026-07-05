from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from data_mesh_producer_semantics import validate_producer_product_semantics


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM_CATALOG_PATH = (
    ROOT.parent / "lotus-platform" / "generated" / "domain-product-catalog.json"
)
DEFAULT_PLATFORM_SOURCE_MANIFEST_PATH = (
    ROOT.parent
    / "lotus-platform"
    / "platform-contracts"
    / "domain-data-products"
    / "domain-product-source-manifest.v1.json"
)

PRODUCER_DECLARATION_PATH = Path("contracts/domain-data-products/lotus-idea-products.v1.json")
CONSUMER_DECLARATION_PATH = Path("contracts/domain-data-products/lotus-idea-consumers.v1.json")
MESH_READINESS_PATH = Path("contracts/domain-data-products/mesh-readiness.v1.json")
TRUST_TELEMETRY_PATH = Path("contracts/trust-telemetry/idea-candidate.telemetry.v1.json")
SLO_POLICY_PATH = Path("contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json")
ACCESS_POLICY_PATH = Path("contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json")
EVIDENCE_POLICY_PATH = Path(
    "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json"
)

REQUIRED_PRODUCTS = {
    "OpportunitySignalCandidate",
    "IdeaCandidate",
    "IdeaEvidencePacket",
    "AdvisorOpportunityQueue",
    "IdeaReviewDecision",
    "IdeaFeedbackEvent",
    "IdeaConversionIntent",
    "IdeaConversionOutcome",
    "IdeaTrustTelemetry",
}

REQUIRED_DEPENDENCIES = {
    ("lotus-core", "PortfolioStateSnapshot", "v1"),
    ("lotus-core", "HoldingsAsOf", "v1"),
    ("lotus-core", "PortfolioCashMovementSummary", "v1"),
    ("lotus-core", "PortfolioCashflowProjection", "v1"),
    ("lotus-core", "BenchmarkAssignment", "v1"),
    ("lotus-performance", "ReturnsSeriesBundle", "v1"),
    ("lotus-performance", "BenchmarkExposureContext", "v1"),
    ("lotus-performance", "MandatePerformanceHealthContext", "v1"),
    ("lotus-risk", "RiskMetricsReport", "v1"),
    ("lotus-risk", "ConcentrationRiskReport", "v1"),
    ("lotus-risk", "MandateRiskHealthContext", "v1"),
    ("lotus-risk", "RegimeScenarioPackEvaluation", "v1"),
    ("lotus-advise", "AdvisoryProposalLifecycleRecord", "v1"),
    ("lotus-advise", "AdvisoryPolicyEvaluationRecord", "v1"),
    ("lotus-advise", "AdvisoryCopilotInteractionRecord", "v1"),
    ("lotus-manage", "PortfolioActionRegister", "v1"),
    ("lotus-report", "ClientReportEvidencePack", "v1"),
}

ALLOWED_SOURCE_REPOSITORIES = {
    "lotus-core",
    "lotus-performance",
    "lotus-risk",
    "lotus-advise",
    "lotus-manage",
    "lotus-report",
}

ALLOWED_FAILURE_POSTURES = {"fail_closed", "degrade_to_partial", "support_only"}
REQUIRED_VALIDATION_LANES = {"feature", "pr-merge"}
CERTIFICATION_BLOCKERS = (
    "implementation",
    "source manifest",
    "runtime telemetry",
    "platform certification",
)


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((ROOT / path).read_text(encoding="utf-8")))


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _validate_no_placeholders() -> list[str]:
    errors: list[str] = []
    for base_path in (ROOT / "contracts", ROOT / "docs" / "operations"):
        for path in base_path.rglob("*placeholder*"):
            if path.is_file():
                errors.append(f"Placeholder file is not allowed in governed mesh paths: {path}")
    return errors


def validate_producer_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("contract_id") != "domain-data-products":
        errors.append("producer declaration contract_id must be `domain-data-products`")
    if payload.get("producer_repository") != "lotus-idea":
        errors.append("producer declaration producer_repository must be `lotus-idea`")
    if payload.get("authoritative_domain") != "opportunity_intelligence":
        errors.append(
            "producer declaration authoritative_domain must be `opportunity_intelligence`"
        )

    products = payload.get("products")
    if not isinstance(products, list) or not products:
        return [*errors, "producer declaration products must be a non-empty list"]

    product_names = {
        str(product.get("product_name")) for product in products if isinstance(product, dict)
    }
    missing_products = sorted(REQUIRED_PRODUCTS - product_names)
    if missing_products:
        errors.append(f"producer declaration missing products: {', '.join(missing_products)}")

    seen_product_ids: set[str] = set()
    for index, product in enumerate(products):
        if not isinstance(product, dict):
            errors.append(f"products[{index}] must be an object")
            continue
        product_name = str(product.get("product_name", ""))
        product_version = str(product.get("product_version", ""))
        product_id = f"lotus-idea:{product_name}:{product_version}"
        if product_id in seen_product_ids:
            errors.append(f"{product_id}: duplicate producer product")
        seen_product_ids.add(product_id)

        if product_version != "v1":
            errors.append(f"{product_id}: product_version must be v1")
        if product.get("owner_repository") != "lotus-idea":
            errors.append(f"{product_id}: owner_repository must be lotus-idea")
        if product.get("lifecycle_status") != "proposed":
            errors.append(
                f"{product_id}: lifecycle_status must remain proposed before certification"
            )
        if product.get("authoritative_domain") != "opportunity_intelligence":
            errors.append(f"{product_id}: authoritative_domain must be opportunity_intelligence")
        if product.get("current_routes"):
            errors.append(
                f"{product_id}: current_routes must not exist before supported runtime APIs"
            )
        approved_consumers = product.get("approved_consumers")
        if not isinstance(approved_consumers, list) or "lotus-gateway" not in approved_consumers:
            errors.append(f"{product_id}: approved_consumers must include lotus-gateway")
        errors.extend(validate_producer_product_semantics(product, product_id))
    return errors


def validate_consumer_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("contract_id") != "domain-data-product-consumers":
        errors.append("consumer declaration contract_id must be `domain-data-product-consumers`")
    if payload.get("consumer_repository") != "lotus-idea":
        errors.append("consumer declaration consumer_repository must be `lotus-idea`")

    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        return [*errors, "consumer declaration dependencies must be a non-empty list"]

    declared_dependencies: set[tuple[str, str, str]] = set()
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            errors.append(f"dependencies[{index}] must be an object")
            continue
        producer = str(dependency.get("producer_repository", ""))
        product_name = str(dependency.get("product_name", ""))
        product_version = str(dependency.get("required_product_version", ""))
        dependency_id = (producer, product_name, product_version)
        if dependency_id in declared_dependencies:
            errors.append(f"{producer}:{product_name}:{product_version}: duplicate dependency")
        declared_dependencies.add(dependency_id)

        if producer not in ALLOWED_SOURCE_REPOSITORIES:
            errors.append(
                f"{producer}:{product_name}:{product_version}: unsupported source repository"
            )
        if producer == "lotus-idea":
            errors.append(
                f"{producer}:{product_name}:{product_version}: self-owned source dependency"
            )
        if dependency.get("migration_posture", {}).get("status") != "current":
            errors.append(
                f"{producer}:{product_name}:{product_version}: migration status must be current"
            )
        validation_lanes = dependency.get("validation_lanes")
        if not isinstance(validation_lanes, list) or not REQUIRED_VALIDATION_LANES <= set(
            validation_lanes
        ):
            errors.append(
                f"{producer}:{product_name}:{product_version}: validation_lanes must include "
                "feature and pr-merge"
            )
        failure_posture = dependency.get("failure_posture")
        if failure_posture not in ALLOWED_FAILURE_POSTURES:
            errors.append(
                f"{producer}:{product_name}:{product_version}: invalid failure_posture "
                f"{failure_posture!r}"
            )
        required_trust_metadata = dependency.get("required_trust_metadata")
        if (
            not isinstance(required_trust_metadata, list)
            or "correlation_id" not in required_trust_metadata
        ):
            errors.append(
                f"{producer}:{product_name}:{product_version}: required_trust_metadata must include "
                "correlation_id"
            )
        if not str(dependency.get("business_purpose", "")).strip():
            errors.append(
                f"{producer}:{product_name}:{product_version}: business_purpose is required"
            )

    missing_dependencies = sorted(REQUIRED_DEPENDENCIES - declared_dependencies)
    if missing_dependencies:
        missing = ", ".join(
            f"{repo}:{name}:{version}" for repo, name, version in missing_dependencies
        )
        errors.append(f"consumer declaration missing dependencies: {missing}")
    return errors


def validate_mesh_readiness(
    readiness: dict[str, Any],
    telemetry: dict[str, Any],
    slo: dict[str, Any],
    access: dict[str, Any],
    evidence: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if readiness.get("repository") != "lotus-idea":
        errors.append("mesh readiness repository must be lotus-idea")
    if readiness.get("lifecycle_status") != "planned":
        errors.append("mesh readiness lifecycle_status must remain planned")
    if readiness.get("certification_status") != "not_certified":
        errors.append("mesh readiness certification_status must remain not_certified")

    source_of_truth = readiness.get("source_of_truth")
    if not isinstance(source_of_truth, dict):
        errors.append("mesh readiness source_of_truth is required")
    else:
        expected_paths = {
            "producer_declaration": PRODUCER_DECLARATION_PATH.as_posix(),
            "consumer_declaration": CONSUMER_DECLARATION_PATH.as_posix(),
            "trust_telemetry": TRUST_TELEMETRY_PATH.as_posix(),
            "slo_policy": SLO_POLICY_PATH.as_posix(),
            "access_policy": ACCESS_POLICY_PATH.as_posix(),
            "evidence_policy": EVIDENCE_POLICY_PATH.as_posix(),
        }
        for field, expected_path in expected_paths.items():
            if source_of_truth.get(field) != expected_path:
                errors.append(f"mesh readiness source_of_truth.{field} must be {expected_path}")

    if telemetry.get("product_id") != "lotus-idea:IdeaCandidate:v1":
        errors.append("trust telemetry product_id must be lotus-idea:IdeaCandidate:v1")
    if telemetry.get("producer_repository") != "lotus-idea":
        errors.append("trust telemetry producer_repository must be lotus-idea")
    if telemetry.get("freshness", {}).get("freshness_state") != "unknown":
        errors.append("trust telemetry freshness_state must remain unknown before runtime evidence")
    if telemetry.get("lineage", {}).get("lineage_materialized") is not False:
        errors.append("trust telemetry lineage must remain unmaterialized before runtime evidence")
    blocking = telemetry.get("blocking")
    if not isinstance(blocking, dict) or blocking.get("blocked") is not True:
        errors.append("trust telemetry must remain blocked before runtime certification")
    else:
        blocked_reason = str(blocking.get("blocked_reason", "")).lower()
        for blocker in CERTIFICATION_BLOCKERS:
            if blocker not in blocked_reason:
                errors.append(f"trust telemetry blocked_reason must mention {blocker}")
    if telemetry.get("observed_trust_metadata") not in ({}, None):
        errors.append("trust telemetry observed_trust_metadata must stay empty before runtime")

    policy_payloads = (slo, access, evidence)
    for payload in policy_payloads:
        if payload.get("product_id") != "lotus-idea:IdeaCandidate:v1":
            errors.append(f"{payload.get('contract_id')}: product_id must be IdeaCandidate v1")
        if payload.get("producer_repository") != "lotus-idea":
            errors.append(f"{payload.get('contract_id')}: producer_repository must be lotus-idea")

    if slo.get("lineage", {}).get("lineage_materialized_required") is not True:
        errors.append("mesh SLO policy must require materialized lineage")
    if access.get("default_posture") != "restricted":
        errors.append("mesh access policy default_posture must be restricted")
    allowed_consumers = access.get("allowed_consumers")
    if not isinstance(allowed_consumers, list) or not any(
        consumer.get("consumer_repository") == "lotus-gateway"
        for consumer in allowed_consumers
        if isinstance(consumer, dict)
    ):
        errors.append("mesh access policy must allow lotus-gateway only through governed policy")
    required_sections = evidence.get("required_manifest_sections")
    if not isinstance(required_sections, list) or "runtime_telemetry" not in required_sections:
        errors.append("mesh evidence policy must require runtime_telemetry")
    field_access_classes = evidence.get("field_access_classes")
    if not isinstance(field_access_classes, dict):
        errors.append("mesh evidence policy field_access_classes is required")
    elif field_access_classes.get("internal_debug") != "internal_only":
        errors.append("mesh evidence policy internal_debug must be internal_only")
    return errors


def validate_against_platform_catalog(
    consumer_payload: dict[str, Any],
    catalog_payload: dict[str, Any] | None,
) -> list[str]:
    if catalog_payload is None:
        return []
    products = catalog_payload.get("products")
    if not isinstance(products, list):
        return ["platform catalog products must be a list when catalog validation is enabled"]
    catalog_product_ids = {
        str(product.get("product_id")) for product in products if isinstance(product, dict)
    }
    errors: list[str] = []
    for dependency in consumer_payload.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        product_id = (
            f"{dependency.get('producer_repository')}:"
            f"{dependency.get('product_name')}:"
            f"{dependency.get('required_product_version')}"
        )
        if product_id not in catalog_product_ids:
            errors.append(f"{product_id}: dependency is absent from platform catalog")
    return errors


def validate_against_platform_source_manifest(
    readiness: dict[str, Any],
    source_manifest: dict[str, Any] | None,
) -> list[str]:
    if source_manifest is None:
        return []
    repositories = source_manifest.get("repositories")
    if not isinstance(repositories, list):
        return [
            "platform source manifest repositories must be a list when manifest validation is enabled"
        ]
    lotus_idea_entries = [
        repository
        for repository in repositories
        if isinstance(repository, dict) and repository.get("repository") == "lotus-idea"
    ]
    if not lotus_idea_entries:
        return []
    errors: list[str] = []
    for entry in lotus_idea_entries:
        if entry.get("source_mode") != "repo_native":
            errors.append("platform source manifest lotus-idea source_mode must be repo_native")
        if entry.get("catalog_inclusion") != "included":
            errors.append("platform source manifest lotus-idea catalog_inclusion must be included")
        if entry.get("repo_native_status") != "implemented":
            errors.append(
                "platform source manifest lotus-idea repo_native_status must be implemented"
            )
        if entry.get("repo_native_declaration_path") != "contracts/domain-data-products":
            errors.append(
                "platform source manifest lotus-idea repo_native_declaration_path must be "
                "contracts/domain-data-products"
            )
        if entry.get("platform_declaration_paths") != []:
            errors.append(
                "platform source manifest lotus-idea platform_declaration_paths must stay empty"
            )
    if readiness.get("certification_status") == "certified":
        errors.append("mesh readiness must not be certified from source-manifest inclusion alone")
    return errors


def validate_data_mesh_contracts(
    *,
    platform_catalog_path: Path | None = DEFAULT_PLATFORM_CATALOG_PATH,
    platform_source_manifest_path: Path | None = DEFAULT_PLATFORM_SOURCE_MANIFEST_PATH,
) -> list[str]:
    producer = _read_json(PRODUCER_DECLARATION_PATH)
    consumer = _read_json(CONSUMER_DECLARATION_PATH)
    readiness = _read_json(MESH_READINESS_PATH)
    telemetry = _read_json(TRUST_TELEMETRY_PATH)
    slo = _read_json(SLO_POLICY_PATH)
    access = _read_json(ACCESS_POLICY_PATH)
    evidence = _read_json(EVIDENCE_POLICY_PATH)
    platform_catalog = _optional_json(platform_catalog_path) if platform_catalog_path else None
    platform_source_manifest = (
        _optional_json(platform_source_manifest_path) if platform_source_manifest_path else None
    )

    return [
        *_validate_no_placeholders(),
        *validate_producer_contract(producer),
        *validate_consumer_contract(consumer),
        *validate_mesh_readiness(readiness, telemetry, slo, access, evidence),
        *validate_against_platform_catalog(consumer, platform_catalog),
        *validate_against_platform_source_manifest(readiness, platform_source_manifest),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate lotus-idea data-mesh contract posture.")
    parser.add_argument(
        "--platform-catalog",
        type=Path,
        default=DEFAULT_PLATFORM_CATALOG_PATH,
        help=(
            "Optional platform generated domain-product catalog. If the path exists, consumer "
            "dependencies are reconciled against it."
        ),
    )
    parser.add_argument(
        "--platform-source-manifest",
        type=Path,
        default=DEFAULT_PLATFORM_SOURCE_MANIFEST_PATH,
        help=(
            "Optional platform domain-product source manifest. If the path exists, premature "
            "lotus-idea source-manifest inclusion is blocked until certification."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_data_mesh_contracts(
        platform_catalog_path=args.platform_catalog,
        platform_source_manifest_path=args.platform_source_manifest,
    )
    if errors:
        print("\n".join(errors))
        return 1
    print("Data-mesh contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
