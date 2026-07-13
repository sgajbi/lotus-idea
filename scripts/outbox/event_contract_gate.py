from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys
from typing import Any

try:
    from scripts.outbox._bootstrap import ROOT
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from _bootstrap import ROOT  # type: ignore[import-not-found,no-redef]

try:
    from scripts.contract_text_guards import validate_forbidden_contract_text
except ModuleNotFoundError:
    from contract_text_guards import validate_forbidden_contract_text  # type: ignore[import-not-found,no-redef]

from app.domain.outbox.events import (  # noqa: E402
    FORBIDDEN_OUTBOX_PAYLOAD_KEYS,
    OUTBOX_EVENT_AGGREGATE_TYPE,
    OUTBOX_EVENT_SCHEMA_VERSION,
    SUPPORTED_OUTBOX_EVENT_TYPES,
)

CONTRACT_PATH = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"
OUTBOX_MIGRATION_PATHS = (
    ROOT / "migrations" / "001_idea_repository_foundation.sql",
    ROOT / "migrations" / "003_outbox_event_contract_constraints.sql",
    ROOT / "migrations" / "007_outbox_event_lineage.sql",
)

REQUIRED_EVENT_TYPES = SUPPORTED_OUTBOX_EVENT_TYPES

REQUIRED_ENVELOPE_FIELDS = (
    "eventId",
    "eventType",
    "aggregateType",
    "aggregateId",
    "schemaVersion",
    "occurredAtUtc",
    "correlationId",
    "traceId",
    "lineageOrigin",
    "payload",
    "producer",
    "sourceAuthority",
    "supportabilityStatus",
)

OPTIONAL_ENVELOPE_FIELDS = (
    "idempotencyFingerprint",
    "causationId",
)

FORBIDDEN_PAYLOAD_KEYS = tuple(FORBIDDEN_OUTBOX_PAYLOAD_KEYS)

REQUIRED_SOURCE_OF_TRUTH_KEYS = {
    "event_domain_model",
    "persistence_event_writers",
    "publisher_port",
    "publisher_adapter",
    "outbox_delivery",
    "outbox_delivery_readiness",
    "outbox_consumer_contract",
    "outbox_consumer_contract_gate",
    "contract_gate",
    "make_target",
    "rfc_slice_06",
    "rfc_slice_14",
    "rfc_slice_17",
}

REMAINING_CERTIFICATION_BLOCKERS = (
    "platform_mesh_event_publication_proof_missing",
    "downstream_consumer_runtime_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)

BOOLEAN_FALSE_CLAIMS = (
    "platformMeshEventPublicationProven",
    "externalBrokerPublicationSupported",
    "downstreamConsumersCertified",
    "gatewayWorkbenchProofPresent",
    "supportedFeaturePromoted",
)

FORBIDDEN_CONTRACT_TEXT = (
    "PB_SG_GLOBAL_BAL_001",
    "idea_high_cash_001",
    "/source-owned/",
    "client-ready supported",
)


def validate_outbox_event_contract(*, contract_path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"outbox event contract missing: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"outbox event contract is not valid JSON: {exc}"]
    if not isinstance(payload, Mapping):
        return ["outbox event contract must be a JSON object"]

    _validate_top_level(payload, errors)
    _validate_envelope(payload, errors)
    _validate_event_families(payload, errors)
    _validate_payload_safety(payload, errors)
    _validate_source_of_truth(payload, errors)
    _validate_source_code_alignment(errors)
    _validate_lineage_implementation_alignment(errors)
    _validate_migration_alignment(errors)
    validate_forbidden_contract_text(payload, errors, FORBIDDEN_CONTRACT_TEXT)
    return errors


def _validate_top_level(payload: Mapping[str, Any], errors: list[str]) -> None:
    expected = {
        "contractId": "lotus-idea-outbox-events",
        "contractVersion": "1.0.0",
        "schemaVersion": "lotus-idea.outbox-events.v1",
        "repository": "lotus-idea",
        "producer": "lotus-idea",
        "sourceAuthority": "lotus-idea",
        "lifecycleStatus": "implemented_contract_not_certified",
        "supportabilityStatus": "not_certified",
        "publicationScope": "internal_outbox_event_publication_contract",
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            errors.append(f"{key} must be {expected_value}")
    if payload.get("platformMeshEventContractAvailable") is not True:
        errors.append("platformMeshEventContractAvailable must be true")
    for key in BOOLEAN_FALSE_CLAIMS:
        if payload.get(key) is not False:
            errors.append(f"{key} must remain false before live certification")
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_CERTIFICATION_BLOCKERS
    ):
        errors.append("remainingCertificationBlockers must match the governed outbox blockers")


def _validate_envelope(payload: Mapping[str, Any], errors: list[str]) -> None:
    envelope = payload.get("envelope")
    if not isinstance(envelope, Mapping):
        errors.append("envelope must be present")
        return
    if tuple(envelope.get("requiredFields") or ()) != REQUIRED_ENVELOPE_FIELDS:
        errors.append("envelope.requiredFields must match the implemented publisher envelope")
    if tuple(envelope.get("optionalFields") or ()) != OPTIONAL_ENVELOPE_FIELDS:
        errors.append("envelope.optionalFields must match the implemented publisher envelope")
    field_policies = envelope.get("fieldPolicies")
    if not isinstance(field_policies, Mapping):
        errors.append("envelope.fieldPolicies must be present")
        return
    for field_name in REQUIRED_ENVELOPE_FIELDS:
        if field_name not in field_policies and field_name in {"aggregateType", "payload"}:
            errors.append(f"envelope.fieldPolicies missing required policy for {field_name}")
    example = envelope.get("example")
    if not isinstance(example, Mapping):
        errors.append("envelope.example must be present")
        return
    missing_example_fields = sorted(set(REQUIRED_ENVELOPE_FIELDS) - set(example))
    if missing_example_fields:
        errors.append("envelope.example missing fields: " + ", ".join(missing_example_fields))
    if example.get("traceId") == example.get("causationId"):
        errors.append("envelope.example must keep traceId distinct from causationId")


def _validate_event_families(payload: Mapping[str, Any], errors: list[str]) -> None:
    event_families = payload.get("eventFamilies")
    if not isinstance(event_families, Sequence) or isinstance(event_families, (str, bytes)):
        errors.append("eventFamilies must be a list")
        return
    event_types: list[str] = []
    for index, event_family in enumerate(event_families):
        if not isinstance(event_family, Mapping):
            errors.append(f"eventFamilies[{index}] must be an object")
            continue
        event_type = event_family.get("eventType")
        if isinstance(event_type, str):
            event_types.append(event_type)
        if event_family.get("aggregateType") != OUTBOX_EVENT_AGGREGATE_TYPE:
            errors.append(
                f"eventFamilies[{index}].aggregateType must be {OUTBOX_EVENT_AGGREGATE_TYPE}"
            )
        description = event_family.get("description")
        if not isinstance(description, str) or len(description.strip()) < 24:
            errors.append(f"eventFamilies[{index}].description must be meaningful")
    if tuple(event_types) != REQUIRED_EVENT_TYPES:
        errors.append("eventFamilies must list every implemented v1 event type in order")


def _validate_payload_safety(payload: Mapping[str, Any], errors: list[str]) -> None:
    policy = payload.get("payloadSafetyPolicy")
    if not isinstance(policy, Mapping):
        errors.append("payloadSafetyPolicy must be present")
        return
    if policy.get("payloadValueType") != "string":
        errors.append("payloadSafetyPolicy.payloadValueType must be string")
    forbidden_payload_keys = policy.get("forbiddenPayloadKeys") or ()
    if (
        not isinstance(forbidden_payload_keys, Sequence)
        or isinstance(forbidden_payload_keys, (str, bytes))
        or set(forbidden_payload_keys) != FORBIDDEN_OUTBOX_PAYLOAD_KEYS
    ):
        errors.append("payloadSafetyPolicy.forbiddenPayloadKeys must match domain guardrails")
    if "must not echo sensitive" not in str(policy.get("failureReasonPolicy", "")):
        errors.append("payloadSafetyPolicy.failureReasonPolicy must reject sensitive echoing")


def _validate_source_of_truth(payload: Mapping[str, Any], errors: list[str]) -> None:
    source_of_truth = payload.get("sourceOfTruth")
    if not isinstance(source_of_truth, Mapping):
        errors.append("sourceOfTruth must be present")
        return
    missing_keys = sorted(REQUIRED_SOURCE_OF_TRUTH_KEYS - set(source_of_truth))
    if missing_keys:
        errors.append("sourceOfTruth missing keys: " + ", ".join(missing_keys))
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"sourceOfTruth.{key} must be non-empty text")
            continue
        if value.startswith("make "):
            target = value.removeprefix("make ")
            if f"{target}:" not in (ROOT / "Makefile").read_text(encoding="utf-8"):
                errors.append(f"sourceOfTruth.{key} references missing Make target {target}")
            continue
        relative_path = Path(value)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            errors.append(f"sourceOfTruth.{key} must be a repository-relative path")
            continue
        if not (ROOT / relative_path).exists():
            errors.append(f"sourceOfTruth.{key} path does not exist")


def _validate_source_code_alignment(errors: list[str]) -> None:
    try:
        persistence_text = (ROOT / "src" / "app" / "domain" / "persistence.py").read_text(
            encoding="utf-8"
        )
        event_text = (
            ROOT / "src" / "app" / "domain" / "outbox" / "events.py"
        ).read_text(encoding="utf-8")
        publisher_text = (
            ROOT / "src" / "app" / "infrastructure" / "outbox" / "publisher.py"
        ).read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"source alignment read failed: {exc}")
        return
    for event_type in REQUIRED_EVENT_TYPES:
        if event_type not in persistence_text:
            errors.append(f"implemented persistence event type missing: {event_type}")
    for forbidden_key in FORBIDDEN_PAYLOAD_KEYS:
        if f'"{forbidden_key}"' not in event_text:
            errors.append(f"domain forbidden payload key missing: {forbidden_key}")
    for envelope_field in REQUIRED_ENVELOPE_FIELDS + OPTIONAL_ENVELOPE_FIELDS:
        if f'"{envelope_field}"' not in publisher_text:
            errors.append(f"publisher envelope field missing: {envelope_field}")
    for constant in (
        "SUPPORTED_OUTBOX_EVENT_TYPES",
        "OUTBOX_EVENT_SCHEMA_VERSION",
        "OUTBOX_EVENT_AGGREGATE_TYPE",
    ):
        if constant not in event_text:
            errors.append(f"domain outbox contract constant missing: {constant}")


def _validate_migration_alignment(errors: list[str]) -> None:
    migration_text_parts: list[str] = []
    for migration_path in OUTBOX_MIGRATION_PATHS:
        try:
            migration_text_parts.append(migration_path.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"migration alignment read failed: {exc}")
            return
    migration_text = "\n".join(migration_text_parts)
    for event_type in REQUIRED_EVENT_TYPES:
        if f"'{event_type}'" not in migration_text:
            errors.append(f"migration outbox event_type check missing: {event_type}")
    if f"aggregate_type = '{OUTBOX_EVENT_AGGREGATE_TYPE}'" not in migration_text:
        errors.append("migration outbox aggregate_type check missing")
    if f"schema_version = '{OUTBOX_EVENT_SCHEMA_VERSION}'" not in migration_text:
        errors.append("migration outbox schema_version check missing")


def _validate_lineage_implementation_alignment(errors: list[str]) -> None:
    source_requirements = {
        "src/app/domain/outbox/events.py": (
            "class EventLineageContext",
            "class EventLineageOrigin",
            "trace_id: str",
            "lineage_origin: EventLineageOrigin",
        ),
        "src/app/domain/persistence.py": ("event_lineage: EventLineageContext | None",),
        "src/app/domain/outbox/persistence.py": ("lineage=event_lineage",),
        "src/app/ports/idea_repository.py": ("EventLineageContext",),
        "src/app/infrastructure/outbox/postgres_writes.py": (
            "event.trace_id",
            "event.lineage_origin.value",
        ),
        "src/app/infrastructure/outbox/postgres_delivery.py": (
            'read_row_value(row, "trace_id")',
            'read_row_value(row, "lineage_origin")',
        ),
        "migrations/007_outbox_event_lineage.sql": (
            "ck_idea_outbox_event_lineage_identifiers",
            "ck_idea_outbox_event_causation_origin",
            "ALTER COLUMN trace_id SET NOT NULL",
        ),
    }
    for relative_path, fragments in source_requirements.items():
        _require_source_fragments(relative_path, fragments, errors)

    publisher_path = "src/app/infrastructure/outbox/publisher.py"
    publisher_text = _read_source_text(publisher_path, errors)
    if publisher_text is not None:
        if "trace_id=event.trace_id" not in publisher_text:
            errors.append("outbox publisher must propagate event.trace_id as transport trace")
        if "trace_id=event.causation_id" in publisher_text:
            errors.append("outbox publisher must not substitute causation_id for trace_id")

    api_mapper_counts = {
        "src/app/api/idea_signals.py": 1,
        "src/app/api/candidate_lifecycle.py": 1,
        "src/app/api/review_workflow.py": 2,
        "src/app/api/conversion_governance.py": 2,
        "src/app/api/report_evidence.py": 1,
    }
    for relative_path, expected_count in api_mapper_counts.items():
        source_text = _read_source_text(relative_path, errors)
        if source_text is None:
            continue
        if source_text.count("event_lineage_from_request(") < expected_count:
            errors.append(
                f"{relative_path} must map lineage for {expected_count} mutation route(s)"
            )
        if "EventCausationHeader" not in source_text:
            errors.append(f"{relative_path} must expose the governed causation header")

    persistence_text = _read_source_text("src/app/domain/persistence.py", errors)
    if persistence_text is not None and persistence_text.count("event_lineage=event_lineage") < len(
        REQUIRED_EVENT_TYPES
    ):
        errors.append("domain persistence must pass lineage to every outbox event family")


def _require_source_fragments(
    relative_path: str,
    fragments: Sequence[str],
    errors: list[str],
) -> None:
    source_text = _read_source_text(relative_path, errors)
    if source_text is None:
        return
    for fragment in fragments:
        if fragment not in source_text:
            errors.append(f"{relative_path} missing lineage contract fragment: {fragment}")


def _read_source_text(relative_path: str, errors: list[str]) -> str | None:
    try:
        return (ROOT / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"lineage source alignment read failed for {relative_path}: {exc}")
        return None


def main() -> int:
    errors = validate_outbox_event_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox event contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
