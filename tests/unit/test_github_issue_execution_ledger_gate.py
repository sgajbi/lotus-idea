from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_execution_ledger_gate.py"
    spec = importlib.util.spec_from_file_location(
        "github_issue_execution_ledger_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ledger_payload(module: ModuleType) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(module.LEDGER_PATH.read_text(encoding="utf-8")))


def _write_ledger(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_rfc0002_github_issue_execution_ledger_gate_passes_current_ledger() -> None:
    module = _load_gate()

    assert module.validate_github_issue_execution_ledger() == []


def test_rfc0002_github_issue_execution_ledger_requires_current_issue_690(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    payload["issues"] = [
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] != 690
    ]

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "Missing RFC-0002 execution issue entries: #690" in errors


def test_rfc0002_github_issue_execution_ledger_closes_advise_live_proof_after_main_validation() -> (
    None
):
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_688 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 688
    )

    assert issue_688["githubState"] == "closed"
    assert issue_688["executionStatus"] == "closed_complete"
    assert issue_688["allowPullRequestAutoClose"] is True
    assert "Closed #688" in issue_688["closureInstruction"]
    assert "PR #714 merged to main" in issue_688["closureInstruction"]
    assert "advise_live_contract_proof_missing" in issue_688["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_blocks_issue_379_on_certification_evidence() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_379 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 379
    )

    assert issue_379["githubState"] == "open"
    assert issue_379["executionStatus"] == "open_blocked"
    assert issue_379["allowPullRequestAutoClose"] is False
    assert "Keep #379 open and status/blocked" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-advise#461" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-manage#621" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-report#152" in issue_379["closureInstruction"]
    assert (
        "consumes sgajbi/lotus-manage#620 Manage temporal receipt identity"
        in issue_379["closureInstruction"]
    )
    assert "closed v3 Manage mandate runtime proof contract" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-manage#624" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-report#136" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-archive#55" in issue_379["closureInstruction"]
    assert "production/certification evidence" in issue_379["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_slice18_posture_evidence() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_681 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )

    assert issue_681["githubState"] == "open"
    assert issue_681["executionStatus"] == "open_in_progress"
    assert issue_681["allowPullRequestAutoClose"] is False
    assert "Keep #681 open" in issue_681["closureInstruction"]
    assert (
        "PR #765 merged the Slice 18 cross-repo issue posture command"
        in issue_681["closureInstruction"]
    )
    assert "3ab78c4e9ba23b08eec5396f0641acf21c98f74a" in issue_681["closureInstruction"]
    assert "30411606383" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit 0aea688" in issue_681["closureInstruction"]
    assert (
        "PR #767 rendered pending final-closure and post-completion issue sections"
        in issue_681["closureInstruction"]
    )
    assert "PR #768 added keep-open PR text enforcement" in issue_681["closureInstruction"]
    assert (
        "PR #769 synchronized Manage temporal receipt identity consumption"
        in issue_681["closureInstruction"]
    )
    assert (
        "PR #770 reconciled historical Manage #620 closure truth" in issue_681["closureInstruction"]
    )
    assert "c4a58683a05cb0c78bea5848a287abda682aea8f" in issue_681["closureInstruction"]
    assert "30418344813" in issue_681["closureInstruction"]
    assert "30418340512" in issue_681["closureInstruction"]
    assert "PR #776 synchronized #690 final QA closure truth" in issue_681["closureInstruction"]
    assert "aa492aedd46f30b854c8478edb919605dbdd58fc" in issue_681["closureInstruction"]
    assert "30432065538" in issue_681["closureInstruction"]
    assert "30432058627" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit c08509a" in issue_681["closureInstruction"]
    assert (
        "PR #777 synchronized #681 evidence after #690 QA closure"
        in issue_681["closureInstruction"]
    )
    assert "39d51c5cb63df360f1e97e6e9e862784a9ad9178" in issue_681["closureInstruction"]
    assert "30434057675" in issue_681["closureInstruction"]
    assert "30434051218" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit d0a1fa1" in issue_681["closureInstruction"]
    assert "rfc0002-issue681-pr776-evidence-sync" in issue_681["closureInstruction"]
    assert "PR #779 hardened operations blocker truth" in issue_681["closureInstruction"]
    assert "655d1245e96b7a67dea6c5d9ff0c78d0a32ee9e6" in issue_681["closureInstruction"]
    assert "30437706105" in issue_681["closureInstruction"]
    assert "30437690255" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit b3359fa" in issue_681["closureInstruction"]
    assert "rfc0002-slice15-operations-blocker-truth" in issue_681["closureInstruction"]
    assert "PR #785 synchronized #782 final QA closure truth" in issue_681["closureInstruction"]
    assert "3ed24b318923dd4bf172da315fdc5996a612f0dc" in issue_681["closureInstruction"]
    assert "30447510833" in issue_681["closureInstruction"]
    assert "30447504086" in issue_681["closureInstruction"]
    assert (
        "PR #787 corrected cross-repo RFC-0002 posture coverage" in issue_681["closureInstruction"]
    )
    assert "39a480ddf115649acc3f6793a69596d4e5912bc8" in issue_681["closureInstruction"]
    assert "30451401411" in issue_681["closureInstruction"]
    assert "30451387946" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit d06f46b" in issue_681["closureInstruction"]
    assert "PR #789 classified RFC-0002 blocker actionability" in issue_681["closureInstruction"]
    assert "01ae36ba89f975508bde47b4361190ef5c083597" in issue_681["closureInstruction"]
    assert "30456433618" in issue_681["closureInstruction"]
    assert "30456425304" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit c926899" in issue_681["closureInstruction"]
    assert (
        "PR #790 synchronized PR #789 evidence into source-controlled execution truth"
        in issue_681["closureInstruction"]
    )
    assert "f23c72d7d95d1676b8f673f538a9336e4b704fbc" in issue_681["closureInstruction"]
    assert "30458163573" in issue_681["closureInstruction"]
    assert "30458146092" in issue_681["closureInstruction"]
    assert "lotus-idea.wiki commit bbd9e2f" in issue_681["closureInstruction"]
    assert (
        "PR #791 synchronized PR #790 evidence into source-controlled execution truth"
        in issue_681["closureInstruction"]
    )
    assert "65e11890aaddb70fea4cf9d80e836ce1625a6c44" in issue_681["closureInstruction"]
    assert "30460122600" in issue_681["closureInstruction"]
    assert "30460101418" in issue_681["closureInstruction"]
    assert (
        "lotus-idea.wiki commit 2453c3006722ee40e48762d884581fb6b3893bbe"
        in issue_681["closureInstruction"]
    )
    assert (
        "Workbench PR #505 merged BFF principal-boundary hardening"
        in (issue_681["closureInstruction"])
    )
    assert "1b4afb92f4c810c99921fc26e451b04bca731e28" in issue_681["closureInstruction"]
    assert "30464152669" in issue_681["closureInstruction"]
    assert "c4add59871bc3f0e78dc6602c8857c5e141e6367" in issue_681["closureInstruction"]
    assert "30465110912" in issue_681["closureInstruction"]
    assert "Workbench wiki publication reached commit 3b4f78f" in (issue_681["closureInstruction"])
    assert "0 app-actionable blocked issues" in issue_681["closureInstruction"]
    assert (
        "Current Idea ledger posture after PR #791 is 42 tracked issues, 24 open, and 18 closed"
        in issue_681["closureInstruction"]
    )
    assert (
        "Current governed cross-repo RFC-0002 posture after Workbench PR #505, the platform #636 traceability label update, and platform #638 skill-guidance closure is 37 open and 42 closed issues across 13 repositories, 79 tracked issues total"
        in issue_681["closureInstruction"]
    )
    assert (
        "Platform #636 / PR #637 closed stale queued workflow-run detection"
        in (issue_681["closureInstruction"])
    )
    assert "30472672629" in issue_681["closureInstruction"]
    assert (
        "Platform #638 / PR #639 hardened stale PR-text payload guidance"
        in issue_681["closureInstruction"]
    )
    assert "641aabe9f303a178f3a4e489c52b3d789d8339d3" in issue_681["closureInstruction"]
    assert "30475978275" in issue_681["closureInstruction"]
    assert "strict DiffCount 0" in issue_681["closureInstruction"]
    assert "coordination and documentation truth only" in issue_681["closureInstruction"]
    assert "does not clear RFC-0002 blockers" in issue_681["closureInstruction"]
    assert (
        "replace production IdP/session/token-claims evidence" in (issue_681["closureInstruction"])
    )


def test_rfc0002_github_issue_execution_ledger_tracks_workbench_principal_blocker() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_687 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 687
    )

    assert issue_687["githubState"] == "open"
    assert issue_687["executionStatus"] == "open_blocked"
    assert issue_687["allowPullRequestAutoClose"] is False
    assert "Keep #687 open and status/blocked" in issue_687["closureInstruction"]
    assert (
        "Platform PR #635 defined the authenticated BFF principal session source-contract posture"
        in issue_687["closureInstruction"]
    )
    assert "68c9d3a377a0a801d1a89d1eccf00cefcb3b46b6" in issue_687["closureInstruction"]
    assert "30462517594" in issue_687["closureInstruction"]
    assert "30462522963" in issue_687["closureInstruction"]
    assert "platform wiki commit 3f36de5" in issue_687["closureInstruction"]
    assert (
        "Workbench PR #505 merged BFF principal-boundary hardening"
        in (issue_687["closureInstruction"])
    )
    assert "1b4afb92f4c810c99921fc26e451b04bca731e28" in issue_687["closureInstruction"]
    assert "30464152669" in issue_687["closureInstruction"]
    assert "c4add59871bc3f0e78dc6602c8857c5e141e6367" in issue_687["closureInstruction"]
    assert "30465110912" in issue_687["closureInstruction"]
    assert "Workbench wiki publication reached commit 3b4f78f" in (issue_687["closureInstruction"])
    assert (
        "strips browser-supplied Authorization, Cookie, Proxy-Authorization, and X-Session-Id"
        in issue_687["closureInstruction"]
    )
    assert (
        "production IdP-backed session/token-claim principal derivation"
        in (issue_687["closureInstruction"])
    )
    assert "entitlement-denied proof" in issue_687["closureInstruction"]
    assert "local/dev caller-authority fixture" in issue_687["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_requires_slice18_posture_evidence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 681:
            issue["closureInstruction"] = issue["closureInstruction"].replace(
                "30418344813",
                "",
            )
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#681: closureInstruction missing required evidence `30418344813`" in errors


def test_rfc0002_github_issue_execution_ledger_tracks_report_live_proof_qa_closure() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_690 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 690
    )

    assert issue_690["githubState"] == "closed"
    assert issue_690["executionStatus"] == "closed_complete"
    assert issue_690["allowPullRequestAutoClose"] is True
    assert "Closed #690 after QA passed" in issue_690["closureInstruction"]
    assert "PR #774" in issue_690["closureInstruction"]
    assert "5f53c4ac6ac519c7e6b0019e00f5286109e1628c" in issue_690["closureInstruction"]
    assert "30428715937" in issue_690["closureInstruction"]
    assert "800f682c4f7ae20a2c0634eb112323d7936cca73" in issue_690["closureInstruction"]
    assert "30430120214" in issue_690["closureInstruction"]
    assert "lotus-idea.wiki commit 3ebd0f0" in issue_690["closureInstruction"]
    assert (
        "PR #776 then synchronized the closed-complete execution state"
        in issue_690["closureInstruction"]
    )
    assert "aa492aedd46f30b854c8478edb919605dbdd58fc" in issue_690["closureInstruction"]
    assert "30432065538" in issue_690["closureInstruction"]
    assert "30432058627" in issue_690["closureInstruction"]
    assert "lotus-idea.wiki commit c08509a" in issue_690["closureInstruction"]
    assert "make report-intake-runtime-execution-proof-gate" in issue_690["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_render_archive_merged_main_pending_qa() -> (
    None
):
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_691 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 691
    )

    assert issue_691["githubState"] == "open"
    assert issue_691["executionStatus"] == "open_blocked"
    assert issue_691["allowPullRequestAutoClose"] is False
    assert "Keep #691 open and status/blocked" in issue_691["closureInstruction"]
    assert "PR #725 merged to main" in issue_691["closureInstruction"]
    assert "29972535964" in issue_691["closureInstruction"]
    assert "rendered_output_creation_missing" in issue_691["closureInstruction"]
    assert "archive_record_creation_missing" in issue_691["closureInstruction"]
    assert "lotus-archive #55" in issue_691["closureInstruction"]
    assert "This issue is not QA-pending" in issue_691["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_closes_claim_matrix_after_qa() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_697 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 697
    )

    assert issue_697["githubState"] == "closed"
    assert issue_697["executionStatus"] == "closed_complete"
    assert issue_697["allowPullRequestAutoClose"] is True
    assert "Closed #697" in issue_697["closureInstruction"]
    assert "PR #733 merged" in issue_697["closureInstruction"]
    assert "30000365330" in issue_697["closureInstruction"]
    assert "30000359147" in issue_697["closureInstruction"]
    assert "claim-matrix guardrail tranche" in issue_697["closureInstruction"]
    assert "does not certify live journey" in issue_697["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_closes_archetype_pack_after_qa() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_696 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 696
    )

    assert issue_696["githubState"] == "closed"
    assert issue_696["executionStatus"] == "closed_complete"
    assert issue_696["allowPullRequestAutoClose"] is True
    assert "Closed #696" in issue_696["closureInstruction"]
    assert "PR #738 merged" in issue_696["closureInstruction"]
    assert "30019870406" in issue_696["closureInstruction"]
    assert "30019863754" in issue_696["closureInstruction"]
    assert (
        "source-safe canonical archetype evidence-pack tranche" in issue_696["closureInstruction"]
    )
    assert "does not certify live journey" in issue_696["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_requires_issue_340_qa_closure_evidence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 340:
            issue["closureInstruction"] = issue["closureInstruction"].replace("154 passed", "")
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#340: closureInstruction missing required closed evidence `154 passed`" in errors


def test_rfc0002_github_issue_execution_ledger_tracks_issue_340_closed_qa() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_340 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 340
    )

    assert issue_340["githubState"] == "closed"
    assert issue_340["executionStatus"] == "closed_complete"
    assert issue_340["allowPullRequestAutoClose"] is True
    assert "Closed #340 after QA passed" in issue_340["closureInstruction"]
    assert "3ee62ed5947a0491362f5d080fd1c7deb5ff3567" in issue_340["closureInstruction"]
    assert "30383665975" in issue_340["closureInstruction"]
    assert "30383650543" in issue_340["closureInstruction"]
    assert "154 passed" in issue_340["closureInstruction"]
    assert "51 passed" in issue_340["closureInstruction"]
    assert "sgajbi/lotus-ai#113" in issue_340["closureInstruction"]
    assert "does not claim supported-feature promotion" in issue_340["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_requires_issue_380_blocker_evidence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 380:
            issue["closureInstruction"] = issue["closureInstruction"].replace("open_blocked", "")
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#380: closureInstruction missing required evidence `open_blocked`" in errors


def test_rfc0002_github_issue_execution_ledger_tracks_slice15_operations_blockers() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_343 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 343
    )
    issue_344 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 344
    )
    issue_375 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 375
    )

    assert issue_343["githubState"] == "open"
    assert issue_343["executionStatus"] == "open_blocked"
    assert issue_343["allowPullRequestAutoClose"] is False
    assert "Keep #343 open and status/blocked" in issue_343["closureInstruction"]
    assert "versioned DR contract" in issue_343["closureInstruction"]
    assert "logical backup/restore drill workflow" in issue_343["closureInstruction"]
    assert "managed-provider PITR/failover certification" in issue_343["closureInstruction"]
    assert "continuous WAL/PITR health" in issue_343["closureInstruction"]
    assert "Do not claim production DR" in issue_343["closureInstruction"]

    assert issue_344["githubState"] == "open"
    assert issue_344["executionStatus"] == "open_blocked"
    assert issue_344["allowPullRequestAutoClose"] is False
    assert "Keep #344 open and status/blocked" in issue_344["closureInstruction"]
    assert "versioned lifecycle contract" in issue_344["closureInstruction"]
    assert "signed Archive lifecycle posture consumer" in issue_344["closureInstruction"]
    assert "scheduled lifecycle review workflow" in issue_344["closureInstruction"]
    assert "provider-native AI deletion conformance" in issue_344["closureInstruction"]
    assert "Do not claim legal retention approval" in issue_344["closureInstruction"]

    assert issue_375["githubState"] == "open"
    assert issue_375["executionStatus"] == "open_blocked"
    assert issue_375["allowPullRequestAutoClose"] is False
    assert "Keep #375 open and status/blocked" in issue_375["closureInstruction"]
    assert "exact-image deployment migration contract" in issue_375["closureInstruction"]
    assert "protected workflow" in issue_375["closureInstruction"]
    assert "2026-07-29 live GitHub configuration recheck" in issue_375["closureInstruction"]
    assert "total_count=0" in issue_375["closureInstruction"]
    assert "Deployment Migration Evidence workflow has no runs" in issue_375["closureInstruction"]
    assert "Do not claim production migration certification" in issue_375["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_requires_slice15_operations_blocker_evidence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 375:
            issue["closureInstruction"] = issue["closureInstruction"].replace(
                "total_count=0",
                "",
            )
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#375: closureInstruction missing required evidence `total_count=0`" in errors


def test_rfc0002_github_issue_execution_ledger_tracks_platform_capacity_dependencies() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_345 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 345
    )
    issue_693 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 693
    )

    assert issue_345["githubState"] == "open"
    assert issue_345["executionStatus"] == "open_blocked"
    assert issue_693["githubState"] == "open"
    assert issue_693["executionStatus"] == "open_blocked"
    assert issue_693["allowPullRequestAutoClose"] is False
    assert "Platform PR #629 merged bounded cost-attribution" in issue_345["closureInstruction"]
    assert "823e2641778aaf7db4e1df6218cf84eab0084526" in issue_345["closureInstruction"]
    assert "sgajbi/lotus-platform#495" in issue_345["closureInstruction"]
    assert "capacity-production-like environment" in issue_345["closureInstruction"]
    assert (
        "No supported-feature, production capacity, billing, scaling"
        in issue_345["closureInstruction"]
    )
    assert "Platform PR #629 merged bounded cost-attribution" in issue_693["closureInstruction"]
    assert (
        "platform issue #495 remains the protected FinOps execution"
        in (issue_693["closureInstruction"])
    )
    assert "This issue is not QA-pending" in issue_693["closureInstruction"]
    assert "governed self-hosted lotus-capacity-evidence runner" in issue_693["closureInstruction"]
    assert (
        "Do not close, auto-close, or promote supported features" in issue_693["closureInstruction"]
    )


def test_rfc0002_github_issue_execution_ledger_tracks_workbench_action_blocker() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_686 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 686
    )

    assert issue_686["githubState"] == "open"
    assert issue_686["executionStatus"] == "open_blocked"
    assert issue_686["allowPullRequestAutoClose"] is False
    assert "Keep #686 open and status/blocked" in issue_686["closureInstruction"]
    assert (
        "Workbench PR #501 merged the browser-action proof path"
        in (issue_686["closureInstruction"])
    )
    assert "sgajbi/lotus-core#840" in issue_686["closureInstruction"]
    assert "This issue is not QA-pending" in issue_686["closureInstruction"]
    assert "production identity" in issue_686["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_workbench_read_path_blocker() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_685 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 685
    )

    assert issue_685["githubState"] == "open"
    assert issue_685["executionStatus"] == "open_blocked"
    assert issue_685["allowPullRequestAutoClose"] is False
    assert "Keep #685 open and status/blocked" in issue_685["closureInstruction"]
    assert "make gateway-workbench-runtime-execution-proof" in issue_685["closureInstruction"]
    assert "runtimeExecutionProofValid" in issue_685["closureInstruction"]
    assert "gatewayBffConsumptionObserved" in issue_685["closureInstruction"]
    assert "proofChecks.workbenchEvidenceFresh" in issue_685["closureInstruction"]
    assert "stale runtime-proof timestamp variable" in issue_685["closureInstruction"]
    assert "sgajbi/lotus-core#840" in issue_685["closureInstruction"]
    assert "valuation and aggregation jobs drained to zero" in issue_685["closureInstruction"]
    assert "DPM_CORE_CONTEXT_INCOMPLETE" in issue_685["closureInstruction"]
    assert (
        "POST http://manage.dev.lotus/api/v1/rebalance/simulate"
        in (issue_685["closureInstruction"])
    )
    assert "supported-feature promotion" in issue_685["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_platform_mesh_readiness() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_692 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 692
    )

    assert issue_692["githubState"] == "open"
    assert issue_692["executionStatus"] == "open_blocked"
    assert "Keep #692 open and status/blocked" in issue_692["closureInstruction"]
    assert (
        "Platform PR #630 merged bounded mesh-readiness proof consumption"
        in (issue_692["closureInstruction"])
    )
    assert "30335871870" in issue_692["closureInstruction"]
    assert "30335876432" in issue_692["closureInstruction"]
    assert (
        "clears only the catalog/policy/telemetry-consumable dependency marker"
        in (issue_692["closureInstruction"])
    )
    assert "This issue is not QA-pending" in issue_692["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_live_journey_as_blocked() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_699 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 699
    )

    assert issue_699["githubState"] == "open"
    assert issue_699["executionStatus"] == "open_blocked"
    assert issue_699["allowPullRequestAutoClose"] is False
    assert "Keep #699 open and status/blocked" in issue_699["closureInstruction"]
    assert "PR #740 merged to main" in issue_699["closureInstruction"]
    assert "30319531736" in issue_699["closureInstruction"]
    assert "sgajbi/lotus-ai#122 / PR #123" in issue_699["closureInstruction"]
    assert "937501833b4c2a9d3031a108368ca113204b5db9" in issue_699["closureInstruction"]
    assert "30402022877" in issue_699["closureInstruction"]
    assert (
        "deterministic local-dev idea_explanation.pack@v1 proof-contract execution"
        in issue_699["closureInstruction"]
    )
    assert "approved non-stub live-provider execution" in issue_699["closureInstruction"]
    assert "This issue is not QA-pending" in issue_699["closureInstruction"]
    assert "full live journey validation remains blocked" in issue_699["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_blocks_auto_close_wording_for_open_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 691:
            issue["closureInstruction"] = "Closes #691 after partial Report source proof."
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#691: open issue closureInstruction must contain Keep #691 open" in errors
    assert (
        "#691: open issue closureInstruction must not contain GitHub auto-close wording" in errors
    )


def test_rfc0002_github_issue_execution_ledger_blocks_open_issue_auto_close_flag(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 681:
            issue["allowPullRequestAutoClose"] = True
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#681: open issue cannot allow PR auto-close" in errors


def test_rfc0002_github_issue_execution_ledger_tracks_incident_response_merge() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)

    issue_797 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 797
    )

    assert issue_797["githubState"] == "closed"
    assert issue_797["executionStatus"] == "closed_complete"
    assert issue_797["allowPullRequestAutoClose"] is True
    assert issue_797["rfcSlices"] == ["slice-15", "slice-18"]
    assert (
        "Closed #797 after the incident-response operating model" in issue_797["closureInstruction"]
    )
    assert "PR #798 merged the incident-response operating model" in issue_797["closureInstruction"]
    assert "cfedcc91a5d907e15aa9f50493454eead656b406" in issue_797["closureInstruction"]
    assert "30481301564" in issue_797["closureInstruction"]
    assert "0d075af" in issue_797["closureInstruction"]
    assert "PR #799 synchronized the merge evidence" in issue_797["closureInstruction"]
    assert "13300e21c8b27b4f1418240496f423d54d2ced3e" in issue_797["closureInstruction"]
    assert "30483045202" in issue_797["closureInstruction"]
    assert "90680095852" in issue_797["closureInstruction"]
    assert "issue-797-final-evidence-sync" in issue_797["closureInstruction"]
    assert "does not claim production incident certification" in issue_797["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_records_issue_681_sync_note() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)

    issue_681 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 681
    )

    notes = issue_681.get("evidenceSyncNotes")
    assert isinstance(notes, list)
    assert any(
        isinstance(note, str)
        and "PR #798 merged the incident-response operating model" in note
        and "cfedcc91a5d907e15aa9f50493454eead656b406" in note
        and "30481301564" in note
        and "0d075af" in note
        for note in notes
    )
    assert any(
        isinstance(note, str)
        and "PR #799 synchronized #797 merge evidence" in note
        and "13300e21c8b27b4f1418240496f423d54d2ced3e" in note
        and "30483045202" in note
        and "90680095852" in note
        and "43 tracked issues, 24 open, and 19 closed" in note
        for note in notes
    )


def test_rfc0002_github_issue_execution_ledger_blocks_closed_issue_without_closed_instruction(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 695:
            issue["closureInstruction"] = "Keep #695 open for more dependency evidence."
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#695: closed issue closureInstruction must contain Closed #695" in errors
