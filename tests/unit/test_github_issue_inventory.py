from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import Any

from scripts import github_issue_inventory as inventory


def test_repository_issue_counts_include_total_open_and_label_populations(
    monkeypatch: Any,
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "data": {
                        "repository": {
                            "total": {"totalCount": 358},
                            "open": {"totalCount": 31},
                            "labeled": {"totalCount": 146},
                        }
                    }
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    counts = inventory.fetch_repository_issue_counts(
        repository="sgajbi/lotus-idea",
        label="rfc/RFC-0002",
    )

    assert counts == inventory.RepositoryIssueCounts(total=358, open=31, labeled=146)
    query = commands[0][commands[0].index("--raw-field") + 1]
    assert 'labeled: issues(labels: ["rfc/RFC-0002"])' in query


def test_repository_issue_counts_reject_malformed_graphql_payload(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": {"repository": {"total": {}}}}),
            stderr="",
        ),
    )

    try:
        inventory.fetch_repository_issue_counts(repository="sgajbi/lotus-idea")
    except ValueError as exc:
        assert str(exc) == "GitHub repository issue-count query returned an invalid payload"
    else:
        raise AssertionError("expected malformed repository issue-count payload to fail closed")


def test_complete_issue_list_uses_authoritative_count_as_limit(monkeypatch: Any) -> None:
    commands: list[list[str]] = []
    payload = [{"number": 1}, {"number": 2}]

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = inventory.fetch_complete_issue_list(
        repository="sgajbi/lotus-idea",
        state="all",
        fields="number",
        expected_count=2,
    )

    assert result == payload
    assert commands[0][commands[0].index("--limit") + 1] == "2"


def test_complete_issue_list_rejects_truncated_population(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="[]", stderr=""),
    )

    try:
        inventory.fetch_complete_issue_list(
            repository="sgajbi/lotus-idea",
            state="all",
            fields="number",
            expected_count=201,
        )
    except RuntimeError as exc:
        assert (
            str(exc) == "gh issue list returned 0 all issues for sgajbi/lotus-idea, but GitHub "
            "reports 201; complete pagination is required"
        )
    else:
        raise AssertionError("expected truncated GitHub issue population to fail closed")


def test_complete_issue_list_skips_cli_for_zero_population(monkeypatch: Any) -> None:
    def fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("subprocess must not run for a zero issue population")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    assert (
        inventory.fetch_complete_issue_list(
            repository="sgajbi/empty",
            state="all",
            fields="number",
            expected_count=0,
        )
        == []
    )
