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
    assert "sgajbi/lotus-manage#620" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-manage#624" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-report#136" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-archive#55" in issue_379["closureInstruction"]
    assert "production/certification evidence" in issue_379["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_keeps_report_live_proof_in_progress() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_690 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 690
    )

    assert issue_690["githubState"] == "open"
    assert issue_690["executionStatus"] == "open_blocked"
    assert issue_690["allowPullRequestAutoClose"] is False
    assert "Keep #690 open and status/blocked" in issue_690["closureInstruction"]
    assert "PR #724 merged" in issue_690["closureInstruction"]
    assert "This issue is not QA-pending" in issue_690["closureInstruction"]
    assert "Report/Render/Archive production trust" in issue_690["closureInstruction"]


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
    assert "This issue is not QA-pending" in issue_699["closureInstruction"]
    assert "full live journey validation remains blocked" in issue_699["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_blocks_auto_close_wording_for_open_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 690:
            issue["closureInstruction"] = "Closes #690 after partial Report source proof."
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#690: open issue closureInstruction must contain Keep #690 open" in errors
    assert (
        "#690: open issue closureInstruction must not contain GitHub auto-close wording" in errors
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
