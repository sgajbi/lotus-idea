from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.outbox import consumer_runtime_proof as proof_module
from app.application.outbox.consumer_runtime_proof import (
    OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED,
    OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS,
    REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS,
    build_outbox_consumer_runtime_proof_payload,
    outbox_consumer_runtime_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[3]
VALID_CONSUMER_CONTRACT_PAYLOAD = json.loads(
    (ROOT / "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json").read_text(
        encoding="utf-8"
    )
)
VALID_EVENT_CONTRACT_PAYLOAD = json.loads(
    (ROOT / "contracts/outbox-events/lotus-idea-outbox-events.v1.json").read_text(encoding="utf-8")
)
VALID_CONSUMER_POLICY = cast(
    dict[str, str],
    VALID_CONSUMER_CONTRACT_PAYLOAD["consumerContractPolicy"],
)


def test_builds_source_safe_outbox_consumer_runtime_proof() -> None:
    proof = _valid_outbox_consumer_runtime_proof()

    assert proof["schemaVersion"] == OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "outbox_downstream_consumer_runtime_contract"
    assert proof["proofScope"] == "bounded_declared_consumer_runtime_proof"
    assert proof["outboxConsumerRuntimeProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED
    assert tuple(proof["evidenceRefs"]) == REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS
    )
    assert proof["externalBrokerPublicationSupported"] is False
    assert proof["platformMeshEventCertified"] is False
    assert proof["gatewayWorkbenchProofPresent"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert outbox_consumer_runtime_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "idea_high_cash_001" not in serialized
    assert "eventId" not in serialized
    assert "aggregateId" not in serialized
    assert "idempotency" not in serialized


def test_rejects_outbox_consumer_runtime_proof_when_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_outbox_consumer_runtime_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["outboxConsumerRuntimeProofValid"] is False
    assert outbox_consumer_runtime_proof_is_valid(proof) is False


def test_rejects_outbox_consumer_runtime_proof_with_naive_timestamp() -> None:
    proof = build_outbox_consumer_runtime_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["outboxConsumerRuntimeProofValid"] is False
    assert outbox_consumer_runtime_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "outbox"),
        ("proofScope", "production_consumer_delivery"),
        ("outboxConsumerRuntimeProofValid", False),
        ("externalBrokerPublicationSupported", True),
        ("platformMeshEventCertified", True),
        ("gatewayWorkbenchProofPresent", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_outbox_consumer_runtime_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_outbox_consumer_runtime_proof()
    proof[field_name] = bad_value

    assert outbox_consumer_runtime_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_outbox_consumer_runtime_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_outbox_consumer_runtime_proof()
    proof[field_name] = bad_value

    assert outbox_consumer_runtime_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "declaredConsumerCoveragePresent",
        "eventTypeCoverageSourceOwned",
        "authorityBoundariesPreserved",
    ],
)
def test_rejects_outbox_consumer_runtime_proof_with_invalid_proof_checks(
    check_name: str,
) -> None:
    proof = _valid_outbox_consumer_runtime_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert outbox_consumer_runtime_proof_is_valid(proof) is False


def test_outbox_consumer_runtime_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "outbox-consumer-runtime-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert outbox_consumer_runtime_proof_is_valid(proof) is True


def test_outbox_consumer_runtime_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("event_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `event_id` is present"]


def test_outbox_consumer_runtime_proof_rejects_non_object_contract_payload(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    assert proof_module._load_json_object(contract_path) is None


def test_outbox_consumer_runtime_proof_rejects_missing_make_target(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        "outbox-consumer-contract-gate:\n\tpython scripts/outbox/consumer_contract_gate.py\n",
        encoding="utf-8",
    )

    assert (
        proof_module._required_make_target_evidence_present(
            repository_root=tmp_path,
            evidence_refs=("make outbox-consumer-runtime-proof-contract-gate",),
        )
        is False
    )


def test_outbox_consumer_runtime_proof_rejects_invalid_declared_consumer_status() -> None:
    contract_payload = _valid_consumer_contract_payload()
    contract_payload["declaredConsumers"][0]["certificationStatus"] = "certified"

    assert proof_module._declared_consumer_coverage_present(contract_payload) is False


@pytest.mark.parametrize(
    ("contract_payload", "event_contract_payload"),
    [
        (VALID_CONSUMER_CONTRACT_PAYLOAD, {"eventFamilies": []}),
        ({"declaredConsumers": "bad"}, VALID_EVENT_CONTRACT_PAYLOAD),
        ({"declaredConsumers": [42]}, VALID_EVENT_CONTRACT_PAYLOAD),
        (
            {
                "declaredConsumers": [
                    {"consumerRepository": "lotus-gateway", "consumedEventTypes": "bad"}
                ]
            },
            VALID_EVENT_CONTRACT_PAYLOAD,
        ),
        (
            {
                "declaredConsumers": [
                    {"consumerRepository": "lotus-gateway", "consumedEventTypes": []}
                ]
            },
            VALID_EVENT_CONTRACT_PAYLOAD,
        ),
        (
            {
                "declaredConsumers": [
                    {"consumerRepository": "lotus-gateway", "consumedEventTypes": ["unknown"]}
                ]
            },
            VALID_EVENT_CONTRACT_PAYLOAD,
        ),
    ],
)
def test_outbox_consumer_runtime_proof_rejects_invalid_event_coverage(
    contract_payload: dict[str, Any],
    event_contract_payload: dict[str, Any],
) -> None:
    assert (
        proof_module._declared_event_types_are_source_owned(
            contract_payload=contract_payload,
            event_contract_payload=event_contract_payload,
        )
        is False
    )


def test_outbox_consumer_runtime_proof_rejects_invalid_event_family_shape() -> None:
    assert proof_module._event_types_from_contract({"eventFamilies": "bad"}) == ()


@pytest.mark.parametrize(
    "contract_payload",
    [
        {"consumerContractPolicy": "bad"},
        {
            "consumerContractPolicy": {"summary": "missing required policy text"},
            "declaredConsumers": [],
        },
        {
            "consumerContractPolicy": VALID_CONSUMER_POLICY,
            "declaredConsumers": "bad",
        },
        {
            "consumerContractPolicy": VALID_CONSUMER_POLICY,
            "declaredConsumers": [42],
        },
        {
            "consumerContractPolicy": VALID_CONSUMER_POLICY,
            "declaredConsumers": [{"consumerRepository": 7, "authorityBoundary": "bad"}],
        },
        {
            "consumerContractPolicy": VALID_CONSUMER_POLICY,
            "declaredConsumers": [
                {"consumerRepository": "lotus-unknown", "authorityBoundary": "bad"}
            ],
        },
        {
            "consumerContractPolicy": VALID_CONSUMER_POLICY,
            "declaredConsumers": [
                {"consumerRepository": "lotus-advise", "authorityBoundary": "missing terms"}
            ],
        },
    ],
)
def test_outbox_consumer_runtime_proof_rejects_invalid_authority_boundaries(
    contract_payload: dict[str, Any],
) -> None:
    assert proof_module._authority_boundaries_preserved(contract_payload) is False


def _valid_outbox_consumer_runtime_proof() -> dict[str, Any]:
    return build_outbox_consumer_runtime_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _valid_consumer_contract_payload() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            (ROOT / "contracts/outbox-events/lotus-idea-outbox-consumers.v1.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "outbox" / "generate_consumer_runtime_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_outbox_consumer_runtime_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "outbox" / "consumer_runtime_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "outbox_consumer_runtime_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
