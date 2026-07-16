from __future__ import annotations

import json
from pathlib import Path

from app.api.candidate_evidence_replay import CandidateEvidenceReplayResponse
from app.api.candidate_lifecycle import CandidateLifecycleTransitionResponse
from app.api.examples.candidate_state import (
    CANDIDATE_EVIDENCE_REPLAY_OPERATION_PATH,
    CANDIDATE_LIFECYCLE_OPERATION_PATH,
    build_candidate_evidence_replay_response_examples,
    build_candidate_lifecycle_response_examples,
)
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")


def test_candidate_lifecycle_success_examples_match_ledger_and_openapi() -> None:
    expected = build_candidate_lifecycle_response_examples()

    assert _ledger_examples(CANDIDATE_LIFECYCLE_OPERATION_PATH) == list(expected.values())
    assert _openapi_examples(CANDIDATE_LIFECYCLE_OPERATION_PATH) == expected
    assert all(
        CandidateLifecycleTransitionResponse.model_validate(value) for value in expected.values()
    )

    assert expected["accepted"]["transition"] is not None
    assert expected["accepted"]["persistence"]["decision"] == "accepted"
    assert expected["accepted"]["transition"]["grantsDownstreamAuthority"] is False
    assert expected["replayed"]["transition"] is None
    assert expected["replayed"]["persistence"]["decision"] == "replayed"
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())


def test_candidate_evidence_replay_success_examples_match_ledger_and_openapi() -> None:
    expected = build_candidate_evidence_replay_response_examples()

    assert _ledger_examples(CANDIDATE_EVIDENCE_REPLAY_OPERATION_PATH) == list(expected.values())
    assert _openapi_examples(CANDIDATE_EVIDENCE_REPLAY_OPERATION_PATH) == expected
    assert all(CandidateEvidenceReplayResponse.model_validate(value) for value in expected.values())

    assert tuple(expected) == ("matched", "hashMismatch", "staleSource", "expired")
    assert expected["matched"]["currentEvidenceHash"] == expected["matched"]["recordedEvidenceHash"]
    assert (
        expected["hashMismatch"]["currentEvidenceHash"]
        != expected["hashMismatch"]["recordedEvidenceHash"]
    )
    assert expected["staleSource"]["currentEvidenceHash"] is None
    assert expected["expired"]["currentEvidenceHash"] is None
    assert all(value["grantsDownstreamAuthority"] is False for value in expected.values())
    assert all(value["supportedFeaturePromoted"] is False for value in expected.values())
    assert all("route" not in value and "contentHash" not in value for value in expected.values())


def _ledger_examples(operation_path: str) -> list[dict[str, object]]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    endpoint = next(
        item
        for item in ledger["endpoints"]
        if item["method"] == "POST" and item["path"] == operation_path
    )
    return [json.loads(value) for value in endpoint["response_examples"]]


def _openapi_examples(operation_path: str) -> dict[str, dict[str, object]]:
    operation = app.openapi()["paths"][operation_path]["post"]
    examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
