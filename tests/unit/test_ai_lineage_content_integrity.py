from __future__ import annotations

from copy import deepcopy
import json

import pytest

from app.domain.ai_lineage_persistence import ai_explanation_lineage_record_from_result
from app.infrastructure.postgres_codecs import (
    ai_explanation_lineage_from_json,
    ai_explanation_lineage_to_json,
)
from tests.unit.test_idea_persistence import (
    ai_explanation_result_for_candidate,
    high_cash_candidate,
)


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


@pytest.mark.parametrize("tampered_field", ["output_content_digest", "lineage_hash"])
def test_lineage_codec_rejects_v1_hash_tampering(tampered_field: str) -> None:
    payload = deepcopy(_lineage_payload())
    payload[tampered_field] = f"sha256:{'f' * 64}"

    with pytest.raises(ValueError, match="lineage hash does not match"):
        ai_explanation_lineage_from_json(payload)
