from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from typing import cast

import pytest

from app.domain.ai_lineage_persistence import ai_explanation_lineage_record_from_result
from app.domain.ai_execution_provenance import AIExecutionProvenancePosture
from app.domain.ai_governance import build_ai_explanation_request, evaluate_ai_workflow_output
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.ai_provider_retention import (
    AIProviderRetentionOutcome,
    VerifiedAIProviderRetentionReceipt,
)
from app.infrastructure.postgres_codecs import (
    ai_explanation_lineage_from_json,
    ai_explanation_lineage_to_json,
)
from tests.unit.test_idea_persistence import (
    ai_explanation_result_for_candidate,
    high_cash_candidate,
)
from tests.unit.test_ai_governance import candidate, command, output


def _lineage_payload() -> dict[str, object]:
    candidate, _ = high_cash_candidate()
    result = ai_explanation_result_for_candidate(candidate)
    return ai_explanation_lineage_to_json(ai_explanation_lineage_record_from_result(result))


def test_lineage_codec_round_trip_verifies_content_integrity_without_storing_output_text() -> None:
    payload = _lineage_payload()

    record = ai_explanation_lineage_from_json(
        payload,
        expected_integrity_version=str(payload["output_integrity_version"]),
        expected_content_digest=str(payload["output_content_digest"]),
    )

    assert record.output_content_digest == payload["output_content_digest"]
    assert record.execution_provenance_posture == "not_applicable_fallback"
    serialized = json.dumps(payload, sort_keys=True)
    assert "explanation_text" not in serialized
    assert "claim_text" not in serialized
    assert "action_label" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized


def test_lineage_codec_rejects_physical_column_and_json_digest_mismatch() -> None:
    payload = _lineage_payload()

    with pytest.raises(ValueError, match="content digest column mismatch"):
        ai_explanation_lineage_from_json(
            payload,
            expected_integrity_version=str(payload["output_integrity_version"]),
            expected_content_digest=f"sha256:{'f' * 64}",
        )


def test_lineage_codec_rejects_execution_provenance_column_mismatch() -> None:
    payload = _lineage_payload()

    with pytest.raises(ValueError, match="execution provenance column mismatch"):
        ai_explanation_lineage_from_json(
            payload,
            expected_execution_provenance_posture="unattested_local_test_fixture",
        )


def test_lineage_codec_rejects_integrity_version_column_mismatch() -> None:
    payload = _lineage_payload()

    with pytest.raises(ValueError, match="integrity version column mismatch"):
        ai_explanation_lineage_from_json(
            payload,
            expected_integrity_version="lotus-idea.ai-output-integrity.v2",
        )


@pytest.mark.parametrize(
    ("integrity_version", "provenance_posture"),
    [
        (
            "lotus-idea.ai-output-integrity.pre-v1-unverifiable",
            "pre_attestation_unverifiable",
        ),
        ("lotus-idea.ai-output-integrity.v1", "pre_attestation_unverifiable"),
    ],
)
def test_lineage_codec_preserves_explicit_unverifiable_migration_posture(
    integrity_version: str,
    provenance_posture: str,
) -> None:
    payload = _lineage_payload()
    payload["output_integrity_version"] = integrity_version
    payload["execution_provenance_posture"] = provenance_posture

    record = ai_explanation_lineage_from_json(payload)

    assert record.execution_provenance_posture == "pre_attestation_unverifiable"


@pytest.mark.parametrize("tampered_field", ["output_content_digest", "lineage_hash"])
def test_lineage_codec_rejects_v1_hash_tampering(tampered_field: str) -> None:
    payload = deepcopy(_lineage_payload())
    payload[tampered_field] = f"sha256:{'f' * 64}"

    with pytest.raises(ValueError, match="lineage hash does not match"):
        ai_explanation_lineage_from_json(payload)


def test_verified_attestation_receipt_round_trips_and_is_lineage_hash_bound() -> None:
    request = build_ai_explanation_request(candidate(), command())
    result = replace(
        evaluate_ai_workflow_output(request, output(request.request_id)),
        execution_provenance_posture=AIExecutionProvenancePosture.LOTUS_AI_ATTESTATION_VERIFIED,
    )
    record = ai_explanation_lineage_record_from_result(
        result,
        attestation_receipt=_verified_receipt(request.request_id),
        provider_retention_receipt=_provider_retention_receipt(),
    )
    payload = ai_explanation_lineage_to_json(record)

    restored = ai_explanation_lineage_from_json(payload)

    assert restored.attestation_receipt is not None
    assert restored.attestation_receipt.run_id == "packrun_idea_explanation_request-001"
    assert restored.attestation_receipt.replay_nonce == "a" * 64
    assert restored.provider_retention_receipt is not None
    assert restored.provider_retention_receipt.outcome is (
        AIProviderRetentionOutcome.DELETION_CONFIRMED
    )
    assert "explanation_text" not in json.dumps(payload)

    tampered = deepcopy(payload)
    cast(dict[str, object], tampered["attestation_receipt"])["replay_nonce"] = "f" * 64
    with pytest.raises(ValueError, match="lineage hash does not match"):
        ai_explanation_lineage_from_json(tampered)

    tampered_retention = deepcopy(payload)
    cast(dict[str, object], tampered_retention["provider_retention_receipt"])[
        "retention_policy_id"
    ] = "tampered-policy"
    with pytest.raises(ValueError, match="lineage hash does not match"):
        ai_explanation_lineage_from_json(tampered_retention)


def _verified_receipt(request_id: str) -> VerifiedLotusAIRunAttestationReceipt:
    verified_at = datetime(2026, 7, 11, 10, 5, tzinfo=UTC)
    return VerifiedLotusAIRunAttestationReceipt(
        run_id="packrun_idea_explanation_request-001",
        consumer_request_id=request_id,
        replay_nonce="a" * 64,
        key_id="attestation-key-1",
        rotation_epoch=1,
        provider_id="text.openai",
        provider_mode="openai",
        model_id="gpt-5.4",
        model_version="2026-06-01",
        model_risk_approval_ref="model-risk://lotus-ai/gpt-5.4/2026-06-01",
        evaluator_id="idea-explanation-guardrails",
        evaluator_policy_version="idea-explanation-policy.v1",
        input_evidence_sha256="b" * 64,
        output_content_sha256="c" * 64,
        issued_at_utc=verified_at - timedelta(seconds=5),
        expires_at_utc=verified_at + timedelta(minutes=5),
        verified_at_utc=verified_at,
    )


def _provider_retention_receipt() -> VerifiedAIProviderRetentionReceipt:
    verified_at = datetime(2026, 7, 11, 10, 5, tzinfo=UTC)
    return VerifiedAIProviderRetentionReceipt(
        confirmation_id="provider-retention-001",
        workflow_run_id="packrun_idea_explanation_request-001",
        tenant_id="tenant-private-bank-sg",
        provider_confirmation_ref="provider-confirmation-001",
        retention_policy_id="idea-provider-zero-retention-v1",
        outcome=AIProviderRetentionOutcome.DELETION_CONFIRMED,
        evidence_sha256="e" * 64,
        provider_failure_code=None,
        deletion_confirmed=True,
        supportability_status="READY",
        replay_nonce="d" * 64,
        key_id="attestation-key-1",
        rotation_epoch=1,
        provider_decision_at_utc=verified_at - timedelta(seconds=10),
        issued_at_utc=verified_at - timedelta(seconds=5),
        expires_at_utc=verified_at + timedelta(minutes=5),
        verified_at_utc=verified_at,
    )
