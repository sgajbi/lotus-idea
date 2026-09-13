"""Audit whether every main revision in a fixed range has an ordered releasability verdict.

Rebase merging lands several independently releasable revisions per pull request, so
each revision needs a verdict-bearing Main Releasability run for its exact tree. The
audit reports coverage separately from outcome:

* coverage says whether ordered terminal evidence exists for the revision -- ``verdict``,
  ``unverifiable`` (complete history holds runs but none reached a verdict), ``ungated``
  (complete history holds no run at all) or ``unknown`` (the history could not be read, or
  it was exhausted before a verdict could be established);
* outcome is the conclusion of the latest terminal run for that exact revision, ordered by
  creation time and then by run id. An earlier success never outranks a later failure, a
  later cancellation never erases an earlier verdict, and when two terminal runs cannot be
  ordered and disagree, the ambiguity resolves to ``failure`` rather than manufacturing a
  pass.

CI history is read as attempts, not runs: every run carries its attempt number into the
ledger, a verdict decided by a rerun (attempt > 1) is flagged because run listings expose
only the latest attempt and a rerun-to-green must stay visible as such, and a timed-out
attempt is a failing verdict, not a coverage gap. Cancelled, skipped, in-progress and unreadable evidence is not a verdict and
fails closed under ``--fail-on-gap``. A failing verdict is evaluated coverage; it is
reported, preserved in the ledger and never counted as a gap. The audited scope is the
fixed ``baseline..end`` range, so historical verdicts and gaps do not age out of view.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

WORKFLOW = "main-releasability.yml"
DEFAULT_END_REF = "origin/main"
DEFAULT_LISTING_LIMIT = 5000
DEFAULT_REVISION_LIMIT = 200
_VERDICT_CONCLUSIONS = {"success", "failure", "timed_out"}
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

COVERAGE_VERDICT = "verdict"
COVERAGE_UNVERIFIABLE = "unverifiable"
COVERAGE_UNGATED = "ungated"
COVERAGE_UNKNOWN = "unknown"
_GAP_COVERAGE = {COVERAGE_UNVERIFIABLE, COVERAGE_UNGATED, COVERAGE_UNKNOWN}

NOTE_HISTORY_UNREADABLE = "run history could not be read"
NOTE_HISTORY_EXHAUSTED = "run history exhausted before a terminal verdict"
NOTE_AMBIGUOUS_ORDER = "equal-order terminal verdicts disagree; resolved to failure"
NOTE_RERUN_VERDICT = (
    "verdict decided by a rerun (attempt > 1); earlier attempts of that run are not visible "
    "in run listings"
)


@dataclass(frozen=True)
class RunEvidence:
    """One workflow run attempt for a revision: when it started, its identity, how it ended."""

    created_at: str
    state: str
    run_id: int = 0
    attempt: int = 1

    @property
    def order_key(self) -> tuple[str, int]:
        return (self.created_at, self.run_id)

    @property
    def is_verdict(self) -> bool:
        return self.state in _VERDICT_CONCLUSIONS

    @property
    def outcome(self) -> str:
        """Collapse the terminal conclusion to the audited outcome; timed_out is a failure."""

        return "success" if self.state == "success" else "failure"

    @property
    def label(self) -> str:
        return f"{self.state}@{self.attempt}"


@dataclass(frozen=True)
class RunHistory:
    """Runs known for one revision and whether that knowledge is complete."""

    runs: tuple[RunEvidence, ...]
    complete: bool


@dataclass(frozen=True)
class RevisionVerdict:
    sha: str
    short: str
    subject: str
    coverage: str
    outcome: str | None
    run_states: tuple[str, ...]
    note: str | None = None


def _git(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _parse_runs(stdout: str) -> list[dict[str, object]] | None:
    try:
        runs = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(runs, list):
        return None
    return [run for run in runs if isinstance(run, dict)]


def _positive_int(value: object, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default


def _evidence(run: dict[str, object]) -> RunEvidence:
    return RunEvidence(
        created_at=str(run.get("createdAt") or ""),
        state=str(run.get("conclusion") or run.get("status") or ""),
        run_id=_positive_int(run.get("databaseId"), 0),
        attempt=_positive_int(run.get("attempt"), 1),
    )


def _gh_run_list(*arguments: str) -> list[dict[str, object]] | None:
    completed = subprocess.run(
        ["gh", "run", "list", "--workflow", WORKFLOW, *arguments],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return _parse_runs(completed.stdout)


def _list_workflow_runs(limit: int) -> tuple[dict[str, list[RunEvidence]], bool] | None:
    """Return runs grouped by exact head SHA plus a truncation flag, or ``None`` if unreadable.

    The listing is newest-first across every revision, so the runs it holds for one
    revision are that revision's newest runs. A revision whose listed runs include a
    terminal verdict therefore has its latest verdict in hand; a revision whose listed runs
    hold no verdict may still have an older one beyond the listing and is re-checked
    individually before any gap is declared.
    """

    runs = _gh_run_list(
        "--limit",
        str(limit),
        "--json",
        "databaseId,attempt,headSha,conclusion,status,createdAt",
    )
    if runs is None:
        return None
    grouped: dict[str, list[RunEvidence]] = {}
    for run in runs:
        head_sha = str(run.get("headSha") or "")
        if head_sha:
            grouped.setdefault(head_sha, []).append(_evidence(run))
    return grouped, len(runs) >= limit


def _runs_for_revision(sha: str, limit: int) -> RunHistory | None:
    """Return the run history of one exact revision, or ``None`` if unknowable."""

    runs = _gh_run_list(
        "--commit",
        sha,
        "--limit",
        str(limit),
        "--json",
        "databaseId,attempt,conclusion,status,createdAt",
    )
    if runs is None:
        return None
    evidence = tuple(_evidence(run) for run in runs)
    return RunHistory(runs=evidence, complete=len(evidence) < limit)


def classify_revision(history: RunHistory | None) -> tuple[str, str | None, str | None]:
    """Return ``(coverage, outcome, note)`` from the ordered terminal evidence of one revision."""

    if history is None:
        return COVERAGE_UNKNOWN, None, NOTE_HISTORY_UNREADABLE
    ordered = sorted(history.runs, key=lambda run: run.order_key)
    terminal = [run for run in ordered if run.is_verdict]
    if terminal:
        latest_key = terminal[-1].order_key
        latest = [run for run in terminal if run.order_key == latest_key]
        outcomes = {run.outcome for run in latest}
        notes: list[str] = []
        if len(outcomes) > 1:
            notes.append(NOTE_AMBIGUOUS_ORDER)
        if any(run.attempt > 1 for run in latest):
            notes.append(NOTE_RERUN_VERDICT)
        outcome = "failure" if len(outcomes) > 1 else outcomes.pop()
        return COVERAGE_VERDICT, outcome, "; ".join(notes) or None
    if not history.complete:
        return COVERAGE_UNKNOWN, None, NOTE_HISTORY_EXHAUSTED
    if ordered:
        return COVERAGE_UNVERIFIABLE, None, None
    return COVERAGE_UNGATED, None, None


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-sha",
        help="exclusive rollout boundary; older revisions are explicitly classified as pre-gate",
    )
    parser.add_argument(
        "--end-ref",
        default=DEFAULT_END_REF,
        help="inclusive end of the audited range (default: origin/main)",
    )
    parser.add_argument(
        "--fail-on-gap",
        action="store_true",
        help="exit non-zero for missing or unverifiable releasability evidence",
    )
    parser.add_argument(
        "--ledger-output",
        help="write the per-revision ledger as JSON to this path",
    )
    parser.add_argument(
        "--listing-limit",
        type=int,
        default=DEFAULT_LISTING_LIMIT,
        help="maximum workflow runs fetched in the bulk listing",
    )
    parser.add_argument(
        "--revision-limit",
        type=int,
        default=DEFAULT_REVISION_LIMIT,
        help="maximum runs fetched when one revision's history is re-checked individually",
    )
    arguments = parser.parse_args()
    if arguments.listing_limit < 1:
        parser.error("--listing-limit must be a positive integer")
    if arguments.revision_limit < 1:
        parser.error("--revision-limit must be a positive integer")
    if arguments.baseline_sha and not _FULL_SHA.fullmatch(arguments.baseline_sha):
        parser.error("--baseline-sha must be a full lowercase Git SHA")
    return arguments


def _revision_range(arguments: argparse.Namespace) -> str | None:
    baseline_sha = getattr(arguments, "baseline_sha", None)
    end_ref = getattr(arguments, "end_ref", DEFAULT_END_REF)
    if not baseline_sha:
        return end_ref
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", baseline_sha, end_ref],
        check=False,
    )
    if ancestor.returncode != 0:
        return None
    return f"{baseline_sha}..{end_ref}"


def _history_for_revision(
    sha: str,
    listing: dict[str, list[RunEvidence]] | None,
    *,
    revision_limit: int,
) -> RunHistory | None:
    listed = listing.get(sha, []) if listing is not None else []
    if any(run.is_verdict for run in listed):
        return RunHistory(runs=tuple(listed), complete=True)
    return _runs_for_revision(sha, revision_limit)


def _audit_revisions(
    commits: list[str],
    listing: dict[str, list[RunEvidence]] | None,
    *,
    revision_limit: int,
) -> list[RevisionVerdict]:
    verdicts: list[RevisionVerdict] = []
    for entry in commits:
        sha, short, subject = entry.split(" ", 2)
        history = _history_for_revision(sha, listing, revision_limit=revision_limit)
        coverage, outcome, note = classify_revision(history)
        ordered = sorted(history.runs, key=lambda run: run.order_key) if history else ()
        verdicts.append(
            RevisionVerdict(
                sha=sha,
                short=short,
                subject=subject,
                coverage=coverage,
                outcome=outcome,
                run_states=tuple(run.label for run in ordered),
                note=note,
            )
        )
    return verdicts


def _write_ledger(
    path: str,
    *,
    revision_range: str,
    verdicts: list[RevisionVerdict],
    summary: dict[str, int],
) -> None:
    ledger = {
        "workflow": WORKFLOW,
        "revision_range": revision_range,
        "audited_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "summary": summary,
        "revisions": [asdict(verdict) for verdict in verdicts],
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    arguments = _arguments()
    fail_on_gap = bool(getattr(arguments, "fail_on_gap", False))
    if shutil.which("gh") is None:
        print("gh is not available; main-gate coverage cannot be verified.")
        return 1 if fail_on_gap else 0

    revision_range = _revision_range(arguments)
    if revision_range is None:
        print(f"Coverage baseline {arguments.baseline_sha} is not an ancestor of the end ref.")
        return 1 if fail_on_gap else 0

    commits = _git("log", "--format=%H %h %s", revision_range)
    if not commits:
        if getattr(arguments, "baseline_sha", None):
            print(
                f"No post-rollout commits in {revision_range}; "
                "earlier revisions are explicitly classified as pre-gate."
            )
            return 0
        print(f"{revision_range} contains no auditable commits.")
        return 1 if fail_on_gap else 0

    listed = _list_workflow_runs(getattr(arguments, "listing_limit", DEFAULT_LISTING_LIMIT))
    listing: dict[str, list[RunEvidence]] | None = None
    if listed is not None:
        listing, truncated = listed
        if truncated:
            print(
                "bulk run listing reached its limit; revisions without a listed verdict are "
                "re-checked individually"
            )
    verdicts = _audit_revisions(
        commits,
        listing,
        revision_limit=getattr(arguments, "revision_limit", DEFAULT_REVISION_LIMIT),
    )

    for verdict in verdicts:
        detail = verdict.outcome or ",".join(sorted(set(verdict.run_states))) or "-"
        line = f"{verdict.coverage.upper():12} {detail:10} {verdict.short}  {verdict.subject[:70]}"
        if verdict.note:
            line += f"  [{verdict.note}]"
        print(line)

    summary = {
        "audited": len(verdicts),
        "verdict": sum(verdict.coverage == COVERAGE_VERDICT for verdict in verdicts),
        "unverifiable": sum(verdict.coverage == COVERAGE_UNVERIFIABLE for verdict in verdicts),
        "ungated": sum(verdict.coverage == COVERAGE_UNGATED for verdict in verdicts),
        "unknown": sum(verdict.coverage == COVERAGE_UNKNOWN for verdict in verdicts),
        "passing": sum(verdict.outcome == "success" for verdict in verdicts),
        "failing": sum(verdict.outcome == "failure" for verdict in verdicts),
    }
    print(
        f"\naudited {summary['audited']} revision(s) in {revision_range}; "
        f"coverage: {summary['verdict']} with a terminal {WORKFLOW} verdict, "
        f"{summary['unverifiable']} unverifiable, {summary['ungated']} ungated, "
        f"{summary['unknown']} unknown; "
        f"outcome: {summary['passing']} passing, {summary['failing']} with a failing verdict."
    )
    gaps = [verdict for verdict in verdicts if verdict.coverage in _GAP_COVERAGE]
    if any(verdict.coverage == COVERAGE_UNGATED for verdict in gaps):
        print(
            "\nBackfill one with:\n"
            "  gh api repos/OWNER/REPO/git/refs "
            "-f ref=refs/tags/main-releasability-SHA -f sha=SHA\n"
            "  gh workflow run main-releasability.yml --ref main-releasability-SHA "
            "-f expected_sha=SHA -f triggering_pr=backfill\n"
        )
    ledger_output = getattr(arguments, "ledger_output", None)
    if ledger_output:
        _write_ledger(
            ledger_output,
            revision_range=revision_range,
            verdicts=verdicts,
            summary=summary,
        )
        print(f"ledger written to {ledger_output}")
    if fail_on_gap and gaps:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
