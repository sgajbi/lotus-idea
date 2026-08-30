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


def _policy_payload(module: ModuleType) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(module.POLICY_PATH.read_text(encoding="utf-8")))


def _write_ledger(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_policy(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _issue_by_number(payload: dict[str, Any], issue_number: int) -> dict[str, Any]:
    return next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == issue_number
    )


def _assert_closure_instruction_contains_fragments(
    issue: dict[str, Any],
    fragments: tuple[str, ...],
) -> None:
    instruction = cast(str, issue["closureInstruction"])
    missing_fragments = [fragment for fragment in fragments if fragment not in instruction]

    assert missing_fragments == []


EvidenceNoteSignature = tuple[str, ...]


def _assert_evidence_notes_contain_signatures(
    notes: object,
    signatures: tuple[EvidenceNoteSignature, ...],
) -> None:
    assert isinstance(notes, list)
    note_texts = [note for note in notes if isinstance(note, str)]
    missing_signatures = [
        signature
        for signature in signatures
        if not any(all(fragment in note for fragment in signature) for note in note_texts)
    ]

    assert missing_signatures == []


ISSUE_681_SLICE18_POSTURE_FRAGMENTS = (
    "Keep #681 open",
    "PR #765 merged the Slice 18 cross-repo issue posture command",
    "3ab78c4e9ba23b08eec5396f0641acf21c98f74a",
    "30411606383",
    "lotus-idea.wiki commit 0aea688",
    "PR #767 rendered pending final-closure and post-completion issue sections",
    "PR #768 added keep-open PR text enforcement",
    "PR #769 synchronized Manage temporal receipt identity consumption",
    "PR #770 reconciled historical Manage #620 closure truth",
    "c4a58683a05cb0c78bea5848a287abda682aea8f",
    "30418344813",
    "30418340512",
    "PR #776 synchronized #690 final QA closure truth",
    "aa492aedd46f30b854c8478edb919605dbdd58fc",
    "30432065538",
    "30432058627",
    "lotus-idea.wiki commit c08509a",
    "PR #777 synchronized #681 evidence after #690 QA closure",
    "39d51c5cb63df360f1e97e6e9e862784a9ad9178",
    "30434057675",
    "30434051218",
    "lotus-idea.wiki commit d0a1fa1",
    "rfc0002-issue681-pr776-evidence-sync",
    "PR #779 hardened operations blocker truth",
    "655d1245e96b7a67dea6c5d9ff0c78d0a32ee9e6",
    "30437706105",
    "30437690255",
    "lotus-idea.wiki commit b3359fa",
    "rfc0002-slice15-operations-blocker-truth",
    "PR #785 synchronized #782 final QA closure truth",
    "3ed24b318923dd4bf172da315fdc5996a612f0dc",
    "30447510833",
    "30447504086",
    "PR #787 corrected cross-repo RFC-0002 posture coverage",
    "39a480ddf115649acc3f6793a69596d4e5912bc8",
    "30451401411",
    "30451387946",
    "lotus-idea.wiki commit d06f46b",
    "PR #789 classified RFC-0002 blocker actionability",
    "01ae36ba89f975508bde47b4361190ef5c083597",
    "30456433618",
    "30456425304",
    "lotus-idea.wiki commit c926899",
    "PR #790 synchronized PR #789 evidence into source-controlled execution truth",
    "f23c72d7d95d1676b8f673f538a9336e4b704fbc",
    "30458163573",
    "30458146092",
    "lotus-idea.wiki commit bbd9e2f",
    "PR #791 synchronized PR #790 evidence into source-controlled execution truth",
    "65e11890aaddb70fea4cf9d80e836ce1625a6c44",
    "30460122600",
    "30460101418",
    "lotus-idea.wiki commit 2453c3006722ee40e48762d884581fb6b3893bbe",
    "Workbench PR #505 merged BFF principal-boundary hardening",
    "1b4afb92f4c810c99921fc26e451b04bca731e28",
    "30464152669",
    "c4add59871bc3f0e78dc6602c8857c5e141e6367",
    "30465110912",
    "Workbench wiki publication reached commit 3b4f78f",
    "0 app-actionable blocked issues",
    "Current Idea ledger posture after PR #801 is 43 tracked issues, 24 open, and 19 closed",
    "PR #801 then synchronized the final #797/#681 evidence on Idea main",
    "95c47d27f45e09369f6b709588fa2de1a1f8700b",
    "30487277416",
    (
        "Current governed cross-repo RFC-0002 posture after PR #801 is 37 open "
        "and 43 closed issues across 13 repositories, 80 tracked issues total"
    ),
    "PR #802 then synchronized current RFC-0002 posture truth on Idea main",
    "7df8fbff1fbab3acb5568a8e95eb7d5d58c8dcdd",
    "30488990343",
    "ec05a36",
    "issue-681-current-posture-sync",
    "Current Idea ledger posture after PR #802 is 43 tracked issues, 24 open, and 19 closed",
    (
        "Current governed cross-repo RFC-0002 posture after PR #802 is 37 open "
        "and 43 closed issues across 13 repositories, 80 tracked issues total"
    ),
    "PR #803 then synchronized PR #802 evidence truth on Idea main",
    "31e5157de796e0accd0f23d3a80102ecd0871c71",
    "30490458612",
    "3743f01",
    "issue-681-pr802-evidence-sync",
    "Current Idea ledger posture after PR #803 is 43 tracked issues, 24 open, and 19 closed",
    (
        "Current governed cross-repo RFC-0002 posture after PR #803 is 37 open "
        "and 43 closed issues across 13 repositories, 80 tracked issues total"
    ),
    "PR #804 then synchronized PR #803 evidence truth on Idea main",
    "615e3ba848af551801c897dd9b0a52f964801da0",
    "30491918891",
    "05026e8",
    "issue-681-pr803-evidence-sync",
    "Current Idea ledger posture after PR #804 is 43 tracked issues, 24 open, and 19 closed",
    (
        "Current governed cross-repo RFC-0002 posture after PR #804 is 37 open "
        "and 43 closed issues across 13 repositories, 80 tracked issues total"
    ),
    "Platform #636 / PR #637 closed stale queued workflow-run detection",
    "30472672629",
    "Platform #638 / PR #639 hardened stale PR-text payload guidance",
    "641aabe9f303a178f3a4e489c52b3d789d8339d3",
    "30475978275",
    "strict DiffCount 0",
    "coordination and documentation truth only",
    "does not clear RFC-0002 blockers",
    "replace production IdP/session/token-claims evidence",
)


ISSUE_681_EVIDENCE_SYNC_NOTE_SIGNATURES: tuple[EvidenceNoteSignature, ...] = (
    (
        "PR #798 merged the incident-response operating model",
        "cfedcc91a5d907e15aa9f50493454eead656b406",
        "30481301564",
        "0d075af",
    ),
    (
        "PR #799 synchronized #797 merge evidence",
        "13300e21c8b27b4f1418240496f423d54d2ced3e",
        "30483045202",
        "90680095852",
        "43 tracked issues, 24 open, and 19 closed",
    ),
    (
        "PR #800 merged the final #797 closed-complete source truth",
        "4ab19e3a85d4b00fc3daeb5d63d2ce1f98a43740",
        "30485290281",
        "issue-797-final-closure-sync",
        "43 tracked issues, 24 open, and 19 closed",
    ),
    (
        "PR #809 synchronized #807 final QA closure truth",
        "c340daa01b41097410bbc8a802d9a8d1f9f24135",
        "30499444726",
        "44 tracked issues, 24 open, and 20 closed",
        "0 app-actionable blocked issues",
    ),
    (
        "PR #810 synchronized PR #809 main evidence",
        "fe7f0efac9fca86a3e19302e8b8436e8941f3d0c",
        "30500588217",
        "lotus-idea.wiki commit f0f9293",
        "sgajbi/lotus-core#836",
        "sgajbi/lotus-core#840",
        "0 app-actionable blocked issues",
    ),
    (
        "PR #817 merged this synchronization",
        "c4c14598be2fa021f7adf9aaf166954ca4f903cf",
        "30551831675",
        "30551812269",
        "lotus-idea.wiki commit 8b36421",
        "returned to open_in_progress",
    ),
    (
        "PR #819 evidence-sync tranche",
        "3b2cc0bb4472a158cb4617b277276244c0e4a22b",
        "30555536256",
        "30555528134",
        "strict wiki parity stayed DiffCount 0",
        "0 app-actionable blocked issues",
        "keeps #681 and #380 open",
    ),
    (
        "2026-08-02 SGT cross-repo blocker sync",
        "sgajbi/lotus-core#882",
        "core_dpm_portfolio_universe_source_batch_fingerprint",
        "106 label-backed RFC-0002 issues",
        "5 Core dependencies",
        "0 app-actionable blocked issues",
    ),
    (
        "PR #838 merged to Idea main",
        "2c2d35667643ad5efae83924475574ab6c16be03",
        "30723235065",
        "lotus-idea.wiki commit ee15dc3",
        "#681 returned to open_in_progress/status/in-progress",
        "108 label-backed issues across 13 repositories",
    ),
    (
        "PR #839 merged to Idea main",
        "71867084c2832d053342db048557e03720a3773a",
        "30724145516",
        "91432087325",
        "lotus-idea.wiki commit c2258e6",
        "#681 returned to open_in_progress/status/in-progress",
        "0 PR-open issues",
    ),
    (
        "PR #842 merged the PR #841 evidence-sync tranche",
        "4e2dd20c3f1b7f17a30eda016e79c62e631b2a2f",
        "30727100273",
        "30727098069",
    ),
    (
        "PR #843 merged the RFC-0002 posture snapshot documentation guard",
        "2ed353b0394a625dd212b437fb93c0d5d4c02a89",
        "30728039165",
        "30728037050",
        "lotus-idea.wiki commit 87dd4e4",
        "#681 returned to open_in_progress/status/in-progress",
    ),
    (
        "PR #844 merged the PR #843 evidence synchronization",
        "c21deeb55dcb1d46395c02c95053ab6149ef6ad6",
        "30728738511",
        "30728733346",
        "lotus-idea.wiki commit b47cbcb",
        "issuecomment-5154685336",
        "#681 returned to open_in_progress/status/in-progress",
    ),
)


def test_rfc0002_github_issue_execution_ledger_gate_passes_current_ledger() -> None:
    module = _load_gate()

    assert module.validate_github_issue_execution_ledger() == []


def test_rfc0002_github_issue_execution_ledger_gate_loads_policy_contract() -> None:
    module = _load_gate()

    policy = module._load_gate_policy()

    assert 871 in policy.expected_issue_numbers
    assert 874 in policy.expected_issue_numbers
    assert "Closed #871" in policy.required_closed_issue_evidence[871]
    assert (
        "rfc0002-github-issue-execution-ledger-gate-policy.v1.json"
        in policy.required_closed_issue_evidence[871]
    )
    assert "Closed #874" in policy.required_closed_issue_evidence[874]
    assert "rfc0002-issue-posture-snapshot.v1.json" in policy.required_closed_issue_evidence[874]
    assert policy.ledger_schema_version == ("lotus-idea:rfc0002-github-issue-execution-ledger:v1")


def test_rfc0002_github_issue_execution_ledger_gate_rejects_bad_policy_schema(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    policy = _policy_payload(module)
    policy["schemaVersion"] = "lotus-idea:bad-policy:v1"

    errors = module.validate_github_issue_execution_ledger(
        policy_path=_write_policy(tmp_path, policy),
    )

    assert errors == [
        "schemaVersion must be lotus-idea:rfc0002-github-issue-execution-ledger-gate-policy:v1",
    ]


def test_rfc0002_github_issue_execution_ledger_gate_enforces_policy_contract_evidence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    policy = _policy_payload(module)
    policy["requiredClosedIssueEvidence"]["871"] = ["missing #871 fragment"]

    errors = module.validate_github_issue_execution_ledger(
        policy_path=_write_policy(tmp_path, policy),
    )

    assert (
        "#871: closureInstruction missing required closed evidence `missing #871 fragment`"
    ) in errors


def test_rfc0002_github_issue_execution_ledger_declares_evidence_only_sync_policy() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)

    policy = payload["policy"]["evidenceOnlySyncPrRule"]

    assert "Evidence-only Slice 18 synchronization PRs" in policy
    assert "must not recursively require another source-sync PR" in policy
    assert "final PR evidence comment" in policy
    assert "exact-main Main Releasability run" in policy
    assert "branch/worktree hygiene" in policy
    assert "If the PR changes implementation truth" in policy
    assert "source-controlled ledger/docs/wiki/context update is required" in policy


def test_rfc0002_github_issue_execution_ledger_requires_evidence_only_sync_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    payload["policy"]["evidenceOnlySyncPrRule"] = (
        "Evidence-only Slice 18 synchronization PRs can use comments."
    )

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert (
        "policy.evidenceOnlySyncPrRule missing required evidence "
        "`Evidence-only Slice 18 synchronization PRs must not recursively "
        "require another source-sync PR for their own post-merge evidence`"
    ) in errors
    assert (
        "policy.evidenceOnlySyncPrRule missing required evidence "
        "`source-controlled ledger/docs/wiki/context update is required`"
    ) in errors


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
        "sgajbi/lotus-report#136 is closed for Report-owned Idea evidence retention-policy conformance"
        in issue_379["closureInstruction"]
    )
    assert "30898036781" in issue_379["closureInstruction"]
    assert (
        "consumes sgajbi/lotus-manage#620 Manage temporal receipt identity"
        in issue_379["closureInstruction"]
    )
    assert "closed v3 Manage mandate runtime proof contract" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-manage#624" in issue_379["closureInstruction"]
    assert "sgajbi/lotus-archive#55" in issue_379["closureInstruction"]
    assert "production/certification evidence" in issue_379["closureInstruction"]
    assert (
        "Archive production legal/privacy lifecycle conformance" in issue_379["closureInstruction"]
    )


def test_rfc0002_github_issue_execution_ledger_tracks_slice18_posture_evidence() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_681 = _issue_by_number(payload, 681)

    assert issue_681["githubState"] == "open"
    assert issue_681["executionStatus"] == "open_in_progress"
    assert issue_681["allowPullRequestAutoClose"] is False
    _assert_closure_instruction_contains_fragments(
        issue_681,
        ISSUE_681_SLICE18_POSTURE_FRAGMENTS,
    )


def test_rfc0002_github_issue_execution_ledger_tracks_issue_854_gate_false_positive() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_854 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 854
    )

    assert issue_854["githubState"] == "closed"
    assert issue_854["executionStatus"] == "closed_complete"
    assert issue_854["allowPullRequestAutoClose"] is True
    assert issue_854["rfcSlices"] == ["slice-18"]
    assert "Closed #854 after PR #855 merged" in issue_854["closureInstruction"]
    assert "PR #855" in issue_854["closureInstruction"]
    assert "1f8a5ffaed7a6d6aaa522d1c4cb06ca6a5602cc5" in issue_854["closureInstruction"]
    assert "31258522447" in issue_854["closureInstruction"]
    assert "31258517415" in issue_854["closureInstruction"]
    assert (
        "fail-closed PR text gate terminology parser correction" in issue_854["closureInstruction"]
    )
    assert "direct issue-reference regression guard" in issue_854["closureInstruction"]
    assert "Keep #681 open" in issue_854["closureInstruction"]
    assert "does not complete Slice 18" in issue_854["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_proof_readiness_hardening_closures() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issues_by_number = {
        issue["issueNumber"]: issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and isinstance(issue.get("issueNumber"), int)
    }

    issue_864 = issues_by_number[864]
    issue_866 = issues_by_number[866]

    assert issue_864["githubState"] == "closed"
    assert issue_864["executionStatus"] == "closed_complete"
    assert issue_864["allowPullRequestAutoClose"] is True
    assert issue_864["rfcSlices"] == ["slice-17", "slice-19"]
    assert "Closed #864" in issue_864["closureInstruction"]
    assert "PR #865" in issue_864["closureInstruction"]
    assert "35091eec121ea0c7186302526b211e288a59abed" in issue_864["closureInstruction"]
    assert "locals()-based implicit composition" in issue_864["closureInstruction"]
    assert "31304700457" in issue_864["closureInstruction"]
    assert "does not complete Slice 17" in issue_864["closureInstruction"]

    assert issue_866["githubState"] == "closed"
    assert issue_866["executionStatus"] == "closed_complete"
    assert issue_866["allowPullRequestAutoClose"] is True
    assert issue_866["rfcSlices"] == ["slice-17", "slice-19"]
    assert "Closed #866" in issue_866["closureInstruction"]
    assert "PR #867" in issue_866["closureInstruction"]
    assert "PR #868" in issue_866["closureInstruction"]
    assert "ImplementationProofReadinessProofInputs" in issue_866["closureInstruction"]
    assert "6d40f7489d70af33e42e28dfb9ffe6e40d880994" in issue_866["closureInstruction"]
    assert "560ddcfff9ba61f2db3008fabc62c31c20cfb425" in issue_866["closureInstruction"]
    assert "does not implement authentication or authorization" in issue_866["closureInstruction"]


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
    assert issue_687["currentBlockerIssueRefs"] == [
        "sgajbi/lotus-platform#563",
        "sgajbi/lotus-workbench#436",
    ]


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


def test_rfc0002_github_issue_execution_ledger_tracks_render_archive_open_blocked_after_report_intake_qa() -> (
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
    assert (
        "The bounded #690 Report intake runtime tranche is complete"
        in issue_691["closureInstruction"]
    )
    assert "PR #774" in issue_691["closureInstruction"]
    assert "5f53c4ac6ac519c7e6b0019e00f5286109e1628c" in issue_691["closureInstruction"]
    assert "PR #776 synchronized final QA truth" in issue_691["closureInstruction"]
    assert "aa492aedd46f30b854c8478edb919605dbdd58fc" in issue_691["closureInstruction"]
    assert "30432065538" in issue_691["closureInstruction"]
    assert "30432058627" in issue_691["closureInstruction"]
    assert "wiki commit c08509a" in issue_691["closureInstruction"]
    assert "rendered_output_creation_missing" in issue_691["closureInstruction"]
    assert "archive_record_creation_missing" in issue_691["closureInstruction"]
    assert "sgajbi/lotus-archive#55" in issue_691["closureInstruction"]
    assert issue_691["currentBlockerIssueRefs"] == ["sgajbi/lotus-archive#55"]
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


def test_rfc0002_github_issue_execution_ledger_tracks_current_issue_380_blockers() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_380 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 380
    )

    assert issue_380["githubState"] == "open"
    assert issue_380["executionStatus"] == "open_blocked"
    assert issue_380["currentBlockerIssueRefs"] == [
        "sgajbi/lotus-platform#563",
        "sgajbi/lotus-workbench#436",
    ]
    assert (
        "Earlier Core runtime blockers #836 and #882 are closed"
        in (issue_380["closureInstruction"])
    )
    assert "foundation_only with zero promoted features" in issue_380["closureInstruction"]


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
        "sgajbi/lotus-platform#495 remains the protected FinOps execution"
        in (issue_693["closureInstruction"])
    )
    assert issue_345["currentBlockerIssueRefs"] == ["sgajbi/lotus-platform#495"]
    assert issue_693["currentBlockerIssueRefs"] == ["sgajbi/lotus-platform#495"]
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
    assert "Core #882 / PR #924 supplied" in issue_686["closureInstruction"]
    assert "source_batch_fingerprint/content_hash" in issue_686["closureInstruction"]
    assert "DpmPortfolioUniverseCandidate:v1" in issue_686["closureInstruction"]
    assert "fresh exact-main Workbench live validation" in issue_686["closureInstruction"]
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
    assert (
        "Core blockers #836, #840, #856, #873, and #882 are closed"
        in (issue_685["closureInstruction"])
    )
    assert "Core #882 / PR #924 supplied" in issue_685["closureInstruction"]
    assert "source_batch_fingerprint/content_hash" in issue_685["closureInstruction"]
    assert "DpmPortfolioUniverseCandidate:v1" in issue_685["closureInstruction"]
    assert "Fresh exact-main Gateway/BFF-backed Workbench" in issue_685["closureInstruction"]
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
    assert issue_699["currentBlockerIssueRefs"] == [
        "sgajbi/lotus-ai#115",
        "sgajbi/lotus-ai#122",
    ]
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
    assert "PR #800 merged the closed-complete source truth" in issue_797["closureInstruction"]
    assert "4ab19e3a85d4b00fc3daeb5d63d2ce1f98a43740" in issue_797["closureInstruction"]
    assert "30485290281" in issue_797["closureInstruction"]
    assert "issue-797-final-closure-sync" in issue_797["closureInstruction"]
    assert "does not claim production incident certification" in issue_797["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_tracks_runtime_image_hardening_issue() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)

    issue_807 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 807
    )

    assert issue_807["githubState"] == "closed"
    assert issue_807["executionStatus"] == "closed_complete"
    assert issue_807["allowPullRequestAutoClose"] is True
    assert issue_807["rfcSlices"] == ["slice-15"]
    assert "Closed #807 after QA passed" in issue_807["closureInstruction"]
    assert "a92144773d1b74bcf19e15396215dd988b5dc0af" in (issue_807["closureInstruction"])
    assert "fe77d768f09444c29efe508e7289b6704b65a69e" in (issue_807["closureInstruction"])
    assert "Main Releasability Gate run 30496796215 passed" in (issue_807["closureInstruction"])
    assert (
        "removes final-image package installer and build-tool metadata"
        in (issue_807["closureInstruction"])
    )
    assert "make docker-build container-image-scan" in issue_807["closureInstruction"]
    assert "make container-runtime-smoke" in issue_807["closureInstruction"]
    assert "HIGH_CRITICAL_FINDINGS=0" in issue_807["closureInstruction"]
    assert "PR #808 synchronized merged-main source truth" in issue_807["closureInstruction"]
    assert "f577efcc14d51208375f3fde87284ac98f8ebb7a" in (issue_807["closureInstruction"])
    assert "30497951358" in issue_807["closureInstruction"]
    assert "30497931322" in issue_807["closureInstruction"]
    assert "30498306031" in issue_807["closureInstruction"]
    assert "PR #809 synchronized final QA closure truth" in issue_807["closureInstruction"]
    assert "c340daa01b41097410bbc8a802d9a8d1f9f24135" in (issue_807["closureInstruction"])
    assert "30499121346" in issue_807["closureInstruction"]
    assert "30499098859" in issue_807["closureInstruction"]
    assert "30499444726" in issue_807["closureInstruction"]
    assert "strict wiki parity DiffCount 0" in issue_807["closureInstruction"]
    assert "git cherry patch-equivalence proof" in issue_807["closureInstruction"]
    assert (
        "does not claim production vulnerability certification" in (issue_807["closureInstruction"])
    )


def test_rfc0002_github_issue_execution_ledger_tracks_capacity_seed_authorization_issue() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)

    issue_814 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 814
    )

    assert issue_814["githubState"] == "open"
    assert issue_814["executionStatus"] == "open_blocked"
    assert issue_814["allowPullRequestAutoClose"] is False
    assert issue_814["rfcSlices"] == ["slice-15", "slice-17"]
    assert "Keep #814 open and status/blocked" in issue_814["closureInstruction"]
    assert "Idea PR #815 merged" in issue_814["closureInstruction"]
    assert "Workbench PR #515 merged" in issue_814["closureInstruction"]
    assert "Workbench PR #516" in issue_814["closureInstruction"]
    assert "1787da79fb4abaf574ebe4ebc3f8b4d5fed7bdac" in issue_814["closureInstruction"]
    assert "30543504302" in issue_814["closureInstruction"]
    assert (
        "Core blockers #836, #840, #856, #873, and #882 are closed"
        in (issue_814["closureInstruction"])
    )
    assert "Fresh 2026-08-29 exact-main evidence" in issue_814["closureInstruction"]
    assert issue_814["currentBlockerIssueRefs"] == [
        "sgajbi/lotus-workbench#904",
        "sgajbi/lotus-advise#557",
    ]
    assert "does not implement production authentication" in issue_814["closureInstruction"]
    assert "supported-feature promotion" in issue_814["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_rejects_malformed_current_blocker_ref(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_814 = _issue_by_number(payload, 814)
    issue_814["currentBlockerIssueRefs"] = ["lotus-workbench-904"]

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#814: every currentBlockerIssueRefs entry must use owner/repo#number" in errors


def test_rfc0002_github_issue_execution_ledger_requires_blocker_ref_in_instruction(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_814 = _issue_by_number(payload, 814)
    issue_814["closureInstruction"] = issue_814["closureInstruction"].replace(
        "sgajbi/lotus-workbench#904",
        "the Workbench memo issue",
    )

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert (
        "#814: current blocker sgajbi/lotus-workbench#904 must appear in closureInstruction"
        in errors
    )


def test_rfc0002_github_issue_execution_ledger_records_issue_681_sync_note() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)

    issue_681 = _issue_by_number(payload, 681)

    _assert_evidence_notes_contain_signatures(
        issue_681.get("evidenceSyncNotes"),
        ISSUE_681_EVIDENCE_SYNC_NOTE_SIGNATURES,
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
