from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository


def test_implementation_proof_readiness_payload_is_source_safe() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    payload = proof_report.implementation_proof_readiness_payload(snapshot)

    assert payload["repository"] == "lotus-idea"
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert {capability["capabilityId"] for capability in payload["capabilities"]} == {
        "source-ingestion",
        "advisor-review-queue",
        "ai-explanation",
        "data-mesh-certification",
        "runtime-trust-telemetry-preview",
        "outbox-delivery",
        "workbench-product-proof",
        "downstream-realization",
        "supported-feature-promotion",
    }
    serialized = json.dumps(payload)
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "request_body" not in serialized
    assert "response_body" not in serialized


def test_generate_implementation_proof_readiness_writes_output_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["repository"] == "lotus-idea"
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["readinessStatus"] == "blocked"


def test_generate_implementation_proof_readiness_rejects_naive_timestamp(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = proof_report.main(["--evaluated-at-utc", "2026-06-21T10:10:00"])

    assert result == 2
    assert "timezone-aware" in capsys.readouterr().err
