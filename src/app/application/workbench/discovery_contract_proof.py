from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.domain.proof_evidence import EvidenceClass
from app.application.workbench.contract_proof import (
    gateway_workbench_contract_proof_is_valid,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    REQUIRED_PRODUCER_PRODUCTS,
    platform_catalog_source_contract_is_valid,
)
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.application.workbench.read_path_source_contract import (
    workbench_read_path_source_contract_proof_is_valid,
)


_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text
_required_make_target_evidence_present = required_make_target_evidence_present

GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_ENV = (
    "LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF"
)
GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.gateway-workbench-discovery-contract-proof.v2"
)

GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED: tuple[str, ...] = ()

REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS = (
    "contracts/domain-data-products/lotus-idea-products.v1.json",
    "contracts/domain-data-products/lotus-idea-consumers.v1.json",
    "contracts/domain-data-products/mesh-readiness.v1.json",
    "src/app/application/data_mesh/platform_catalog_source_contract.py",
    "src/app/application/workbench/read_path_source_contract.py",
    "src/app/application/workbench/contract_proof.py",
    "src/app/application/workbench/discovery_contract_proof.py",
    "scripts/workbench/generate_discovery_contract_proof.py",
    "scripts/workbench/discovery_contract_proof_gate.py",
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Supported-Features.md",
    "make data-mesh-contract-gate",
    "make platform-catalog-source-contract-proof-gate",
    "make workbench-read-path-source-contract-proof-gate",
    "make gateway-workbench-contract-proof-contract-gate",
    "make gateway-workbench-discovery-contract-proof-contract-gate",
    "make implementation-proof-readiness-check",
)

REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS = (
    "../lotus-platform/generated/domain-product-catalog.json",
    "../lotus-platform/generated/domain-product-dependency-graph.json",
)

REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS = (
    "gateway_workbench_discovery_proof_missing",
    "data_mesh_not_certified",
    "producer_products_not_active",
    "platform_mesh_certification_missing",
    "workbench_product_proof_missing",
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "supported_feature_promotion_missing",
)


def build_gateway_workbench_discovery_contract_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    platform_root: Path | None = None,
    platform_catalog_source_contract: Mapping[str, Any] | None,
    workbench_read_path_source_contract_proof: Mapping[str, Any] | None,
    gateway_workbench_contract_proof: Mapping[str, Any] | None,
    platform_catalog_source_contract_ref: str | None,
    workbench_read_path_source_contract_proof_ref: str | None,
    gateway_workbench_contract_proof_ref: str | None,
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
    platform_catalog_source_contract_valid = bool(
        platform_catalog_source_contract
        and platform_catalog_source_contract_is_valid(platform_catalog_source_contract)
    )
    workbench_read_path_source_contract_valid = bool(
        workbench_read_path_source_contract_proof
        and workbench_read_path_source_contract_proof_is_valid(
            workbench_read_path_source_contract_proof
        )
    )
    gateway_contract_valid = bool(
        gateway_workbench_contract_proof
        and gateway_workbench_contract_proof_is_valid(gateway_workbench_contract_proof)
    )
    catalog_declares_gateway_consumable_products = (
        _catalog_declares_gateway_consumable_idea_products(catalog)
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and platform_catalog_source_contract_valid
        and workbench_read_path_source_contract_valid
        and gateway_contract_valid
        and catalog_declares_gateway_consumable_products
    )
    return {
        "schemaVersion": GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "gateway_workbench_discovery_contract",
        "proofScope": "source_catalog_and_consumer_declaration",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "gatewayWorkbenchDiscoveryContractProofValid": proof_valid,
        "aggregateBlockersCleared": GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED,
        "platformCatalogSourceContractRef": platform_catalog_source_contract_ref,
        "workbenchReadPathSourceContractProofRef": (workbench_read_path_source_contract_proof_ref),
        "gatewayWorkbenchContractProofRef": gateway_workbench_contract_proof_ref,
        "localEvidenceRefs": REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS,
        "platformEvidenceRefs": REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS,
        "declaredProductCount": len(REQUIRED_PRODUCER_PRODUCTS),
        "declaredConsumer": "lotus-gateway",
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "platformCatalogSourceContractValid": platform_catalog_source_contract_valid,
            "workbenchReadPathSourceContractProofValid": (
                workbench_read_path_source_contract_valid
            ),
            "gatewayWorkbenchContractProofValid": gateway_contract_valid,
            "catalogDeclaresGatewayConsumableIdeaProducts": (
                catalog_declares_gateway_consumable_products
            ),
            "productsRemainProposed": True,
            "routesRemainUnpublished": True,
        },
        "remainingCertificationBlockers": REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS,
        "dataMeshCertified": False,
        "producerProductsActive": False,
        "fullWorkbenchProductCertified": False,
        "gatewayWorkbenchDiscoveryCertified": False,
        "canonicalDemoRuntimeCertified": False,
        "runtimeExecutionObserved": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def gateway_workbench_discovery_contract_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "gateway_workbench_discovery_contract":
        return False
    if payload.get("proofScope") != "source_catalog_and_consumer_declaration":
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("gatewayWorkbenchDiscoveryContractProofValid") is not True:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    blockers_cleared = payload.get("aggregateBlockersCleared")
    if not isinstance(blockers_cleared, (list, tuple)):
        return False
    if tuple(blockers_cleared) != (GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED):
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
    if payload.get("declaredProductCount") != len(REQUIRED_PRODUCER_PRODUCTS):
        return False
    if payload.get("declaredConsumer") != "lotus-gateway":
        return False
    if payload.get("dataMeshCertified") is not False:
        return False
    if payload.get("producerProductsActive") is not False:
        return False
    if payload.get("fullWorkbenchProductCertified") is not False:
        return False
    if payload.get("gatewayWorkbenchDiscoveryCertified") is not False:
        return False
    if payload.get("canonicalDemoRuntimeCertified") is not False:
        return False
    if payload.get("runtimeExecutionObserved") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    for ref_field in (
        "platformCatalogSourceContractRef",
        "workbenchReadPathSourceContractProofRef",
        "gatewayWorkbenchContractProofRef",
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
            "platformCatalogSourceContractValid",
            "workbenchReadPathSourceContractProofValid",
            "gatewayWorkbenchContractProofValid",
            "catalogDeclaresGatewayConsumableIdeaProducts",
            "productsRemainProposed",
            "routesRemainUnpublished",
        )
    )


def _catalog_declares_gateway_consumable_idea_products(payload: dict[str, Any] | None) -> bool:
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
