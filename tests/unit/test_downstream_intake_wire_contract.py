from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.domain import ConversionTarget, SourceSystem
from app.infrastructure.downstream_realization import (
    AdviseRealizationServiceContext,
    ManageRealizationServiceContext,
    ReportRealizationServiceContext,
    _conversion_intent_envelope,
    _report_evidence_pack_materialization_envelope,
)

from tests.unit.test_downstream_realization_adapters import (
    conversion_intent,
    report_access_scope,
    report_evidence_pack,
)


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
        legal_entity_code="SGPB",
        service_identity="lotus-idea-local-development",
        capabilities="manage.write",
    )

    assert set(context.request_headers()) == set(contract["required_server_headers"])
    assert contract["receipt_outcomes"] == ["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
    assert contract["local_dev_principal_source"] == (
        "trusted_headers_until_production_idp_available"
    )


def test_advise_service_context_matches_versioned_wire_contract() -> None:
    contract = _consumer_contract(ConversionTarget.ADVISE_PROPOSAL.value)
    context = AdviseRealizationServiceContext(
        actor_id="lotus-idea-local-development",
        role="SERVICE",
        tenant_id="tenant-sg",
        legal_entity_code="SGPB",
        service_identity="lotus-idea-local-development",
        capabilities=contract["principal_capability"],
    )

    assert set(context.request_headers()) == set(contract["required_server_headers"])
    assert contract["receipt_outcomes"] == ["ACCEPTED", "ACCEPTED_REPLAYED", "REJECTED"]
    assert contract["local_dev_principal_source"] == (
        "trusted_headers_until_production_idp_available"
    )


def test_report_adapter_envelope_matches_versioned_wire_contract() -> None:
    contract = _consumer_contract("report_evidence")
    envelope = _report_evidence_pack_materialization_envelope(
        report_evidence_pack(),
        access_scope=report_access_scope(),
        service_context=ReportRealizationServiceContext(
            actor_id="lotus-idea-local-development",
            caller_application="lotus-idea",
            tenant_id=contract["local_test_service_context"]["tenant_id"],
            region=contract["local_test_service_context"]["region"],
            requested_output_formats=tuple(
                contract["local_test_service_context"]["output_formats"]
            ),
        ),
    )

    assert set(envelope) == set(contract["request_fields"])
    assert set(envelope["idea_evidence_pack"]) == set(contract["idea_evidence_pack_fields"])
    assert (
        envelope["idea_evidence_pack"]["purpose"]
        == contract["purpose_mapping"]["client_review_report_section"]
    )
    assert (
        envelope["idea_evidence_pack"]["retention_policy_ref"]
        == contract["owner_retention_policy_mapping"]["lotus-report:idea-evidence-retention:v1"]
    )
    assert envelope["boundary"] == contract["boundary"]
    assert envelope["grants_client_publication_authority"] is False
    assert envelope["requested_output_formats"] == ["json"]
    assert "content_hash" not in str(envelope)


def test_report_service_context_matches_versioned_wire_contract() -> None:
    contract = _consumer_contract("report_evidence")
    context = ReportRealizationServiceContext(
        actor_id="lotus-idea-local-development",
        caller_application="lotus-idea",
        tenant_id=contract["local_test_service_context"]["tenant_id"],
        region=contract["local_test_service_context"]["region"],
        requested_output_formats=tuple(contract["local_test_service_context"]["output_formats"]),
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
