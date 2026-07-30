from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _load_module() -> ModuleType:
    script_path = ROOT / "scripts" / "cross_repo_issue_posture.py"
    spec = importlib.util.spec_from_file_location("cross_repo_issue_posture", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _issue(
    number: int,
    *,
    state: str,
    title: str,
    labels: list[str],
    repo: str = "lotus-idea",
) -> dict[str, Any]:
    return {
        "number": number,
        "state": state,
        "title": title,
        "url": f"https://github.com/sgajbi/{repo}/issues/{number}",
        "updatedAt": "2026-07-29T00:00:00Z",
        "labels": [{"name": label} for label in labels],
    }


def _write_fixture(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "issues.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_blocker_classification(
    tmp_path: Path,
    classifications: list[dict[str, Any]],
) -> Path:
    path = tmp_path / "blocker-classification.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": "lotus-idea:rfc0002-cross-repo-blocker-classification:v1",
                "rfcId": "RFC-0002",
                "classifications": classifications,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _classification(
    number: int,
    *,
    repo: str = "lotus-idea",
    actionability: str = "external_or_protected_evidence",
    blocker_class: str = "protected_evidence",
) -> dict[str, Any]:
    return {
        "repository": f"sgajbi/{repo}",
        "issueNumber": number,
        "actionability": actionability,
        "blockerClass": blocker_class,
        "remainingAuthority": "test authority boundary",
    }


def test_cross_repo_issue_posture_counts_statuses_and_attention_issues(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        {
            "sgajbi/lotus-idea": {
                "openIssues": [
                    _issue(681, state="OPEN", title="Slice 18 docs", labels=[]),
                    _issue(685, state="OPEN", title="Workbench proof", labels=[]),
                ],
                "rfc0002Issues": [
                    _issue(
                        681,
                        state="OPEN",
                        title="Slice 18 docs",
                        labels=[
                            "rfc/RFC-0002",
                            "rfc/RFC-0002/slice-18",
                            "status/in-progress",
                            "priority/P1",
                        ],
                    ),
                    _issue(
                        685,
                        state="OPEN",
                        title="Workbench proof",
                        labels=[
                            "rfc/RFC-0002",
                            "rfc/RFC-0002/slice-11",
                            "status/blocked",
                            "priority/P0",
                        ],
                    ),
                    _issue(
                        340,
                        state="CLOSED",
                        title="AI proof",
                        labels=["rfc/RFC-0002", "status/merged-main"],
                    ),
                ],
            },
            "sgajbi/lotus-platform": {
                "openIssues": [
                    _issue(
                        598,
                        state="OPEN",
                        title="Platform mesh proof",
                        labels=[],
                        repo="lotus-platform",
                    ),
                    _issue(42, state="OPEN", title="Other", labels=[], repo="lotus-platform"),
                ],
                "rfc0002Issues": [
                    _issue(
                        598,
                        state="OPEN",
                        title="Platform mesh proof",
                        labels=[
                            "rfc/RFC-0002",
                            "rfc/RFC-0002/slice-14",
                            "status/merged-main",
                            "priority/P1",
                        ],
                        repo="lotus-platform",
                    )
                ],
            },
        },
    )
    blocker_classification = _write_blocker_classification(
        tmp_path,
        [_classification(685, blocker_class="canonical_workbench_runtime_core_readiness")],
    )

    summary = module.build_cross_repo_issue_posture(
        repositories=("sgajbi/lotus-idea", "sgajbi/lotus-platform"),
        fixture_path=fixture,
        blocker_classification_path=blocker_classification,
    )

    assert summary["schemaVersion"] == "lotus-idea:rfc0002-cross-repo-issue-posture:v1"
    assert summary["totalOpenIssuesAcrossRepositories"] == 4
    assert summary["counts"]["repositories"] == 2
    assert summary["counts"]["openRfc0002Issues"] == 3
    assert summary["counts"]["closedRfc0002Issues"] == 1
    assert summary["counts"]["openRfc0002IssuesByStatus"] == {
        "status/blocked": 1,
        "status/in-progress": 1,
        "status/merged-main": 1,
    }
    assert summary["blockedActionability"]["openBlockedIssueCount"] == 1
    assert summary["blockedActionability"]["appActionableBlockedIssueCount"] == 0
    assert summary["blockedActionability"]["openBlockedIssuesByClass"] == {
        "canonical_workbench_runtime_core_readiness": 1
    }
    assert [issue["repository"] for issue in summary["openAttentionIssues"]] == [
        "lotus-idea",
        "lotus-platform",
    ]
    assert [issue["number"] for issue in summary["openAttentionIssues"]] == [681, 598]


def test_cross_repo_issue_posture_markdown_is_comment_ready(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        {
            "sgajbi/lotus-idea": {
                "openIssues": [_issue(681, state="OPEN", title="Slice 18 docs", labels=[])],
                "rfc0002Issues": [
                    _issue(
                        681,
                        state="OPEN",
                        title="Slice 18 docs",
                        labels=["rfc/RFC-0002", "status/in-progress"],
                    )
                ],
            }
        },
    )
    blocker_classification = _write_blocker_classification(tmp_path, [])

    rendered = module.render_markdown(
        module.build_cross_repo_issue_posture(
            repositories=("sgajbi/lotus-idea",),
            fixture_path=fixture,
            blocker_classification_path=blocker_classification,
        )
    )

    assert "# RFC-0002 Cross-Repo Issue Posture" in rendered
    assert "- Open RFC-0002 issues: 1" in rendered
    assert "| `sgajbi/lotus-idea` | 1 | 1 | 0 | `status/in-progress` 1 |" in rendered
    assert "- App-actionable blocked issues: 0" in rendered
    assert "`lotus-idea#681` `status/in-progress` Slice 18 docs" in rendered
    assert "not product-support evidence" in rendered


def test_cross_repo_issue_posture_rejects_missing_repo_fixture(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, {})
    blocker_classification = _write_blocker_classification(tmp_path, [])

    try:
        module.build_cross_repo_issue_posture(
            repositories=("sgajbi/lotus-idea",),
            fixture_path=fixture,
            blocker_classification_path=blocker_classification,
        )
    except ValueError as exc:
        assert "missing repository payload for sgajbi/lotus-idea" in str(exc)
    else:
        raise AssertionError("expected missing repository fixture to fail")


def test_default_repository_scope_covers_governed_rfc0002_owner_dependencies() -> None:
    module = _load_module()

    assert module.DEFAULT_REPOSITORIES == (
        "sgajbi/lotus-idea",
        "sgajbi/lotus-core",
        "sgajbi/lotus-performance",
        "sgajbi/lotus-risk",
        "sgajbi/lotus-advise",
        "sgajbi/lotus-manage",
        "sgajbi/lotus-report",
        "sgajbi/lotus-render",
        "sgajbi/lotus-archive",
        "sgajbi/lotus-ai",
        "sgajbi/lotus-platform",
        "sgajbi/lotus-gateway",
        "sgajbi/lotus-workbench",
    )


def test_cross_repo_issue_posture_requires_classification_for_open_blocked_issue(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        {
            "sgajbi/lotus-idea": {
                "openIssues": [_issue(685, state="OPEN", title="Workbench proof", labels=[])],
                "rfc0002Issues": [
                    _issue(
                        685,
                        state="OPEN",
                        title="Workbench proof",
                        labels=["rfc/RFC-0002", "status/blocked"],
                    )
                ],
            }
        },
    )
    blocker_classification = _write_blocker_classification(tmp_path, [])

    try:
        module.build_cross_repo_issue_posture(
            repositories=("sgajbi/lotus-idea",),
            fixture_path=fixture,
            blocker_classification_path=blocker_classification,
        )
    except ValueError as exc:
        assert (
            "open blocked RFC-0002 issues missing blocker classification: sgajbi/lotus-idea#685"
        ) in str(exc)
    else:
        raise AssertionError("expected missing blocked classification to fail")


def test_cross_repo_issue_posture_rejects_stale_classification_for_scoped_repo(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        {
            "sgajbi/lotus-idea": {
                "openIssues": [_issue(681, state="OPEN", title="Slice 18 docs", labels=[])],
                "rfc0002Issues": [
                    _issue(
                        681,
                        state="OPEN",
                        title="Slice 18 docs",
                        labels=["rfc/RFC-0002", "status/in-progress"],
                    )
                ],
            }
        },
    )
    blocker_classification = _write_blocker_classification(
        tmp_path,
        [_classification(685)],
    )

    try:
        module.build_cross_repo_issue_posture(
            repositories=("sgajbi/lotus-idea",),
            fixture_path=fixture,
            blocker_classification_path=blocker_classification,
        )
    except ValueError as exc:
        assert (
            "blocker classification contract contains stale non-open-blocked issue(s): "
            "sgajbi/lotus-idea#685"
        ) in str(exc)
    else:
        raise AssertionError("expected stale blocked classification to fail")


def test_default_blocker_classification_tracks_manage_tax_lot_seed_boundary() -> None:
    contract_path = (
        ROOT
        / "contracts"
        / "implementation-proof"
        / ("rfc0002-cross-repo-blocker-classification.v1.json")
    )
    payload = json.loads(contract_path.read_text(encoding="utf-8"))

    matching_rows = [
        row
        for row in payload["classifications"]
        if row["repository"] == "sgajbi/lotus-manage" and row["issueNumber"] == 626
    ]

    assert matching_rows == [
        {
            "repository": "sgajbi/lotus-manage",
            "issueNumber": 626,
            "actionability": "core_dependency",
            "blockerClass": "canonical_dpm_seed_runtime_core_readiness",
            "remainingAuthority": (
                "Core-owned canonical DPM source readiness and governed Platform "
                "command-center seed runtime evidence for PB_SG_GLOBAL_BAL_001 after "
                "the Manage tax-lot identity fix merged"
            ),
        }
    ]
