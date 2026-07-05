from __future__ import annotations

from typing import Any


REQUIRED_PRODUCER_TRUST_METADATA = {
    "product_name",
    "product_version",
    "tenant_id",
    "generated_at",
    "as_of_date",
    "reconciliation_status",
    "data_quality_status",
    "lineage_bundle_id",
    "source_batch_fingerprint",
    "correlation_id",
}

ALLOWED_FRESHNESS_CLASSES = {"daily", "intraday", "event_driven"}
ALLOWED_COMPLETENESS_STATUSES = {"complete", "partial"}
ALLOWED_FRESHNESS_BASES = {"as_of_date", "event_time"}


def validate_producer_product_semantics(
    product: dict[str, Any],
    product_id: str,
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_request_scope(product, product_id))
    errors.extend(_validate_temporal_scope(product, product_id))
    errors.extend(_validate_identifier_refs(product, product_id))
    errors.extend(_validate_trust_metadata(product, product_id))
    errors.extend(_validate_freshness_policy(product, product_id))
    errors.extend(_validate_completeness_policy(product, product_id))
    errors.extend(_validate_lineage_policy(product, product_id))
    errors.extend(_validate_security_and_lifecycle_policy(product, product_id))
    return errors


def _validate_request_scope(product: dict[str, Any], product_id: str) -> list[str]:
    request_scope = product.get("request_scope")
    if not isinstance(request_scope, dict):
        return [f"{product_id}: request_scope is required"]

    errors: list[str] = []
    if not str(request_scope.get("scope_level", "")).strip():
        errors.append(f"{product_id}: request_scope.scope_level is required")
    if not isinstance(request_scope.get("supports_bulk"), bool):
        errors.append(f"{product_id}: request_scope.supports_bulk must be boolean")
    return errors


def _validate_temporal_scope(product: dict[str, Any], product_id: str) -> list[str]:
    temporal_scope = product.get("temporal_scope")
    if not isinstance(temporal_scope, dict):
        return [f"{product_id}: temporal_scope is required"]

    errors: list[str] = []
    primary_time_field = str(temporal_scope.get("primary_time_field", ""))
    temporal_semantics_ref = str(product.get("temporal_semantics_ref", ""))
    if not primary_time_field:
        errors.append(f"{product_id}: temporal_scope.primary_time_field is required")
    elif primary_time_field != temporal_semantics_ref:
        errors.append(f"{product_id}: temporal_semantics_ref must match primary_time_field")
    if temporal_scope.get("freshness_basis") not in ALLOWED_FRESHNESS_BASES:
        errors.append(f"{product_id}: temporal_scope.freshness_basis is invalid")
    if temporal_scope.get("supports_restatement") is not True:
        errors.append(f"{product_id}: temporal_scope.supports_restatement must be true")
    return errors


def _validate_identifier_refs(product: dict[str, Any], product_id: str) -> list[str]:
    identifier_refs = product.get("identifier_refs")
    if not isinstance(identifier_refs, list) or not {"tenant_id", "correlation_id"} <= set(
        identifier_refs
    ):
        return [f"{product_id}: identifier_refs must include tenant_id and correlation_id"]
    return []


def _validate_trust_metadata(product: dict[str, Any], product_id: str) -> list[str]:
    trust_metadata = product.get("required_trust_metadata")
    if not isinstance(trust_metadata, list):
        return [f"{product_id}: required_trust_metadata must be a list"]

    missing_metadata = sorted(REQUIRED_PRODUCER_TRUST_METADATA - set(trust_metadata))
    if missing_metadata:
        return [f"{product_id}: required_trust_metadata missing {', '.join(missing_metadata)}"]
    return []


def _validate_freshness_policy(product: dict[str, Any], product_id: str) -> list[str]:
    freshness_policy = product.get("freshness_policy")
    if not isinstance(freshness_policy, dict):
        return [f"{product_id}: freshness_policy is required"]

    errors: list[str] = []
    if freshness_policy.get("freshness_class") not in ALLOWED_FRESHNESS_CLASSES:
        errors.append(f"{product_id}: freshness_policy.freshness_class is invalid")
    if not str(freshness_policy.get("max_allowed_age_description", "")).strip():
        errors.append(f"{product_id}: freshness_policy.max_allowed_age_description is required")
    return errors


def _validate_completeness_policy(product: dict[str, Any], product_id: str) -> list[str]:
    completeness_policy = product.get("completeness_policy")
    if not isinstance(completeness_policy, dict):
        return [f"{product_id}: completeness_policy is required"]

    errors: list[str] = []
    if completeness_policy.get("default_status") not in ALLOWED_COMPLETENESS_STATUSES:
        errors.append(f"{product_id}: completeness_policy.default_status is invalid")
    if not isinstance(completeness_policy.get("partial_allowed"), bool):
        errors.append(f"{product_id}: completeness_policy.partial_allowed must be boolean")
    return errors


def _validate_lineage_policy(product: dict[str, Any], product_id: str) -> list[str]:
    lineage_policy = product.get("lineage_policy")
    if not isinstance(lineage_policy, dict):
        return [f"{product_id}: lineage_policy is required"]

    errors: list[str] = []
    if lineage_policy.get("lineage_required") is not True:
        errors.append(f"{product_id}: lineage_required must be true")
    if lineage_policy.get("evidence_bundle_required") is not True:
        errors.append(f"{product_id}: evidence_bundle_required must be true")
    if not str(lineage_policy.get("lineage_bundle_class_ref", "")).strip():
        errors.append(f"{product_id}: lineage_bundle_class_ref is required")
    if not str(lineage_policy.get("evidence_access_class_ref", "")).strip():
        errors.append(f"{product_id}: evidence_access_class_ref is required")
    return errors


def _validate_security_and_lifecycle_policy(
    product: dict[str, Any],
    product_id: str,
) -> list[str]:
    errors: list[str] = []
    if "client_confidential" not in str(product.get("security_profile_ref", "")):
        errors.append(f"{product_id}: security_profile_ref must retain client_confidential")

    deprecation_policy = product.get("deprecation_policy")
    if not isinstance(deprecation_policy, dict):
        errors.append(f"{product_id}: deprecation_policy is required")
    elif deprecation_policy.get("state") != "not_deprecated":
        errors.append(f"{product_id}: deprecation_policy.state must be not_deprecated")
    return errors
