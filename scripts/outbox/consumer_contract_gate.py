from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
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

CONTRACT_PATH = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-consumers.v1.json"
EVENT_CONTRACT_PATH = ROOT / "contracts" / "outbox-events" / "lotus-idea-outbox-events.v1.json"

REQUIRED_CONSUMERS = ("lotus-gateway", "lotus-advise", "lotus-manage", "lotus-report")
REQUIRED_SOURCE_OF_TRUTH_KEYS = {
    "producer_event_contract",
    "consumer_contract",
    "consumer_contract_gate",
    "make_target",
    "outbox_delivery_readiness",
    "rfc_slice_06",
    "rfc_slice_14",
    "rfc_slice_17",
}
REMAINING_CERTIFICATION_BLOCKERS = (
    "downstream_consumer_runtime_proof_missing",
    "platform_mesh_event_publication_proof_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)
BOOLEAN_FALSE_CLAIMS = (
    "downstreamConsumerRuntimeProven",
    "platformMeshEventPublicationProven",
    "gatewayWorkbenchProofPresent",
    "supportedFeaturePromoted",
)
FORBIDDEN_CONTRACT_TEXT = (
    "PB_SG_GLOBAL_BAL_001",
    "idea_high_cash_001",
    "/source-owned/",
    "client-ready supported",
    "certified live consumer",
)


def validate_outbox_consumer_contract(*, contract_path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    payload = _load_json(contract_path, errors, "outbox consumer contract")
    event_contract = _load_json(EVENT_CONTRACT_PATH, errors, "outbox event contract")
    if not isinstance(payload, Mapping):
        return errors or ["outbox consumer contract must be a JSON object"]
    if not isinstance(event_contract, Mapping):
        return errors or ["outbox event contract must be a JSON object"]

    event_types = _event_types_from_event_contract(event_contract, errors)
    _validate_top_level(payload, errors)
    _validate_policy(payload, errors)
    _validate_consumers(payload, event_types, errors)
    _validate_source_of_truth(payload, errors)
    validate_forbidden_contract_text(payload, errors, FORBIDDEN_CONTRACT_TEXT)
    return errors


def _load_json(path: Path, errors: list[str], label: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{label} missing: {exc}")
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
    return None


def _event_types_from_event_contract(
    event_contract: Mapping[str, Any],
    errors: list[str],
) -> tuple[str, ...]:
    event_families = event_contract.get("eventFamilies")
    if not isinstance(event_families, Sequence) or isinstance(event_families, (str, bytes)):
        errors.append("outbox event contract eventFamilies must be a list")
        return ()
    event_types: list[str] = []
    for event_family in event_families:
        if isinstance(event_family, Mapping) and isinstance(event_family.get("eventType"), str):
            event_types.append(event_family["eventType"])
    if not event_types:
        errors.append("outbox event contract must expose event types")
    return tuple(event_types)


def _validate_top_level(payload: Mapping[str, Any], errors: list[str]) -> None:
    expected = {
        "contractId": "lotus-idea-outbox-consumers",
        "contractVersion": "1.0.0",
        "schemaVersion": "lotus-idea.outbox-consumers.v1",
        "repository": "lotus-idea",
        "producer": "lotus-idea",
        "lifecycleStatus": "implemented_contract_not_certified",
        "supportabilityStatus": "not_certified",
        "publicationScope": "declared_downstream_consumer_contract",
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            errors.append(f"{key} must be {expected_value}")
    if payload.get("downstreamConsumerContractAvailable") is not True:
        errors.append("downstreamConsumerContractAvailable must be true")
    for key in BOOLEAN_FALSE_CLAIMS:
        if payload.get(key) is not False:
            errors.append(f"{key} must remain false before live certification")
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_CERTIFICATION_BLOCKERS
    ):
        errors.append("remainingCertificationBlockers must match the governed consumer blockers")


def _validate_policy(payload: Mapping[str, Any], errors: list[str]) -> None:
    policy = payload.get("consumerContractPolicy")
    if not isinstance(policy, Mapping):
        errors.append("consumerContractPolicy must be present")
        return
    required_fragments = {
        "authorityBoundary": "source-authoritative services",
        "payloadPolicy": "must not require raw",
        "failurePolicy": "must not echo raw",
        "lineagePolicy": "must preserve correlationId and traceId as distinct",
        "certificationPolicy": "live contract tests",
    }
    for key, required_fragment in required_fragments.items():
        value = policy.get(key)
        if not isinstance(value, str) or required_fragment not in value:
            errors.append(f"consumerContractPolicy.{key} must include `{required_fragment}`")


def _validate_consumers(
    payload: Mapping[str, Any],
    event_types: tuple[str, ...],
    errors: list[str],
) -> None:
    consumers = payload.get("declaredConsumers")
    if not isinstance(consumers, Sequence) or isinstance(consumers, (str, bytes)):
        errors.append("declaredConsumers must be a list")
        return
    repositories: list[str] = []
    for index, consumer in enumerate(consumers):
        if not isinstance(consumer, Mapping):
            errors.append(f"declaredConsumers[{index}] must be an object")
            continue
        repository = consumer.get("consumerRepository")
        if isinstance(repository, str):
            repositories.append(repository)
        if consumer.get("certificationStatus") != "contract_declared_not_runtime_certified":
            errors.append(
                f"declaredConsumers[{index}].certificationStatus must stay not runtime certified"
            )
        for key in ("consumerRole", "authorityBoundary", "requiredRuntimeProof"):
            value = consumer.get(key)
            if not isinstance(value, str) or len(value.strip()) < 24:
                errors.append(f"declaredConsumers[{index}].{key} must be meaningful text")
        consumed = consumer.get("consumedEventTypes")
        if not isinstance(consumed, Sequence) or isinstance(consumed, (str, bytes)):
            errors.append(f"declaredConsumers[{index}].consumedEventTypes must be a list")
            continue
        for event_type in consumed:
            if event_type not in event_types:
                errors.append(
                    f"declaredConsumers[{index}] references unknown event type `{event_type}`"
                )
    if tuple(repositories) != REQUIRED_CONSUMERS:
        errors.append("declaredConsumers must list the governed downstream repositories in order")


def _validate_source_of_truth(payload: Mapping[str, Any], errors: list[str]) -> None:
    source_of_truth = payload.get("sourceOfTruth")
    if not isinstance(source_of_truth, Mapping):
        errors.append("sourceOfTruth must be present")
        return
    missing_keys = sorted(REQUIRED_SOURCE_OF_TRUTH_KEYS - set(source_of_truth))
    if missing_keys:
        errors.append("sourceOfTruth missing keys: " + ", ".join(missing_keys))
    makefile_text = (ROOT / "Makefile").read_text(encoding="utf-8")
    for key, value in sorted(source_of_truth.items()):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"sourceOfTruth.{key} must be non-empty text")
            continue
        if value.startswith("make "):
            target = value.removeprefix("make ")
            if f"{target}:" not in makefile_text:
                errors.append(f"sourceOfTruth.{key} references missing Make target {target}")
            continue
        relative_path = Path(value)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            errors.append(f"sourceOfTruth.{key} must be a repository-relative path")
            continue
        if not (ROOT / relative_path).exists():
            errors.append(f"sourceOfTruth.{key} path does not exist")


def main() -> int:
    errors = validate_outbox_consumer_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox consumer contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
