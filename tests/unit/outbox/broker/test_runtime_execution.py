from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from app.application.outbox.broker.runtime_execution import (
    OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED,
    OUTBOX_BROKER_RUNTIME_EXECUTION_ENV,
    REMAINING_OUTBOX_BROKER_RUNTIME_BLOCKERS,
    build_outbox_broker_runtime_execution_payload,
    outbox_broker_runtime_execution_is_valid,
)
from app.application.outbox.readiness import OUTBOX_BROKER_URL_ENV
from scripts.outbox.broker import generate_runtime_execution, runtime_execution_gate


GENERATED_AT = datetime(2026, 7, 23, 4, 45, tzinfo=UTC)


def test_outbox_broker_runtime_execution_accepts_real_publication_receipt() -> None:
    payload = valid_runtime_execution_payload()

    assert outbox_broker_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == OUTBOX_BROKER_RUNTIME_BLOCKERS_SATISFIED
    assert payload["remainingCertificationBlockers"] == REMAINING_OUTBOX_BROKER_RUNTIME_BLOCKERS
    assert payload["nonProofClaims"]["supportedFeaturePromoted"] is False  # type: ignore[index]


def test_outbox_broker_runtime_execution_builder_requires_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_outbox_broker_runtime_execution_payload(
            generated_at_utc=datetime(2026, 7, 23, 4, 45),
            broker_configured=True,
            publication_receipt=valid_receipt(),
        )


def test_outbox_broker_runtime_execution_rejects_failed_publication() -> None:
    payload = build_outbox_broker_runtime_execution_payload(
        generated_at_utc=GENERATED_AT,
        broker_configured=True,
        publication_receipt={
            **valid_receipt(),
            "outcomeAccepted": False,
            "failureReasonCode": "publisher_unavailable",
        },
    )

    assert not outbox_broker_runtime_execution_is_valid(payload)
    assert payload["runtimeChecks"]["failureReasonBounded"] is True
    assert payload["runtimeChecks"]["publicationAccepted"] is False


def test_outbox_broker_runtime_execution_rejects_overclaims() -> None:
    payload = deepcopy(valid_runtime_execution_payload())
    payload["nonProofClaims"]["platformMeshEventCertified"] = True  # type: ignore[index]

    assert not outbox_broker_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_runtime_execution_payload())
    payload["aggregateBlockersSatisfied"] = (
        "external_broker_runtime_proof_missing",
        "platform_mesh_event_publication_proof_missing",
    )

    assert not outbox_broker_runtime_execution_is_valid(payload)


def test_outbox_broker_runtime_execution_rejects_contract_drift() -> None:
    payload = deepcopy(valid_runtime_execution_payload())
    payload["evidenceClass"] = "source_contract"
    assert not outbox_broker_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_runtime_execution_payload())
    payload["evidenceRefs"] = ()
    assert not outbox_broker_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_runtime_execution_payload())
    payload["runtimeChecks"]["brokerConfigured"] = False  # type: ignore[index]
    assert not outbox_broker_runtime_execution_is_valid(payload)


def test_outbox_broker_runtime_execution_gate_validates_path(tmp_path: Path) -> None:
    proof_path = tmp_path / "outbox-broker-runtime.json"
    proof_path.write_text(json.dumps(valid_runtime_execution_payload()), encoding="utf-8")

    assert runtime_execution_gate.main([str(proof_path)]) == 0


def test_outbox_broker_runtime_execution_gate_rejects_missing_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_RUNTIME_EXECUTION_ENV, raising=False)

    assert runtime_execution_gate.main([]) == 2


def test_generate_runtime_execution_requires_configured_broker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(OUTBOX_BROKER_URL_ENV, raising=False)

    result = generate_runtime_execution.main(
        [
            "--generated-at-utc",
            "2026-07-23T04:45:00Z",
            "--output",
            str(tmp_path / "proof.json"),
        ]
    )

    assert result == 2


def valid_runtime_execution_payload() -> dict[str, object]:
    return build_outbox_broker_runtime_execution_payload(
        generated_at_utc=GENERATED_AT,
        broker_configured=True,
        publication_receipt=valid_receipt(),
    )


def valid_receipt() -> dict[str, object]:
    return {
        "outcomeAccepted": True,
        "failureReasonCode": None,
        "sourceSafeEnvelopePublished": True,
        "supportabilityStatusPublished": "not_certified",
    }
