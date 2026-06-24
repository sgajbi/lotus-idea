from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.outbox_broker_proof import (
    OUTBOX_BROKER_BLOCKERS_CLEARED,
    OUTBOX_BROKER_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS,
    REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS,
    build_outbox_broker_proof_payload,
    outbox_broker_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_outbox_broker_proof() -> None:
    proof = _valid_outbox_broker_proof()

    assert proof["schemaVersion"] == OUTBOX_BROKER_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "outbox_broker_runtime_contract"
    assert proof["proofScope"] == "bounded_configured_publisher_runtime_proof"
    assert proof["outboxBrokerProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == OUTBOX_BROKER_BLOCKERS_CLEARED
    assert tuple(proof["evidenceRefs"]) == REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS
    )
    assert proof["externalBrokerPublicationSupported"] is False
    assert proof["platformMeshEventCertified"] is False
    assert proof["downstreamConsumersCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert outbox_broker_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "idea_high_cash_001" not in serialized
    assert "eventId" not in serialized
    assert "aggregateId" not in serialized
    assert "idempotency" not in serialized


def test_rejects_outbox_broker_proof_when_evidence_is_missing(tmp_path: Path) -> None:
    proof = build_outbox_broker_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
    )

    assert proof["outboxBrokerProofValid"] is False
    assert outbox_broker_proof_is_valid(proof) is False


def test_rejects_outbox_broker_proof_with_naive_timestamp() -> None:
    proof = build_outbox_broker_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert proof["outboxBrokerProofValid"] is False
    assert outbox_broker_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "outbox"),
        ("proofScope", "production_broker"),
        ("outboxBrokerProofValid", False),
        ("externalBrokerPublicationSupported", True),
        ("platformMeshEventCertified", True),
        ("downstreamConsumersCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_outbox_broker_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_outbox_broker_proof()
    proof[field_name] = bad_value

    assert outbox_broker_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
    ],
)
def test_rejects_outbox_broker_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_outbox_broker_proof()
    proof[field_name] = bad_value

    assert outbox_broker_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "configuredPublisherRuntimeExercised",
    ],
)
def test_rejects_outbox_broker_proof_with_invalid_proof_checks(check_name: str) -> None:
    proof = _valid_outbox_broker_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert outbox_broker_proof_is_valid(proof) is False


def test_outbox_broker_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "outbox-broker-proof.json"

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
    assert outbox_broker_proof_is_valid(proof) is True


def test_outbox_broker_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("event_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `event_id` is present"]


def _valid_outbox_broker_proof() -> dict[str, Any]:
    return build_outbox_broker_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_outbox_broker_proof.py"
    spec = importlib.util.spec_from_file_location("generate_outbox_broker_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "outbox_broker_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location("outbox_broker_proof_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
