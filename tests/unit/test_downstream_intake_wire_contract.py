from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.domain import ConversionTarget, SourceSystem
from app.infrastructure.downstream_realization import (
    ManageRealizationServiceContext,
    _conversion_intent_envelope,
)

from tests.unit.test_downstream_realization_adapters import conversion_intent


ROOT = Path(__file__).resolve().parents[2]
WIRE_CONTRACT_PATH = (
    ROOT / "contracts/downstream-realization/lotus-idea-downstream-intake-wire-contract.v1.json"
)


@pytest.mark.parametrize(
    ("target", "authority"),
    [
        (ConversionTarget.ADVISE_PROPOSAL, SourceSystem.LOTUS_ADVISE),
        (ConversionTarget.MANAGE_REVIEW, SourceSystem.LOTUS_MANAGE),
    ],
)
def test_conversion_intent_adapter_envelope_matches_versioned_wire_contract(
    target: ConversionTarget,
    authority: SourceSystem,
) -> None:
    contract = _consumer_contract(target.value)
    envelope = _conversion_intent_envelope(conversion_intent(target, authority))

    assert set(envelope) == set(contract["request_fields"])
    assert envelope["intent_type"] == contract["intent_type"]
    assert envelope["source_system"] == "lotus-idea"
    assert envelope["source_refs"] == [
        {
            "source_system": "lotus-idea",
            "source_type": "IdeaCandidate",
            "source_id": "idea_high_cash_redacted",
            "content_hash": "sha256:evidence-redacted",
        }
    ]


def test_manage_service_context_matches_versioned_wire_contract() -> None:
    contract = _consumer_contract(ConversionTarget.MANAGE_REVIEW.value)
    context = ManageRealizationServiceContext(
        actor_id="lotus-idea-local-development",
        role="service",
        tenant_id="local-development",
        service_identity="lotus-idea-local-development",
        capabilities="manage.write",
    )

    assert set(context.request_headers()) == set(contract["required_server_headers"])


def _consumer_contract(target: str) -> dict[str, Any]:
    payload = json.loads(WIRE_CONTRACT_PATH.read_text(encoding="utf-8"))
    consumers = payload.get("consumer_contracts")
    if not isinstance(consumers, list):
        raise AssertionError("wire contract consumer_contracts must be a list")
    for contract in consumers:
        if isinstance(contract, dict) and contract.get("conversion_target") == target:
            return contract
    raise AssertionError(f"missing wire contract for {target}")
