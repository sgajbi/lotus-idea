from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"

REQUIRED_EVENT_TYPES = (
    "idea.candidate.persisted.v1",
    "idea.lifecycle.transitioned.v1",
    "idea.review.decision_recorded.v1",
    "idea.feedback.recorded.v1",
    "idea.conversion.intent_requested.v1",
    "idea.conversion.outcome_recorded.v1",
    "idea.report_evidence_pack.requested.v1",
)

REQUIRED_ENVELOPE_FIELDS = (
    "eventId",
    "eventType",
    "aggregateType",
    "aggregateId",
    "schemaVersion",
    "occurredAtUtc",
    "payload",
    "producer",
    "sourceAuthority",
    "supportabilityStatus",
)

OPTIONAL_ENVELOPE_FIELDS = (
    "idempotencyFingerprint",
    "correlationId",
    "causationId",
)

FORBIDDEN_PAYLOAD_KEYS = (
    "account_id",
    "client_id",
    "client_name",
    "content_hash",
    "evidence_hash",
    "holding_id",
    "idempotency_key",
    "portfolio_id",
    "raw_source_payload",
    "request_body",
    "response_body",
    "route",
    "source_route",
)

REQUIRED_SOURCE_OF_TRUTH_KEYS = {
    "event_domain_model",
    "persistence_event_writers",
    "publisher_port",
    "publisher_adapter",
    "outbox_delivery",
    "outbox_delivery_readiness",
    "contract_gate",
    "make_target",
    "rfc_slice_06",
    "rfc_slice_14",
    "rfc_slice_17",
}

REMAINING_CERTIFICATION_BLOCKERS = (
    "platform_mesh_event_publication_proof_missing",
    "downstream_consumer_contracts_missing",
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
    _validate_forbidden_contract_text(payload, errors)
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
        if event_family.get("aggregateType") != "idea_candidate":
            errors.append(f"eventFamilies[{index}].aggregateType must be idea_candidate")
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
    if tuple(policy.get("forbiddenPayloadKeys") or ()) != FORBIDDEN_PAYLOAD_KEYS:
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
        event_text = (ROOT / "src" / "app" / "domain" / "events.py").read_text(encoding="utf-8")
        publisher_text = (
            ROOT / "src" / "app" / "infrastructure" / "outbox_publisher.py"
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


def _validate_forbidden_contract_text(value: object, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _validate_forbidden_contract_text(nested, errors, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, nested in enumerate(value):
            _validate_forbidden_contract_text(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for forbidden_text in FORBIDDEN_CONTRACT_TEXT:
            if forbidden_text in value:
                errors.append(f"{path}: forbidden contract text `{forbidden_text}`")


def main() -> int:
    errors = validate_outbox_event_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox event contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
