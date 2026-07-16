from __future__ import annotations

import json
from pathlib import Path

from app.api.examples.report_evidence import (
    REPORT_EVIDENCE_PACK_OPERATION_PATH,
    build_report_evidence_pack_response_examples,
)
from app.api.report_evidence import ReportEvidencePackApiResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")


def test_report_evidence_pack_success_examples_match_ledger_and_openapi() -> None:
    expected = build_report_evidence_pack_response_examples()

    assert _ledger_examples() == list(expected.values())
    assert _openapi_examples() == expected
    assert all(ReportEvidencePackApiResponse.model_validate(value) for value in expected.values())

    evidence_pack = expected["accepted"]["reportEvidencePack"]
    assert evidence_pack is not None
    assert evidence_pack["grantsClientPublicationAuthority"] is False
    assert evidence_pack["createsRenderedOutput"] is False
    assert evidence_pack["createsArchiveRecord"] is False
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["replayed"]["reportEvidencePack"] is None
    assert expected["replayed"]["persistence"]["decision"] == "replayed"
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())


def _ledger_examples() -> list[dict[str, object]]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    endpoint = next(
        item
        for item in ledger["endpoints"]
        if item["method"] == "POST" and item["path"] == REPORT_EVIDENCE_PACK_OPERATION_PATH
    )
    return [json.loads(value) for value in endpoint["response_examples"]]


def _openapi_examples() -> dict[str, dict[str, object]]:
    operation = app.openapi()["paths"][REPORT_EVIDENCE_PACK_OPERATION_PATH]["post"]
    examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
