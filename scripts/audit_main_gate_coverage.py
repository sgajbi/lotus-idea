"""Audit whether every inspected main commit has a releasability verdict.

Rebase merging can add several independently deployable revisions to main.
Each revision therefore needs a verdict-bearing Main Releasability run. A
missing, unreadable, cancelled, or still-running result is unverified and
fails closed when ``--fail-on-gap`` is selected. A failing verdict still
counts as evaluation and is reported separately from coverage gaps.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys

WORKFLOW = "main-releasability.yml"
_VERDICT_CONCLUSIONS = {"success", "failure"}
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _git(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _run_conclusions(sha: str) -> list[str] | None:
    """Return all run conclusions for one revision, or ``None`` if unknowable."""
    completed = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            WORKFLOW,
            "--commit",
            sha,
            "--json",
            "conclusion,status",
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        runs = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(runs, list):
        return None
    return [str(run.get("conclusion") or run.get("status") or "") for run in runs]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=60,
        help="number of origin/main revisions to inspect",
    )
    parser.add_argument(
        "--fail-on-gap",
        action="store_true",
        help="exit non-zero for missing or unverifiable releasability evidence",
    )
    parser.add_argument(
        "--baseline-sha",
        help=("exclusive rollout boundary; older revisions are explicitly classified as pre-gate"),
    )
    arguments = parser.parse_args()
    if arguments.limit < 1:
        parser.error("--limit must be a positive integer")
    if arguments.baseline_sha and not _FULL_SHA.fullmatch(arguments.baseline_sha):
        parser.error("--baseline-sha must be a full lowercase Git SHA")
    return arguments


def main() -> int:
    arguments = _arguments()
    if shutil.which("gh") is None:
        print("gh is not available; main-gate coverage cannot be verified.")
        return 1 if arguments.fail_on_gap else 0

    baseline_sha = getattr(arguments, "baseline_sha", None)
    revision_range = "origin/main"
    if baseline_sha:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_sha, "origin/main"],
            check=False,
        )
        if ancestor.returncode != 0:
            print(f"Coverage baseline {baseline_sha} is not an ancestor of origin/main.")
            return 1 if arguments.fail_on_gap else 0
        revision_range = f"{baseline_sha}..origin/main"

    commits = _git("log", f"-{arguments.limit}", "--format=%H %h %s", revision_range)
    if not commits:
        if baseline_sha:
            print(
                f"No post-rollout commits after {baseline_sha[:12]}; "
                "earlier revisions are explicitly classified as pre-gate."
            )
            return 0
        print("origin/main contains no auditable commits.")
        return 1 if arguments.fail_on_gap else 0

    ungated: list[str] = []
    unknown: list[str] = []
    failing: list[str] = []
    passing = 0

    for entry in commits:
        sha, short, subject = entry.split(" ", 2)
        conclusions = _run_conclusions(sha)
        if conclusions is None:
            unknown.append(short)
            print(f"UNKNOWN  {short}  (run listing could not be fetched)")
            continue
        verdicts = [value for value in conclusions if value in _VERDICT_CONCLUSIONS]
        if verdicts:
            if "success" in verdicts:
                passing += 1
            else:
                failing.append(f"{short}  {subject[:70]}")
            continue
        if conclusions:
            unknown.append(short)
            states = sorted(set(conclusions))
            print(f"UNKNOWN  {short}  (runs exist without a verdict: {states})")
            continue
        ungated.append(f"{short}  {subject[:70]}")
        print(f"UNGATED  {short}  {subject[:70]}")

    print(
        f"\naudited {len(commits)} commit(s) on main; "
        f"{len(ungated)} with no verdict-bearing {WORKFLOW} run; "
        f"{len(unknown)} unverifiable; "
        f"{passing} passing, {len(failing)} with a failing verdict."
    )
    for entry in failing:
        print(f"FAILING  {entry}")
    if ungated:
        print(
            "\nBackfill one with:\n"
            "  gh api repos/OWNER/REPO/git/refs "
            "-f ref=refs/tags/main-releasability-SHA -f sha=SHA\n"
            "  gh workflow run main-releasability.yml --ref main-releasability-SHA "
            "-f expected_sha=SHA -f triggering_pr=backfill\n"
        )
    if arguments.fail_on_gap and (ungated or unknown):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
