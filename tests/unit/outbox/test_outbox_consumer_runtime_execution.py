from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.application.outbox.consumer_runtime import (
    OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED,
    REMAINING_OUTBOX_CONSUMER_RUNTIME_BLOCKERS,
    build_outbox_consumer_runtime_execution_payload,
    outbox_consumer_runtime_execution_is_valid,
)
from scripts.outbox import consumer_runtime_execution_gate, generate_consumer_runtime_execution
from tests.unit.downstream_realization.fixtures import (
    valid_advise_intake_runtime_execution,
    valid_manage_intake_runtime_execution,
    valid_report_materialization_runtime_execution,
)

EVALUATED_AT_UTC = datetime(2026, 7, 23, 8, 0, tzinfo=UTC)


def test_builds_valid_outbox_consumer_runtime_execution_proof() -> None:
    payload = _valid_payload()

    assert payload["proofType"] == "outbox_consumer_runtime_execution"
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["runtimeProofValid"] is True
    assert tuple(cast(list[str] | tuple[str, ...], payload["aggregateBlockersSatisfied"])) == (
        OUTBOX_CONSUMER_RUNTIME_BLOCKERS_SATISFIED
    )
    assert tuple(cast(list[str] | tuple[str, ...], payload["remainingCertificationBlockers"])) == (
        REMAINING_OUTBOX_CONSUMER_RUNTIME_BLOCKERS
    )
    assert payload["consumerCoverage"] == {
        "domainConsumersCovered": ("lotus-advise", "lotus-manage", "lotus-report"),
        "gatewayWorkbenchRuntimeProofRequiredSeparately": True,
        "platformMeshPublicationProofRequiredSeparately": True,
    }
    assert payload["nonProofClaims"] == {
        "gatewayWorkbenchProofPresent": False,
        "platformMeshEventCertified": False,
        "supportedFeaturePromoted": False,
        "productionCertificationGranted": False,
        "certificationClosed": False,
    }
    assert outbox_consumer_runtime_execution_is_valid(payload)


def test_rejects_source_contract_substitution_for_consumer_runtime() -> None:
    payload = _valid_payload()
    consumer_runtime_evidence = cast(dict[str, dict[str, Any]], payload["consumerRuntimeEvidence"])
    consumer_runtime_evidence["lotus-advise"]["evidenceClass"] = "source_contract"

    assert not outbox_consumer_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("aggregateBlockersSatisfied", ["platform_mesh_event_publication_proof_missing"]),
        ("remainingCertificationBlockers", ["supported_feature_promotion_missing"]),
        ("evidenceClass", "source_contract"),
        ("runtimeProofValid", False),
    ],
)
def test_rejects_top_level_contract_drift(field_name: str, forged_value: object) -> None:
    payload = _valid_payload()
    payload[field_name] = forged_value

    assert not outbox_consumer_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("gatewayWorkbenchProofPresent", True),
        ("platformMeshEventCertified", True),
        ("supportedFeaturePromoted", True),
        ("productionCertificationGranted", True),
        ("certificationClosed", True),
    ],
)
def test_rejects_non_proof_claim_overstatement(field_name: str, forged_value: object) -> None:
    payload = _valid_payload()
    non_proof_claims = cast(dict[str, object], payload["nonProofClaims"])
    non_proof_claims[field_name] = forged_value

    assert not outbox_consumer_runtime_execution_is_valid(payload)


def test_rejects_missing_consumer_runtime_receipt() -> None:
    payload = _valid_payload()
    consumer_runtime_evidence = cast(dict[str, dict[str, Any]], payload["consumerRuntimeEvidence"])
    del consumer_runtime_evidence["lotus-report"]

    assert not outbox_consumer_runtime_execution_is_valid(payload)


def test_rejects_duplicate_consumer_runtime_refs() -> None:
    payload = build_outbox_consumer_runtime_execution_payload(
        generated_at_utc=EVALUATED_AT_UTC,
        advise_intake_runtime_execution_proof=valid_advise_intake_runtime_execution(),
        advise_intake_runtime_execution_proof_ref="output/downstream/shared.json",
        manage_intake_runtime_execution_proof=valid_manage_intake_runtime_execution(),
        manage_intake_runtime_execution_proof_ref="output/downstream/shared.json",
        report_materialization_runtime_execution_proof=(
            valid_report_materialization_runtime_execution()
        ),
        report_materialization_runtime_execution_proof_ref=(
            "output/report/materialization-runtime-execution-proof.json"
        ),
    )

    assert payload["runtimeProofValid"] is False
    assert not outbox_consumer_runtime_execution_is_valid(payload)


def test_generator_and_gate_round_trip_runtime_proof(tmp_path: Path) -> None:
    advise = _write_json(tmp_path / "advise.json", valid_advise_intake_runtime_execution())
    manage = _write_json(tmp_path / "manage.json", valid_manage_intake_runtime_execution())
    report = _write_json(tmp_path / "report.json", valid_report_materialization_runtime_execution())
    output = tmp_path / "consumer-runtime.json"

    result = generate_consumer_runtime_execution.main(
        [
            "--generated-at-utc",
            "2026-07-23T08:00:00Z",
            "--advise-intake-runtime-execution-proof",
            str(advise),
            "--manage-intake-runtime-execution-proof",
            str(manage),
            "--report-materialization-runtime-execution-proof",
            str(report),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert outbox_consumer_runtime_execution_is_valid(payload)
    assert consumer_runtime_execution_gate.main([str(output)]) == 0


def _valid_payload() -> dict[str, object]:
    return build_outbox_consumer_runtime_execution_payload(
        generated_at_utc=EVALUATED_AT_UTC,
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


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
