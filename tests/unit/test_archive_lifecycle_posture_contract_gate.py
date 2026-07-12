from __future__ import annotations

import json

import pytest

from scripts.archive_lifecycle_posture_contract_gate import CONTRACT, validate_contract


def test_archive_lifecycle_consumer_contract_is_strict_and_non_promotional() -> None:
    assert validate_contract() == []

    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["persistence"]["migration"] == "015_archive_lifecycle_posture_receipt"
    assert payload["authority"]["bank_lifecycle_action"] == (
        "independent_signed_authority_required"
    )
    assert payload["policy"]["purge_requires_archive_action"] == "DISPOSAL_EXECUTED"
    assert payload["supported_feature_promoted"] is False


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            lambda payload: payload["verification_controls"].update(
                {"maximum_ttl_seconds": 3600}
            ),
            "Archive receipt verification controls must remain strict and source-bound",
        ),
        (
            lambda payload: payload["policy"].update(
                {"purge_requires_archive_action": "DISPOSAL_ELIGIBLE"}
            ),
            "Archive hold, purge, and unlinked-candidate policy must remain fail closed",
        ),
        (
            lambda payload: payload["authority"].update(
                {"archive_disposal_authority": "granted"}
            ),
            "consumer must preserve bank, Archive, Report, and Idea authority boundaries",
        ),
        (
            lambda payload: payload["source_safety"].update({"raw_document_included": True}),
            "Archive posture receipt must exclude document, evidence, and client content",
        ),
        (
            lambda payload: payload["persistence"].update(
                {"blocked_attempt_consumes_receipt": True}
            ),
            "migration 015 and applied-only decision/digest replay fencing are required",
        ),
    ],
)
def test_archive_lifecycle_contract_gate_rejects_weakened_controls(
    tmp_path, mutation, expected_error: str
) -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    mutation(payload)
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps(payload), encoding="utf-8")

    assert expected_error in validate_contract(contract)
