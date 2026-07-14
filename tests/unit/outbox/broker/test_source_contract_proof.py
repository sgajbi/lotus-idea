from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.outbox.broker.source_contract_proof import (
    OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES,
    REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS,
    REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS,
    _python_class_declares_methods,
    build_outbox_broker_source_contract_proof_payload,
    outbox_broker_source_contract_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[4]
GENERATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_builds_source_safe_outbox_broker_source_contract_proof() -> None:
    proof = _valid_proof()

    assert proof["schemaVersion"] == OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "outbox_broker_source_contract"
    assert proof["proofScope"] == "publisher_port_adapter_and_operator_api_source_contract"
    assert proof["evidenceClass"] == "source_contract"
    assert proof["requiredBlockerEvidenceClasses"] == dict(
        OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    )
    assert proof["outboxBrokerSourceContractValid"] is True
    assert proof["aggregateBlockersCleared"] == OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED
    assert proof["evidenceRefs"] == REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS
    assert proof["remainingCertificationBlockers"] == (
        REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS
    )
    assert proof["sourceContractStatus"] == "valid"
    for field_name in (
        "runtimeExecutionObserved",
        "externalBrokerConfigured",
        "externalBrokerPublicationObserved",
        "deploymentObserved",
        "productionCertificationGranted",
        "externalBrokerPublicationSupported",
        "platformMeshEventCertified",
        "downstreamConsumersCertified",
        "gatewayWorkbenchProofPresent",
        "supportedFeaturePromoted",
        "proofClosed",
    ):
        assert proof[field_name] is False
    assert outbox_broker_source_contract_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    for forbidden_fragment in (
        "PB_SG_GLOBAL_BAL_001",
        "idea_high_cash_001",
        "eventId",
        "aggregateId",
        "idempotency",
    ):
        assert forbidden_fragment not in serialized


def test_missing_source_evidence_is_invalid_and_clears_no_blocker(tmp_path: Path) -> None:
    proof = build_outbox_broker_source_contract_proof_payload(
        generated_at_utc=GENERATED_AT_UTC,
        repository_root=tmp_path,
    )

    assert proof["outboxBrokerSourceContractValid"] is False
    assert proof["sourceContractStatus"] == "invalid"
    assert proof["aggregateBlockersCleared"] == ()
    assert proof["runtimeExecutionObserved"] is False
    assert outbox_broker_source_contract_proof_is_valid(proof) is False


def test_naive_timestamp_is_invalid_and_clears_no_blocker() -> None:
    proof = build_outbox_broker_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["outboxBrokerSourceContractValid"] is False
    assert proof["aggregateBlockersCleared"] == ()
    assert outbox_broker_source_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "outbox_broker_runtime_execution"),
        ("proofScope", "production_broker"),
        ("evidenceClass", "runtime_execution"),
        ("outboxBrokerSourceContractValid", False),
        ("sourceContractStatus", "runtime_certified"),
        ("runtimeExecutionObserved", True),
        ("externalBrokerConfigured", True),
        ("externalBrokerPublicationObserved", True),
        ("deploymentObserved", True),
        ("productionCertificationGranted", True),
        ("externalBrokerPublicationSupported", True),
        ("platformMeshEventCertified", True),
        ("downstreamConsumersCertified", True),
        ("gatewayWorkbenchProofPresent", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_forged_top_level_claim(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_proof()
    proof[field_name] = bad_value

    assert outbox_broker_source_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        (
            "requiredBlockerEvidenceClasses",
            {"external_broker_runtime_proof_missing": "source_contract"},
        ),
        ("aggregateBlockersCleared", ["external_broker_runtime_proof_missing"]),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_forged_contract_field(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_proof()
    proof[field_name] = bad_value

    assert outbox_broker_source_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "publisherPortContractPresent",
        "publisherAdapterContractPresent",
        "evidenceClassMatchesBlockers",
    ],
)
def test_rejects_failed_source_contract_check(check_name: str) -> None:
    proof = _valid_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert outbox_broker_source_contract_proof_is_valid(proof) is False


def test_python_contract_check_uses_parsed_class_and_methods(tmp_path: Path) -> None:
    source = tmp_path / "publisher.py"
    source.write_text(
        "class Publisher:\n"
        "    def publish(self):\n"
        "        return None\n"
        "    async def close(self):\n"
        "        return None\n",
        encoding="utf-8",
    )

    assert _python_class_declares_methods(
        source,
        class_name="Publisher",
        required_methods=("publish", "close"),
    )
    assert not _python_class_declares_methods(
        source,
        class_name="Publisher",
        required_methods=("publish", "health"),
    )


@pytest.mark.parametrize("source_text", ["class Broken(:\n", "class Other:\n    pass\n"])
def test_python_contract_check_fails_closed(
    tmp_path: Path,
    source_text: str,
) -> None:
    source = tmp_path / "publisher.py"
    source.write_text(source_text, encoding="utf-8")

    assert not _python_class_declares_methods(
        source,
        class_name="Publisher",
        required_methods=("publish",),
    )


def test_generator_writes_valid_source_contract_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "outbox" / "broker" / "source-contract-proof.json"

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
    assert outbox_broker_source_contract_proof_is_valid(proof) is True


def test_source_contract_gate_passes_and_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("event_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `event_id` is present"]
    assert module.validate_outbox_broker_source_contract_proof() == []


def _valid_proof() -> dict[str, Any]:
    return build_outbox_broker_source_contract_proof_payload(
        generated_at_utc=GENERATED_AT_UTC,
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts/outbox/broker/generate_source_contract_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_outbox_broker_source_contract_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts/outbox/broker/source_contract_proof_gate.py"
    spec = importlib.util.spec_from_file_location(
        "outbox_broker_source_contract_proof_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
