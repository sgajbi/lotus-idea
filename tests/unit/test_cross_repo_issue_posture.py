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
                "allIssues": [
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
                        563,
                        state="CLOSED",
                        title="RFC-0002 Slice 10: certify high-volatility success-mode contracts",
                        labels=["status/merged-main"],
                    ),
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
                "allIssues": [
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
    assert summary["titleOnlyRfc0002References"] == [
        {
            "number": 563,
            "title": "RFC-0002 Slice 10: certify high-volatility success-mode contracts",
            "url": "https://github.com/sgajbi/lotus-idea/issues/563",
            "updatedAt": "2026-07-29T00:00:00Z",
            "status": "status/merged-main",
            "priorityLabels": [],
            "sliceLabels": [],
            "repository": "lotus-idea",
        }
    ]
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
    assert summary["blockedActionability"]["openBlockedIssues"] == [
        {
            "number": 685,
            "title": "Workbench proof",
            "url": "https://github.com/sgajbi/lotus-idea/issues/685",
            "updatedAt": "2026-07-29T00:00:00Z",
            "status": "status/blocked",
            "priorityLabels": ["priority/P0"],
            "sliceLabels": ["rfc/RFC-0002/slice-11"],
            "repository": "lotus-idea",
            "actionability": "external_or_protected_evidence",
            "blockerClass": "canonical_workbench_runtime_core_readiness",
            "remainingAuthority": "test authority boundary",
        }
    ]
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
                "allIssues": [
                    _issue(
                        681,
                        state="OPEN",
                        title="Slice 18 docs",
                        labels=["rfc/RFC-0002", "status/in-progress"],
                    ),
                    _issue(
                        555,
                        state="CLOSED",
                        title="RFC-0002 Slice 10: certify bond-maturity success-mode contracts",
                        labels=["status/merged-main"],
                    ),
                ],
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
    assert "### Blocked Issue Detail" in rendered
    assert "_None._" in rendered
    assert "Classification boundary: A zero app-actionable blocked count means" in rendered
    assert "Title-Only RFC-0002 References Excluded From Governed Counts" in rendered
    assert "`lotus-idea#555` `status/merged-main`" in rendered
    assert "`lotus-idea#681` `status/in-progress` Slice 18 docs" in rendered
    assert "Counts are label-backed by rfc/RFC-0002" in rendered


def test_cross_repo_issue_posture_markdown_lists_blocked_issue_authority(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        {
            "sgajbi/lotus-idea": {
                "openIssues": [_issue(685, state="OPEN", title="Workbench proof", labels=[])],
                "allIssues": [],
                "rfc0002Issues": [
                    _issue(
                        685,
                        state="OPEN",
                        title="Workbench proof",
                        labels=[
                            "rfc/RFC-0002",
                            "rfc/RFC-0002/slice-11",
                            "status/blocked",
                        ],
                    )
                ],
            }
        },
    )
    blocker_classification = _write_blocker_classification(
        tmp_path,
        [
            _classification(
                685,
                blocker_class="canonical_workbench_runtime_core_readiness",
            )
        ],
    )

    rendered = module.render_markdown(
        module.build_cross_repo_issue_posture(
            repositories=("sgajbi/lotus-idea",),
            fixture_path=fixture,
            blocker_classification_path=blocker_classification,
        )
    )

    assert (
        "- `external_or_protected_evidence` / "
        "`canonical_workbench_runtime_core_readiness`: "
        "`lotus-idea#685` Workbench proof - "
        "https://github.com/sgajbi/lotus-idea/issues/685; "
        "remaining authority: test authority boundary"
    ) in rendered


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


def test_default_blocker_classification_excludes_closed_manage_tax_lot_seed_issue() -> None:
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

    assert matching_rows == []


def test_default_blocker_classification_tracks_issue_814_core_capacity_blocker() -> None:
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
        if (row["repository"] == "sgajbi/lotus-idea" and row["issueNumber"] == 814)
    ]

    assert matching_rows == [
        {
            "repository": "sgajbi/lotus-idea",
            "issueNumber": 814,
            "actionability": "core_dependency",
            "blockerClass": "canonical_idea_capacity_seed_core_readiness",
            "remainingAuthority": (
                "Core-owned DPM portfolio-universe candidate source-batch fingerprint "
                "publication for canonical Workbench/Idea validation, tracked by "
                "sgajbi/lotus-core#882 after earlier Core readiness blockers #836, "
                "#840, #856, and #873 closed"
            ),
        }
    ]


def test_default_blocker_classification_tracks_core_dpm_source_batch_fingerprint() -> None:
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
        if row["repository"] == "sgajbi/lotus-core" and row["issueNumber"] == 882
    ]

    assert matching_rows == [
        {
            "repository": "sgajbi/lotus-core",
            "issueNumber": 882,
            "actionability": "core_dependency",
            "blockerClass": "core_dpm_portfolio_universe_source_batch_fingerprint",
            "remainingAuthority": (
                "Core-owned deterministic non-empty source_batch_fingerprint/content_hash "
                "on DpmPortfolioUniverseCandidate:v1 READY responses so Manage, Gateway, "
                "and Workbench canonical validation can preserve source-ref authority "
                "without fabricating hashes downstream"
            ),
        }
    ]


def test_default_blocker_classification_tracks_core_domain_product_scope_drift() -> None:
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
        if row["repository"] == "sgajbi/lotus-core" and row["issueNumber"] == 885
    ]

    assert matching_rows == [
        {
            "repository": "sgajbi/lotus-core",
            "issueNumber": 885,
            "actionability": "core_dependency",
            "blockerClass": "core_domain_product_request_scope_semantics",
            "remainingAuthority": (
                "Core-owned domain-product request-scope declaration repair for "
                "HoldingsAsOf and IngestionEvidenceBundle so platform and Idea "
                "data-product trust telemetry do not consume contradictory route, "
                "identifier, and bulk-support semantics"
            ),
        }
    ]


def test_default_blocker_classification_tracks_core_technology_governance_pilot() -> None:
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
        if row["repository"] == "sgajbi/lotus-core" and row["issueNumber"] == 917
    ]

    assert matching_rows == [
        {
            "repository": "sgajbi/lotus-core",
            "issueNumber": 917,
            "actionability": "core_dependency",
            "blockerClass": "core_technology_governance_vulnerability_posture_pilot",
            "remainingAuthority": (
                "Core-owned report-only pilot of the platform technology-governance "
                "policy against lotus-core dependency, SBOM, scanner, container-image, "
                "vulnerability, and exception posture, tracked by sgajbi/lotus-core#917 "
                "before sgajbi/lotus-platform#595 can close rollout evidence"
            ),
        }
    ]


def test_default_blocker_classification_excludes_closed_workbench_issue_500() -> None:
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
        if row["repository"] == "sgajbi/lotus-workbench" and row["issueNumber"] == 500
    ]

    assert matching_rows == []


def test_default_blocker_classification_excludes_in_progress_core_issue_856() -> None:
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
        if row["repository"] == "sgajbi/lotus-core" and row["issueNumber"] == 856
    ]

    assert matching_rows == []
