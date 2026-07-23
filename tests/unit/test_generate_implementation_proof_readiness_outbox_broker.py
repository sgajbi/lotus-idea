from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report

from app.application.outbox.broker.source_contract_proof import (
    build_outbox_broker_source_contract_proof_payload,
)
from app.application.outbox.broker.runtime_execution import (
    build_outbox_broker_runtime_execution_payload,
)


def test_generate_implementation_proof_readiness_uses_explicit_outbox_broker_source_contract_proof(
    tmp_path: Path,
) -> None:
    outbox_proof = tmp_path / "outbox-broker-source-contract-proof.json"
    outbox_proof.write_text(
        json.dumps(
            build_outbox_broker_source_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--outbox-broker-source-contract-proof",
            str(outbox_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "outbox_broker_not_configured" in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" in payload["overallBlockers"]
    assert "downstream_consumer_runtime_proof_missing" in payload["overallBlockers"]
    assert "platform_mesh_event_publication_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_outbox_broker_runtime_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.proof_provenance.source_tree_dirty", lambda _: False)
    outbox_proof = tmp_path / "outbox-broker-runtime-execution-proof.json"
    outbox_proof.write_text(
        json.dumps(
            build_outbox_broker_runtime_execution_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                broker_configured=True,
                publication_receipt={
                    "outcomeAccepted": True,
                    "failureReasonCode": None,
                    "sourceSafeEnvelopePublished": True,
                    "supportabilityStatusPublished": "not_certified",
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--outbox-broker-runtime-execution-proof",
            str(outbox_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    outbox_delivery = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "outbox-delivery"
    )
    assert "external_broker_runtime_proof_missing" not in outbox_delivery["blockers"]
    assert "outbox_broker_not_configured" in outbox_delivery["blockers"]
    assert "downstream_consumer_runtime_proof_missing" in outbox_delivery["blockers"]
    assert "platform_mesh_event_publication_proof_missing" in outbox_delivery["blockers"]
    assert "supported_feature_promotion_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
