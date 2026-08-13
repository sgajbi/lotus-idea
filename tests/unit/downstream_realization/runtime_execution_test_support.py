from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def nested_payload_section(
    payload: Mapping[str, object],
    section_name: str,
) -> dict[str, object]:
    section = payload.get(section_name)
    assert isinstance(section, dict), f"{section_name} must be a JSON object"
    return section


def receipt_evidence_for_builder(
    payload: Mapping[str, object],
) -> dict[str, Mapping[str, Any]]:
    receipt_evidence = nested_payload_section(payload, "receiptEvidence")
    typed_evidence: dict[str, Mapping[str, Any]] = {}
    for receipt_name, receipt_payload in receipt_evidence.items():
        assert isinstance(receipt_payload, dict), (
            f"receiptEvidence.{receipt_name} must be a JSON object"
        )
        typed_evidence[receipt_name] = receipt_payload
    return typed_evidence


def set_nested_payload_value(
    payload: Mapping[str, object],
    section_name: str,
    field_name: str,
    value: object,
) -> None:
    nested_payload_section(payload, section_name)[field_name] = value


def set_receipt_evidence_value(
    payload: Mapping[str, object],
    receipt_name: str,
    field_name: str,
    value: object,
) -> None:
    receipt_evidence = nested_payload_section(payload, "receiptEvidence")
    receipt_payload = receipt_evidence.get(receipt_name)
    assert isinstance(receipt_payload, dict), (
        f"receiptEvidence.{receipt_name} must be a JSON object"
    )
    receipt_payload[field_name] = value
