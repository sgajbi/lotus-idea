from __future__ import annotations

import json

from scripts.ai_provider_retention_contract_gate import CONTRACT, validate_contract


def test_ai_provider_retention_consumer_contract_is_strict_and_non_promotional() -> None:
    assert validate_contract() == []

    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["persistence_migration"] == "014_ai_provider_retention_receipt"
    assert payload["authority"]["bank_lifecycle_action"] == "not_granted"
    assert payload["supported_feature_promoted"] is False
