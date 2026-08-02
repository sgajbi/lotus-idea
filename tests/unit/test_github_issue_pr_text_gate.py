from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from _pytest.capture import CaptureFixture


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_pr_text_gate.py"
    spec = importlib.util.spec_from_file_location(
        "github_issue_pr_text_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_github_issue_pr_text_gate_passes_when_no_pr_text_is_supplied() -> None:
    module = _load_gate()

    assert module.validate_pr_text(title="", body="") == []


def test_github_issue_pr_text_gate_allows_neutral_keep_open_partial_pr_text() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Clarify RFC-0002 issue summary posture",
        body=(
            "Keep #681 open.\n\n"
            "This records a bounded Slice 18 execution-posture update and preserves "
            "the remaining RFC-0002 blockers."
        ),
    )

    assert errors == []


def test_github_issue_pr_text_gate_blocks_auto_close_keyword_with_keep_open_issue() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Fixes RFC-0002 issue summary posture",
        body=("Keep #681 open.\n\nThis is intended as partial Slice 18 evidence only."),
    )

    assert errors == [
        (
            "PR text references keep-open RFC-0002 issue(s) #681 but contains "
            "GitHub auto-close keyword(s) `fixes`. Use neutral verbs such as "
            "`updates`, `records`, `reconciles`, or `addresses`, and keep "
            "completion language out of partial PR titles and bodies."
        )
    ]


def test_github_issue_pr_text_gate_blocks_multiple_auto_close_keywords() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Resolve final closure handoff",
        body=("Keep #683 open.\n\nThis fixed the summary presentation but remains partial."),
    )

    assert errors == [
        (
            "PR text references keep-open RFC-0002 issue(s) #683 but contains "
            "GitHub auto-close keyword(s) `fixed`, `resolve`. Use neutral verbs "
            "such as `updates`, `records`, `reconciles`, or `addresses`, and "
            "keep completion language out of partial PR titles and bodies."
        )
    ]


def test_github_issue_pr_text_gate_allows_negated_close_boundary() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Record Slice 18 evidence",
        body=(
            "Keep #681 open.\n\n"
            "This does not close Slice 18 and uses auto-close as a governance term."
        ),
    )

    assert errors == []


def test_github_issue_pr_text_gate_blocks_negated_close_with_issue_reference() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Record Slice 18 evidence",
        body=("Keep #681 open.\n\nThis records documentation policy only and does not close #681."),
    )

    assert errors == [
        (
            "PR text references keep-open RFC-0002 issue(s) #681 but contains "
            "GitHub auto-close keyword(s) `close`. Use neutral verbs such as "
            "`updates`, `records`, `reconciles`, or `addresses`, and keep "
            "completion language out of partial PR titles and bodies."
        )
    ]


def test_github_issue_pr_text_gate_allows_fix_forward_as_governed_delivery_term() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Record Slice 18 evidence",
        body="Keep #681 open. This records a fix-forward governance note only.",
    )

    assert errors == []


def test_github_issue_pr_text_gate_ignores_closed_issue_completion_text() -> None:
    module = _load_gate()

    errors = module.validate_pr_text(
        title="Closed #340 after QA",
        body="Closed #340 after QA passed.",
    )

    assert errors == []


def test_github_issue_pr_text_gate_reads_exact_pr_body_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    module = _load_gate()
    body_file = tmp_path / "pr-body.md"
    body_file.write_text(
        "Keep #681 open.\n\nThis fixes nothing; it only records partial Slice 18 evidence.",
        encoding="utf-8",
    )

    exit_code = module.main(
        [
            "--title",
            "Record Slice 18 evidence",
            "--body-file",
            str(body_file),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "PR text references keep-open RFC-0002 issue(s) #681" in captured.out
    assert "GitHub auto-close keyword(s) `fixes`" in captured.out


def test_github_issue_pr_text_gate_rejects_multiple_body_sources(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    module = _load_gate()
    body_file = tmp_path / "pr-body.md"
    body_file.write_text("Keep #681 open.", encoding="utf-8")

    exit_code = module.main(
        [
            "--title",
            "Record Slice 18 evidence",
            "--body",
            "Keep #681 open.",
            "--body-file",
            str(body_file),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "body text must be provided by only one source; received inline, file" in captured.out
