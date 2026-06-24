from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any


PLATFORM_MESH_ONBOARDING_PROOF_ENV = "LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF"
PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION = "lotus-idea.platform-mesh-onboarding-proof.v1"

PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED = (
    "platform_source_manifest_inclusion_missing",
    "platform_catalog_inclusion_missing",
)

REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS = (
    "data_mesh_not_certified",
    "producer_products_not_active",
    "certified_runtime_trust_telemetry_missing",
    "mesh_slo_policy_certification_missing",
    "mesh_access_policy_certification_missing",
    "mesh_evidence_policy_certification_missing",
    "gateway_workbench_discovery_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_PLATFORM_MESH_EVIDENCE_REFS = (
    "../lotus-platform/platform-contracts/domain-data-products/domain-product-source-manifest.v1.json",
    "../lotus-platform/generated/domain-product-catalog.json",
    "../lotus-platform/generated/domain-product-dependency-graph.json",
    "../lotus-platform/generated/enterprise-mesh-maturity-matrix.json",
    "../lotus-platform/docs/operations/enterprise-mesh-completion-handoff.md",
    "contracts/domain-data-products/lotus-idea-products.v1.json",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "contracts/domain-data-products/mesh-readiness.v1.json",
    "GET /api/v1/data-mesh/readiness",
    "GET /api/v1/implementation-proof/readiness",
)

REQUIRED_PRODUCER_PRODUCTS = (
    "lotus-idea:AdvisorOpportunityQueue:v1",
    "lotus-idea:IdeaCandidate:v1",
    "lotus-idea:IdeaConversionIntent:v1",
    "lotus-idea:IdeaConversionOutcome:v1",
    "lotus-idea:IdeaEvidencePacket:v1",
    "lotus-idea:IdeaFeedbackEvent:v1",
    "lotus-idea:IdeaReviewDecision:v1",
    "lotus-idea:IdeaTrustTelemetry:v1",
    "lotus-idea:OpportunitySignalCandidate:v1",
)

REQUIRED_CONSUMER_DEPENDENCIES = (
    "lotus-advise:AdvisoryCopilotInteractionRecord:v1",
    "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
    "lotus-advise:AdvisoryProposalLifecycleRecord:v1",
    "lotus-core:BenchmarkAssignment:v1",
    "lotus-core:HoldingsAsOf:v1",
    "lotus-core:PortfolioCashMovementSummary:v1",
    "lotus-core:PortfolioCashflowProjection:v1",
    "lotus-core:PortfolioStateSnapshot:v1",
    "lotus-manage:PortfolioActionRegister:v1",
    "lotus-performance:BenchmarkExposureContext:v1",
    "lotus-performance:MandatePerformanceHealthContext:v1",
    "lotus-performance:ReturnsSeriesBundle:v1",
    "lotus-report:ClientReportEvidencePack:v1",
    "lotus-risk:MandateRiskHealthContext:v1",
    "lotus-risk:RegimeScenarioPackEvaluation:v1",
    "lotus-risk:RiskMetricsReport:v1",
)


def build_platform_mesh_onboarding_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    platform_root: Path | None = None,
) -> dict[str, Any]:
    platform_root = platform_root or repository_root.parent / "lotus-platform"
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    source_manifest = _optional_json(
        platform_root
        / "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
    )
    catalog = _optional_json(platform_root / "generated/domain-product-catalog.json")
    maturity_matrix = _optional_json(
        platform_root / "generated/enterprise-mesh-maturity-matrix.json"
    )
    evidence_refs = tuple(REQUIRED_PLATFORM_MESH_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        platform_root=platform_root,
        evidence_refs=evidence_refs,
    )
    platform_source_manifest_includes_idea = _source_manifest_includes_idea(source_manifest)
    platform_catalog_includes_idea_products = _catalog_includes_idea_products(catalog)
    platform_catalog_includes_idea_consumer = _catalog_includes_idea_consumer(catalog)
    platform_maturity_keeps_idea_deferred = _maturity_matrix_keeps_idea_deferred(maturity_matrix)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and platform_source_manifest_includes_idea
        and platform_catalog_includes_idea_products
        and platform_catalog_includes_idea_consumer
        and platform_maturity_keeps_idea_deferred
    )
    return {
        "schemaVersion": PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "platform_mesh_onboarding_contract",
        "proofScope": "platform_source_manifest_and_catalog_inclusion",
        "platformMeshOnboardingProofValid": proof_valid,
        "aggregateBlockersCleared": PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "producerProductCount": len(REQUIRED_PRODUCER_PRODUCTS),
        "consumerDependencyCount": len(REQUIRED_CONSUMER_DEPENDENCIES),
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "platformSourceManifestIncludesIdea": platform_source_manifest_includes_idea,
            "platformCatalogIncludesIdeaProducts": platform_catalog_includes_idea_products,
            "platformCatalogIncludesIdeaConsumer": platform_catalog_includes_idea_consumer,
            "platformMaturityKeepsIdeaDeferred": platform_maturity_keeps_idea_deferred,
        },
        "remainingCertificationBlockers": REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS,
        "platformMeshCertified": False,
        "producerProductsActive": False,
        "gatewayWorkbenchDiscoveryCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def platform_mesh_onboarding_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "platform_mesh_onboarding_contract":
        return False
    if payload.get("proofScope") != "platform_source_manifest_and_catalog_inclusion":
        return False
    if payload.get("platformMeshOnboardingProofValid") is not True:
        return False
    if payload.get("platformMeshCertified") is not False:
        return False
    if payload.get("producerProductsActive") is not False:
        return False
    if payload.get("gatewayWorkbenchDiscoveryCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_PLATFORM_MESH_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS
    ):
        return False
    if payload.get("producerProductCount") != len(REQUIRED_PRODUCER_PRODUCTS):
        return False
    if payload.get("consumerDependencyCount") != len(REQUIRED_CONSUMER_DEPENDENCIES):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "platformSourceManifestIncludesIdea",
            "platformCatalogIncludesIdeaProducts",
            "platformCatalogIncludesIdeaConsumer",
            "platformMaturityKeepsIdeaDeferred",
        )
    )


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _source_manifest_includes_idea(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    for entry in payload.get("repositories", ()):
        if not isinstance(entry, Mapping) or entry.get("repository") != "lotus-idea":
            continue
        return (
            entry.get("source_mode") == "repo_native"
            and entry.get("catalog_inclusion") == "included"
            and entry.get("repo_native_status") == "implemented"
            and entry.get("repo_native_declaration_path") == "contracts/domain-data-products"
            and entry.get("platform_declaration_paths") == []
        )
    return False


def _catalog_includes_idea_products(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    products = payload.get("products")
    if not isinstance(products, list):
        return False
    by_product_id = {
        product.get("product_id"): product for product in products if isinstance(product, Mapping)
    }
    for product_id in REQUIRED_PRODUCER_PRODUCTS:
        product = by_product_id.get(product_id)
        if not isinstance(product, Mapping):
            return False
        if product.get("producer_repository") != "lotus-idea":
            return False
        if product.get("lifecycle_status") != "proposed":
            return False
        if product.get("current_routes") not in ([], None):
            return False
    return True


def _catalog_includes_idea_consumer(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    for consumer in payload.get("consumers", ()):
        if not isinstance(consumer, Mapping) or consumer.get("consumer_repository") != "lotus-idea":
            continue
        dependency_ids = {
            dependency.get("dependency_id")
            for dependency in consumer.get("dependencies", ())
            if isinstance(dependency, Mapping)
        }
        return set(REQUIRED_CONSUMER_DEPENDENCIES) <= dependency_ids
    return False


def _maturity_matrix_keeps_idea_deferred(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    repositories = {
        entry.get("repository"): entry
        for entry in payload.get("repositories", ())
        if isinstance(entry, Mapping)
    }
    idea_repository = repositories.get("lotus-idea")
    if not isinstance(idea_repository, Mapping):
        return False
    if idea_repository.get("classification") != "deferred":
        return False
    if idea_repository.get("mesh_role") != "producer":
        return False
    product_entries = {
        product.get("product_id"): product
        for product in payload.get("products", ())
        if isinstance(product, Mapping)
    }
    for product_id in REQUIRED_PRODUCER_PRODUCTS:
        product = product_entries.get(product_id)
        if not isinstance(product, Mapping):
            return False
        if product.get("classification") != "deferred":
            return False
        if product.get("maturity_wave") != "future_wave":
            return False
        if product.get("lifecycle_status") != "proposed":
            return False
    return True


def _required_file_evidence_present(
    *,
    repository_root: Path,
    platform_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(("GET ", "POST ", "make ")):
            continue
        if ref.startswith("../lotus-platform/"):
            path = platform_root / ref.removeprefix("../lotus-platform/")
        else:
            path = repository_root / ref
        if not path.is_file():
            return False
    return True


def _is_timezone_aware_datetime_text(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None
