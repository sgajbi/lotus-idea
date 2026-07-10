from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_FEATURES_PATH = ROOT / "supported-features" / "supported-features.json"
SUPPORTED_FEATURES_SCHEMA_PATH = ROOT / "supported-features" / "supported-features.schema.json"
ENDPOINT_CERTIFICATION_LEDGER_PATH = (
    ROOT / "docs" / "operations" / "endpoint-certification-ledger.json"
)

IMPLEMENTED_FEATURE_STATUS = "implemented"
NON_IMPLEMENTED_FEATURE_STATUSES = {"planned", "not_applicable"}
CURRENT_POLICY = "Only implementation-backed behavior may be promoted to supported."
FEATURE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TEST_REFERENCE_PATTERN = re.compile(r"^(?P<path>tests/.+\.py)::(?P<test>[A-Za-z_][A-Za-z0-9_]*)$")
PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:placeholder|todo|tbd|to be determined|coming soon|later|sample|string-only)\b",
    re.IGNORECASE,
)

PLANNED_CAPABILITY_REQUIRED_FIELDS = ("id", "name", "governing_rfc", "status")
IMPLEMENTED_FEATURE_REQUIRED_FIELDS = (
    "id",
    "name",
    "owner",
    "status",
    "governing_rfc",
    "support_scope",
    "unsupported_scope",
    "api_surfaces",
    "ui_surfaces",
    "source_dependencies",
    "consumer_publication_state",
    "gateway_workbench_state",
    "data_product_state",
    "promotion_evidence",
    "known_gaps",
    "last_reviewed_utc",
    "promotion_decision_ref",
)
PROMOTION_EVIDENCE_REQUIRED_FIELDS = (
    "code_modules",
    "api_contracts",
    "test_evidence",
    "runtime_evidence",
    "ci_evidence",
    "documentation",
    "runbooks",
    "proof_artifacts",
)
PROMOTION_REVIEW_MAX_AGE = timedelta(days=90)
SUPPORTED_FEATURE_REGISTRY_INVALID = "supported_feature_registry_invalid"
SUPPORTED_FEATURE_PROMOTION_EVIDENCE_STALE = "supported_feature_promotion_evidence_stale"
NO_SUPPORTED_FEATURES_PROMOTED = "no_supported_features_promoted"


@dataclass(frozen=True)
class SupportedFeaturePromotionEvaluation:
    promoted_feature_ids: tuple[str, ...]
    validation_errors: tuple[str, ...]
    blocker_codes: tuple[str, ...]
    source_ref: str = "supported-features/supported-features.json"

    @property
    def registry_valid(self) -> bool:
        return not self.validation_errors

    @property
    def promoted_feature_count(self) -> int:
        return len(self.promoted_feature_ids)

    @property
    def supported_features_promoted(self) -> bool:
        return self.registry_valid and bool(self.promoted_feature_ids)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER_PATTERN.search(value)


def _validate_path_ref(
    *,
    errors: list[str],
    context: str,
    ref: Any,
    allow_url: bool = False,
) -> None:
    if not _non_empty_string(ref):
        errors.append(f"{context} must be a non-empty, non-placeholder string")
        return
    value = str(ref).strip()
    if allow_url and "://" in value:
        return
    target = ROOT / value
    if not target.exists():
        errors.append(f"{context} path does not exist: {value}")


def _validate_string_list(
    *,
    errors: list[str],
    context: str,
    value: Any,
    require_non_empty: bool = True,
    validate_paths: bool = False,
    allow_url: bool = False,
) -> None:
    if not isinstance(value, list):
        errors.append(f"{context} must be a list")
        return
    if require_non_empty and not value:
        errors.append(f"{context} must be a non-empty list")
        return
    for index, item in enumerate(value):
        item_context = f"{context}[{index}]"
        if validate_paths:
            _validate_path_ref(
                errors=errors,
                context=item_context,
                ref=item,
                allow_url=allow_url,
            )
        elif not _non_empty_string(item):
            errors.append(f"{item_context} must be a non-empty, non-placeholder string")


def _endpoint_certification_operations() -> set[tuple[str, str]]:
    if not ENDPOINT_CERTIFICATION_LEDGER_PATH.exists():
        return set()
    payload = json.loads(ENDPOINT_CERTIFICATION_LEDGER_PATH.read_text(encoding="utf-8"))
    endpoints = payload.get("endpoints", [])
    if not isinstance(endpoints, list):
        return set()
    return {
        (str(endpoint.get("method", "")).upper(), str(endpoint.get("path", "")))
        for endpoint in endpoints
        if isinstance(endpoint, dict)
    }


def _validate_test_reference(errors: list[str], context: str, reference: Any) -> None:
    if not _non_empty_string(reference):
        errors.append(f"{context} must be a non-empty, non-placeholder test reference")
        return
    match = TEST_REFERENCE_PATTERN.match(str(reference))
    if not match:
        errors.append(f"{context} must use tests/path.py::test_name")
        return
    test_path = ROOT / match.group("path")
    if not test_path.exists():
        errors.append(f"{context} test file does not exist: {match.group('path')}")
        return
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
    except SyntaxError:
        errors.append(f"{context} test file is not parseable: {match.group('path')}")
        return
    test_name = match.group("test")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name:
            return
    errors.append(f"{context} test does not exist: {reference}")


def _validate_utc_timestamp(
    errors: list[str],
    context: str,
    value: Any,
    *,
    evaluated_at_utc: datetime,
) -> None:
    if not _non_empty_string(value) or not UTC_TIMESTAMP_PATTERN.match(str(value)):
        errors.append(f"{context} must be an explicit UTC timestamp like 2026-06-30T00:00:00Z")
        return
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) != timezone.utc.utcoffset(parsed):
        errors.append(f"{context} must be timezone-aware UTC")
        return
    if parsed > evaluated_at_utc:
        errors.append(f"{context} cannot be after the evaluation time")
    elif evaluated_at_utc - parsed > PROMOTION_REVIEW_MAX_AGE:
        errors.append(f"{context} is older than {PROMOTION_REVIEW_MAX_AGE.days} days")


def _validate_surface_entries(
    *,
    errors: list[str],
    context: str,
    value: Any,
    required_fields: tuple[str, ...],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{context} must be a list")
        return
    for index, entry in enumerate(value):
        entry_context = f"{context}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_context} must be an object")
            continue
        for field in required_fields:
            if not _non_empty_string(entry.get(field)):
                errors.append(f"{entry_context}.{field} is required")


def _validate_api_surfaces(errors: list[str], feature: dict[str, Any], context: str) -> None:
    value = feature.get("api_surfaces")
    if not isinstance(value, list):
        errors.append(f"{context}.api_surfaces must be a list")
        return
    operations = _endpoint_certification_operations()
    for index, entry in enumerate(value):
        entry_context = f"{context}.api_surfaces[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_context} must be an object")
            continue
        method = str(entry.get("method", "")).upper()
        path = str(entry.get("path", ""))
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            errors.append(f"{entry_context}.method must be a supported HTTP method")
        if not path.startswith("/"):
            errors.append(f"{entry_context}.path must be an API path")
        if (method, path) not in operations:
            errors.append(
                f"{entry_context} must reference an endpoint certification ledger operation"
            )
        _validate_path_ref(
            errors=errors,
            context=f"{entry_context}.endpoint_certification_ref",
            ref=entry.get("endpoint_certification_ref"),
        )


def _validate_promotion_evidence(
    errors: list[str],
    feature: dict[str, Any],
    context: str,
) -> None:
    evidence = feature.get("promotion_evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{context}.promotion_evidence must be a structured object")
        return

    missing = [field for field in PROMOTION_EVIDENCE_REQUIRED_FIELDS if field not in evidence]
    if missing:
        errors.append(f"{context}.promotion_evidence missing fields: {', '.join(sorted(missing))}")
        return

    _validate_string_list(
        errors=errors,
        context=f"{context}.promotion_evidence.code_modules",
        value=evidence.get("code_modules"),
        validate_paths=True,
    )
    _validate_string_list(
        errors=errors,
        context=f"{context}.promotion_evidence.api_contracts",
        value=evidence.get("api_contracts"),
        validate_paths=True,
    )
    test_evidence = evidence.get("test_evidence")
    if not isinstance(test_evidence, list) or not test_evidence:
        errors.append(f"{context}.promotion_evidence.test_evidence must be a non-empty list")
    else:
        for index, reference in enumerate(test_evidence):
            _validate_test_reference(
                errors,
                f"{context}.promotion_evidence.test_evidence[{index}]",
                reference,
            )
    _validate_string_list(
        errors=errors,
        context=f"{context}.promotion_evidence.runtime_evidence",
        value=evidence.get("runtime_evidence"),
        validate_paths=True,
        allow_url=True,
    )
    ci_evidence = evidence.get("ci_evidence")
    if not isinstance(ci_evidence, dict):
        errors.append(f"{context}.promotion_evidence.ci_evidence must be an object")
    else:
        _validate_string_list(
            errors=errors,
            context=f"{context}.promotion_evidence.ci_evidence.local_gates",
            value=ci_evidence.get("local_gates"),
        )
        _validate_string_list(
            errors=errors,
            context=f"{context}.promotion_evidence.ci_evidence.github_checks",
            value=ci_evidence.get("github_checks"),
            allow_url=True,
        )
    _validate_string_list(
        errors=errors,
        context=f"{context}.promotion_evidence.documentation",
        value=evidence.get("documentation"),
        validate_paths=True,
    )
    _validate_string_list(
        errors=errors,
        context=f"{context}.promotion_evidence.runbooks",
        value=evidence.get("runbooks"),
        validate_paths=True,
    )
    _validate_string_list(
        errors=errors,
        context=f"{context}.promotion_evidence.proof_artifacts",
        value=evidence.get("proof_artifacts"),
        validate_paths=True,
        allow_url=True,
    )


def _validate_planned_capabilities(errors: list[str], payload: dict[str, Any]) -> None:
    planned_capabilities = payload.get("planned_capabilities")
    if not isinstance(planned_capabilities, list):
        errors.append("planned_capabilities must be a list")
        return
    for index, capability in enumerate(planned_capabilities):
        context = f"planned_capabilities[{index}]"
        if not isinstance(capability, dict):
            errors.append(f"{context} must be an object")
            continue
        missing = [field for field in PLANNED_CAPABILITY_REQUIRED_FIELDS if field not in capability]
        if missing:
            errors.append(f"{context} missing fields: {', '.join(sorted(missing))}")
            continue
        for field in PLANNED_CAPABILITY_REQUIRED_FIELDS:
            if not _non_empty_string(capability.get(field)):
                errors.append(f"{context}.{field} is required")
        if not FEATURE_ID_PATTERN.match(str(capability.get("id", ""))):
            errors.append(f"{context}.id must be stable kebab-case")
        if capability.get("status") != "planned":
            errors.append(f"{context}.status must remain planned until promotion")
        _validate_path_ref(
            errors=errors,
            context=f"{context}.governing_rfc",
            ref=capability.get("governing_rfc"),
        )


def _validate_feature_entry(
    errors: list[str],
    feature: dict[str, Any],
    index: int,
    *,
    evaluated_at_utc: datetime,
) -> None:
    context = f"features[{index}]"
    status = feature.get("status")
    if status in NON_IMPLEMENTED_FEATURE_STATUSES:
        errors.append(
            f"{context}.status {status!r} is not allowed under features[]; "
            "features[] is reserved for implemented supported-feature entries"
        )
        return
    if status != IMPLEMENTED_FEATURE_STATUS:
        errors.append(f"{context} invalid status {status!r}")
        return

    if not FEATURE_ID_PATTERN.match(str(feature.get("id", ""))):
        errors.append(f"{context}.id must be stable kebab-case")

    missing = [field for field in IMPLEMENTED_FEATURE_REQUIRED_FIELDS if field not in feature]
    if missing:
        errors.append(f"{context} implemented feature missing fields: {', '.join(sorted(missing))}")
        return

    for field in (
        "name",
        "owner",
        "support_scope",
        "unsupported_scope",
        "consumer_publication_state",
        "gateway_workbench_state",
        "data_product_state",
        "promotion_decision_ref",
    ):
        if not _non_empty_string(feature.get(field)):
            errors.append(f"{context}.{field} is required")

    _validate_path_ref(
        errors=errors,
        context=f"{context}.governing_rfc",
        ref=feature.get("governing_rfc"),
    )
    _validate_utc_timestamp(
        errors,
        f"{context}.last_reviewed_utc",
        feature.get("last_reviewed_utc"),
        evaluated_at_utc=evaluated_at_utc,
    )
    _validate_api_surfaces(errors, feature, context)
    _validate_surface_entries(
        errors=errors,
        context=f"{context}.ui_surfaces",
        value=feature.get("ui_surfaces"),
        required_fields=("surface", "state", "evidence_ref"),
    )
    _validate_surface_entries(
        errors=errors,
        context=f"{context}.source_dependencies",
        value=feature.get("source_dependencies"),
        required_fields=("repository", "product_or_contract", "authority_boundary"),
    )
    _validate_string_list(
        errors=errors,
        context=f"{context}.known_gaps",
        value=feature.get("known_gaps"),
        require_non_empty=False,
    )
    _validate_promotion_evidence(errors, feature, context)


def validate_supported_features(
    payload: dict[str, Any],
    *,
    evaluated_at_utc: datetime | None = None,
) -> list[str]:
    evaluated_at = evaluated_at_utc or datetime.now(UTC)
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")
    errors: list[str] = []
    if not SUPPORTED_FEATURES_SCHEMA_PATH.exists():
        errors.append(f"Missing {_relative(SUPPORTED_FEATURES_SCHEMA_PATH)}")
    else:
        try:
            json.loads(SUPPORTED_FEATURES_SCHEMA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{_relative(SUPPORTED_FEATURES_SCHEMA_PATH)} is invalid JSON: {exc.msg}")
    if payload.get("schema") != _relative(SUPPORTED_FEATURES_SCHEMA_PATH):
        errors.append("supported-features schema reference is required")
    if payload.get("repository") is None:
        errors.append("supported-features repository is required")
    if payload.get("policy") != CURRENT_POLICY:
        errors.append("supported-features policy must preserve implementation-backed promotion")

    features = payload.get("features")
    if not isinstance(features, list):
        errors.append("supported-features features must be a list")
    else:
        seen_feature_ids: set[str] = set()
        for index, feature in enumerate(features):
            if not isinstance(feature, dict):
                errors.append(f"features[{index}] must be an object")
                continue
            feature_id = str(feature.get("id", ""))
            if feature_id in seen_feature_ids:
                errors.append(f"features[{index}].id duplicates an earlier feature")
            seen_feature_ids.add(feature_id)
            _validate_feature_entry(
                errors,
                feature,
                index,
                evaluated_at_utc=evaluated_at,
            )

    _validate_planned_capabilities(errors, payload)
    return errors


def evaluate_supported_feature_promotion(
    registry_path: Path,
    *,
    evaluated_at_utc: datetime,
) -> SupportedFeaturePromotionEvaluation:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")
    source_ref = _relative(registry_path)
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _invalid_evaluation(("supported-features registry is missing",), source_ref)
    except json.JSONDecodeError:
        return _invalid_evaluation(("supported-features registry is invalid JSON",), source_ref)
    if not isinstance(payload, dict):
        return _invalid_evaluation(("supported-features registry must be an object",), source_ref)

    errors = tuple(validate_supported_features(payload, evaluated_at_utc=evaluated_at_utc))
    if errors:
        blockers = [SUPPORTED_FEATURE_REGISTRY_INVALID]
        if any("last_reviewed_utc" in error and "older than" in error for error in errors):
            blockers.append(SUPPORTED_FEATURE_PROMOTION_EVIDENCE_STALE)
        return SupportedFeaturePromotionEvaluation(
            promoted_feature_ids=(),
            validation_errors=errors,
            blocker_codes=tuple(blockers),
            source_ref=source_ref,
        )

    features = payload.get("features", [])
    promoted_feature_ids = tuple(
        str(feature["id"])
        for feature in features
        if isinstance(feature, dict) and feature.get("status") == IMPLEMENTED_FEATURE_STATUS
    )
    return SupportedFeaturePromotionEvaluation(
        promoted_feature_ids=promoted_feature_ids,
        validation_errors=(),
        blocker_codes=(() if promoted_feature_ids else (NO_SUPPORTED_FEATURES_PROMOTED,)),
        source_ref=source_ref,
    )


def _invalid_evaluation(
    errors: tuple[str, ...], source_ref: str
) -> SupportedFeaturePromotionEvaluation:
    return SupportedFeaturePromotionEvaluation(
        promoted_feature_ids=(),
        validation_errors=errors,
        blocker_codes=(SUPPORTED_FEATURE_REGISTRY_INVALID,),
        source_ref=source_ref,
    )
