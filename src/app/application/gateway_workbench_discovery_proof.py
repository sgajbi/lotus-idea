from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.application.gateway_workbench_operational_proof import (
    gateway_workbench_operational_proof_is_valid,
)
from app.application.platform_mesh_onboarding_proof import (
    REQUIRED_PRODUCER_PRODUCTS,
    platform_mesh_onboarding_proof_is_valid,
)
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.application.workbench_read_path_proof import workbench_read_path_proof_is_valid


_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text
_required_make_target_evidence_present = required_make_target_evidence_present

GATEWAY_WORKBENCH_DISCOVERY_PROOF_ENV = "LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF"
GATEWAY_WORKBENCH_DISCOVERY_PROOF_SCHEMA_VERSION = "lotus-idea.gateway-workbench-discovery-proof.v1"

GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS_CLEARED = ("gateway_workbench_discovery_proof_missing",)

REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS = (
    "contracts/domain-data-products/lotus-idea-products.v1.json",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "contracts/domain-data-products/mesh-readiness.v1.json",
    "src/app/application/platform_mesh_onboarding_proof.py",
    "src/app/application/workbench_read_path_proof.py",
    "src/app/application/gateway_workbench_operational_proof.py",
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Supported-Features.md",
    "make data-mesh-contract-gate",
    "make platform-mesh-onboarding-proof-contract-gate",
    "make workbench-read-path-proof-contract-gate",
    "make gateway-workbench-operational-proof-contract-gate",
    "make gateway-workbench-discovery-proof-contract-gate",
    "make implementation-proof-readiness-check",
)

REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS = (
    "../lotus-platform/generated/domain-product-catalog.json",
    "../lotus-platform/generated/domain-product-dependency-graph.json",
)

REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS = (
    "data_mesh_not_certified",
    "producer_products_not_active",
    "platform_mesh_certification_missing",
    "workbench_product_proof_missing",
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "supported_feature_promotion_missing",
)


def build_gateway_workbench_discovery_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    platform_root: Path | None = None,
    platform_mesh_onboarding_proof: Mapping[str, Any] | None,
    workbench_read_path_proof: Mapping[str, Any] | None,
    gateway_workbench_operational_proof: Mapping[str, Any] | None,
    platform_mesh_onboarding_proof_ref: str | None,
    workbench_read_path_proof_ref: str | None,
    gateway_workbench_operational_proof_ref: str | None,
) -> dict[str, Any]:
    platform_root = platform_root or repository_root.parent / "lotus-platform"
    catalog = _optional_json(platform_root / "generated/domain-product-catalog.json")
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        platform_root=platform_root,
    )
    platform_onboarding_valid = bool(
        platform_mesh_onboarding_proof
        and platform_mesh_onboarding_proof_is_valid(platform_mesh_onboarding_proof)
    )
    workbench_read_path_valid = bool(
        workbench_read_path_proof and workbench_read_path_proof_is_valid(workbench_read_path_proof)
    )
    gateway_operational_valid = bool(
        gateway_workbench_operational_proof
        and gateway_workbench_operational_proof_is_valid(gateway_workbench_operational_proof)
    )
    catalog_exposes_gateway_visible_products = _catalog_exposes_gateway_visible_idea_products(
        catalog
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and platform_onboarding_valid
        and workbench_read_path_valid
        and gateway_operational_valid
        and catalog_exposes_gateway_visible_products
    )
    return {
        "schemaVersion": GATEWAY_WORKBENCH_DISCOVERY_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "gateway_workbench_discovery_contract",
        "proofScope": "source_safe_catalog_visibility_and_read_path_discovery",
        "gatewayWorkbenchDiscoveryProofValid": proof_valid,
        "aggregateBlockersCleared": GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS_CLEARED,
        "platformMeshOnboardingProofRef": platform_mesh_onboarding_proof_ref,
        "workbenchReadPathProofRef": workbench_read_path_proof_ref,
        "gatewayWorkbenchOperationalProofRef": gateway_workbench_operational_proof_ref,
        "localEvidenceRefs": REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS,
        "platformEvidenceRefs": REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS,
        "discoveredProductCount": len(REQUIRED_PRODUCER_PRODUCTS),
        "approvedConsumer": "lotus-gateway",
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "platformMeshOnboardingProofValid": platform_onboarding_valid,
            "workbenchReadPathProofValid": workbench_read_path_valid,
            "gatewayWorkbenchOperationalProofValid": gateway_operational_valid,
            "catalogExposesGatewayVisibleIdeaProducts": (catalog_exposes_gateway_visible_products),
            "productsRemainProposed": True,
            "routesRemainUnpublished": True,
        },
        "remainingCertificationBlockers": REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS,
        "dataMeshCertified": False,
        "producerProductsActive": False,
        "fullWorkbenchProductCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def gateway_workbench_discovery_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != GATEWAY_WORKBENCH_DISCOVERY_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "gateway_workbench_discovery_contract":
        return False
    if payload.get("proofScope") != "source_safe_catalog_visibility_and_read_path_discovery":
        return False
    if payload.get("gatewayWorkbenchDiscoveryProofValid") is not True:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("localEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("platformEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS
    ):
        return False
    if payload.get("discoveredProductCount") != len(REQUIRED_PRODUCER_PRODUCTS):
        return False
    if payload.get("approvedConsumer") != "lotus-gateway":
        return False
    if payload.get("dataMeshCertified") is not False:
        return False
    if payload.get("producerProductsActive") is not False:
        return False
    if payload.get("fullWorkbenchProductCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    for ref_field in (
        "platformMeshOnboardingProofRef",
        "workbenchReadPathProofRef",
        "gatewayWorkbenchOperationalProofRef",
    ):
        if not isinstance(payload.get(ref_field), str):
            return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "platformMeshOnboardingProofValid",
            "workbenchReadPathProofValid",
            "gatewayWorkbenchOperationalProofValid",
            "catalogExposesGatewayVisibleIdeaProducts",
            "productsRemainProposed",
            "routesRemainUnpublished",
        )
    )


def _catalog_exposes_gateway_visible_idea_products(payload: dict[str, Any] | None) -> bool:
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
        consumers = product.get("approved_consumers")
        if not isinstance(consumers, list) or "lotus-gateway" not in consumers:
            return False
        if product.get("current_routes") != []:
            return False
    return True


def _required_file_evidence_present(
    *,
    repository_root: Path,
    platform_root: Path,
) -> bool:
    evidence_refs = (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS
        + REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS
    )
    return required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={"../lotus-platform/": platform_root},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("GET ", "POST ", "make "),
    ) and _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS,
    )


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None
