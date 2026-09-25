from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import select_downstream_capacity_resource as cli


class StubAdapter:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def fetch_candidate_detail(self, **kwargs: str) -> dict[str, object]:
        return {
            "candidate": {
                "candidateId": kwargs["candidate_id"],
                "identity": {"materialVersion": 1, "evidenceVersion": 1},
            },
            "evidence": {"sourceCutPosture": "coherent"},
            "conversionIntents": [
                {
                    "conversionIntentId": "conversion-current-001",
                    "target": "advise_proposal",
                    "acceptedAtUtc": "2026-09-25T06:00:01Z",
                    "targetSourceAuthority": "lotus-advise",
                    "boundary": "intent_only",
                    "reasonCodes": ["review_approved_for_conversion"],
                    "reviewId": "review-001",
                    "reviewChannel": "workbench",
                    "reviewPolicyVersion": "idea-human-review-v1",
                    "authorityPolicyVersion": "idea-review-authority-v1",
                    "presentationReceiptId": "receipt-001",
                    "candidateMaterialVersion": 1,
                    "candidateEvidenceVersion": 1,
                    "grantsDownstreamAuthority": False,
                }
            ],
        }

    def close(self) -> None:
        pass


def test_cli_writes_current_authoritative_resource_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "HttpDownstreamCapacityResource", StubAdapter)
    output = tmp_path / "capacity-resource.json"

    result = cli.main(
        [
            "--base-url",
            "https://idea.example",
            "--candidate-id",
            "idea-001",
            "--tenant-id",
            "tenant-sg",
            "--book-id",
            "book-sg",
            "--portfolio-id",
            "portfolio-sg",
            "--client-id",
            "client-sg",
            "--commit-sha",
            "a" * 40,
            "--branch",
            "main",
            "--run-id",
            "canonical-run-001",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["conversionIntentId"] == "conversion-current-001"
    assert payload["syntheticResource"] is False


def test_cli_accepts_an_explicit_aware_authority_cutoff(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "HttpDownstreamCapacityResource", StubAdapter)

    result = cli.main(
        [
            "--base-url",
            "https://idea.example",
            "--candidate-id",
            "idea-001",
            "--tenant-id",
            "tenant-sg",
            "--book-id",
            "book-sg",
            "--portfolio-id",
            "portfolio-sg",
            "--client-id",
            "client-sg",
            "--accepted-not-before-utc",
            "2026-09-25T06:00:00Z",
            "--commit-sha",
            "a" * 40,
            "--branch",
            "main",
            "--run-id",
            "canonical-run-001",
            "--output",
            str(tmp_path / "out.json"),
        ]
    )

    assert result == 0


def test_cli_rejects_naive_authority_cutoff_before_http(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli, "HttpDownstreamCapacityResource", StubAdapter)

    with pytest.raises(SystemExit):
        cli.main(
            [
                "--base-url",
                "https://idea.example",
                "--candidate-id",
                "idea-001",
                "--tenant-id",
                "tenant-sg",
                "--book-id",
                "book-sg",
                "--portfolio-id",
                "portfolio-sg",
                "--client-id",
                "client-sg",
                "--accepted-not-before-utc",
                "2026-09-25T06:00:00",
                "--commit-sha",
                "a" * 40,
                "--branch",
                "main",
                "--run-id",
                "canonical-run-001",
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
