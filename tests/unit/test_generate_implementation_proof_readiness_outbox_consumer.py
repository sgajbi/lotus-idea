from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report

from app.application.outbox.consumer_runtime import (
    build_outbox_consumer_runtime_execution_payload,
)
from tests.unit.downstream_realization.fixtures import (
    valid_advise_intake_runtime_execution,
    valid_manage_intake_runtime_execution,
    valid_report_materialization_runtime_execution,
)


def test_generate_implementation_proof_readiness_uses_outbox_consumer_runtime_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.application.proof_provenance.source_tree_dirty", lambda _: False)
    proof_path = tmp_path / "outbox-consumer-runtime-execution-proof.json"
    proof_path.write_text(
        json.dumps(
            build_outbox_consumer_runtime_execution_payload(
                generated_at_utc=datetime(2026, 7, 23, 8, 0, tzinfo=UTC),
                advise_intake_runtime_execution_proof=valid_advise_intake_runtime_execution(),
                advise_intake_runtime_execution_proof_ref=(
                    "output/downstream/advise-intake-runtime-execution-proof.json"
                ),
                manage_intake_runtime_execution_proof=valid_manage_intake_runtime_execution(),
                manage_intake_runtime_execution_proof_ref=(
                    "output/downstream/manage-intake-runtime-execution-proof.json"
                ),
                report_materialization_runtime_execution_proof=(
                    valid_report_materialization_runtime_execution()
                ),
                report_materialization_runtime_execution_proof_ref=(
                    "output/report/materialization-runtime-execution-proof.json"
                ),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-07-23T08:00:00Z",
            "--outbox-consumer-runtime-execution-proof",
            str(proof_path),
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
    assert "downstream_consumer_runtime_proof_missing" not in outbox_delivery["blockers"]
    assert "external_broker_runtime_proof_missing" in outbox_delivery["blockers"]
    assert "platform_mesh_event_publication_proof_missing" in outbox_delivery["blockers"]
    assert "gateway_workbench_proof_missing" in outbox_delivery["blockers"]
    assert "supported_feature_promotion_missing" in payload["overallBlockers"]
