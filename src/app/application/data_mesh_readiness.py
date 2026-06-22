from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCER_DECLARATION_PATH = Path("contracts/domain-data-products/lotus-idea-products.v1.json")
MESH_READINESS_PATH = Path("contracts/domain-data-products/mesh-readiness.v1.json")
TRUST_TELEMETRY_PATH = Path("contracts/trust-telemetry/idea-candidate.telemetry.v1.json")


@dataclass(frozen=True)
class DataMeshProductReadiness:
    product_id: str
    lifecycle_status: str
    approved_consumers: tuple[str, ...]


@dataclass(frozen=True)
class DataMeshReadinessSnapshot:
    repository: str
    lifecycle_status: str
    certification_status: str
    mesh_role: str
    source_of_truth: MappingProxyType[str, str]
    products: tuple[DataMeshProductReadiness, ...]
    blockers: tuple[str, ...]
    certification_gates_before_promotion: tuple[str, ...]
    runtime_telemetry_backed: bool
    platform_certified: bool
    supported_feature_promoted: bool


def build_data_mesh_readiness_snapshot(
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> DataMeshReadinessSnapshot:
    producer = _read_json(repository_root / PRODUCER_DECLARATION_PATH)
    readiness = _read_json(repository_root / MESH_READINESS_PATH)
    telemetry = _read_json(repository_root / TRUST_TELEMETRY_PATH)

    products = tuple(_product_readiness(product) for product in _objects(producer, "products"))
    certification_status = str(readiness.get("certification_status", "unknown"))
    telemetry_blocking = telemetry.get("blocking")
    blockers = _readiness_blockers(
        certification_status=certification_status,
        product_statuses=tuple(product.lifecycle_status for product in products),
        telemetry_blocking=telemetry_blocking if isinstance(telemetry_blocking, dict) else {},
    )

    source_of_truth = readiness.get("source_of_truth")
    if not isinstance(source_of_truth, dict):
        raise ValueError("mesh readiness source_of_truth must be an object")

    return DataMeshReadinessSnapshot(
        repository=str(readiness.get("repository", "lotus-idea")),
        lifecycle_status=str(readiness.get("lifecycle_status", "unknown")),
        certification_status=certification_status,
        mesh_role=str(readiness.get("mesh_role", "unknown")),
        source_of_truth=MappingProxyType(
            {str(key): str(value) for key, value in source_of_truth.items()}
        ),
        products=products,
        blockers=blockers,
        certification_gates_before_promotion=tuple(
            str(gate) for gate in readiness.get("certification_gates_before_promotion", ())
        ),
        runtime_telemetry_backed=not blockers,
        platform_certified=certification_status == "certified",
        supported_feature_promoted=False,
    )


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _objects(payload: dict[str, Any], key: str) -> tuple[dict[str, Any], ...]:
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError(f"{key} must be a list")
    return tuple(value for value in values if isinstance(value, dict))


def _product_readiness(product: dict[str, Any]) -> DataMeshProductReadiness:
    product_name = str(product.get("product_name", "unknown"))
    product_version = str(product.get("product_version", "unknown"))
    consumers = product.get("approved_consumers")
    approved_consumers = (
        tuple(str(consumer) for consumer in consumers) if isinstance(consumers, list) else ()
    )
    return DataMeshProductReadiness(
        product_id=f"lotus-idea:{product_name}:{product_version}",
        lifecycle_status=str(product.get("lifecycle_status", "unknown")),
        approved_consumers=approved_consumers,
    )


def _readiness_blockers(
    *,
    certification_status: str,
    product_statuses: tuple[str, ...],
    telemetry_blocking: dict[str, Any],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if certification_status != "certified":
        blockers.append("data_mesh_not_certified")
    if any(status != "active" for status in product_statuses):
        blockers.append("producer_products_not_active")
    if telemetry_blocking.get("blocked") is True:
        blockers.append("certified_runtime_trust_telemetry_missing")
    return tuple(blockers)
