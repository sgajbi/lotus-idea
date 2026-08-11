from __future__ import annotations

from pathlib import Path


REVIEW_LEDGER_RELATIVE_PATH = Path("docs/architecture/CODEBASE-REVIEW-LEDGER.md")
REVIEW_LEDGER_MERGED_MAIN_ENTRIES = {
    "LI-CR-0115": (
        "Issue `#661`",
        "PR `#665` merged",
        "`6b562ac87ca61575c13fefc63b8c688c915da3fc`",
        "Main Releasability `29671128884`",
        "Issue `#661` is closed",
    ),
    "LI-CR-0116": (
        "Issue `#657`",
        "PR `#660` merged",
        "`7aa14e0174b2584110d1d217e31f06c24b1bd153`",
        "Main Releasability `29667502188`",
        "Issue `#657` is closed",
    ),
    "LI-CR-0117": (
        "Issue `#664`",
        "PR `#665` merged",
        "`6b562ac87ca61575c13fefc63b8c688c915da3fc`",
        "Main Releasability `29671128884`",
        "Issue `#664` is closed",
    ),
    "LI-CR-0120": (
        "Issue `#862`",
        "PR `#863` merged",
        "`7ab7bec457f7da1982d91f5238217914d96bb583`",
        "Main Releasability `31303468026`",
        "Issue `#862` is closed with `status/merged-main`",
    ),
}
STALE_REVIEW_LEDGER_STATUS_FRAGMENTS = (
    "Fixed locally; PR/main validation pending",
    "Fixed locally; PR/main proof pending",
    "Locally hardened; PR/main validation pending",
)


def codebase_review_ledger_closure_errors(
    *,
    root: Path,
    require_ledger: bool = True,
) -> list[str]:
    path = root / REVIEW_LEDGER_RELATIVE_PATH
    if not path.exists():
        if not require_ledger:
            return []
        return [f"{REVIEW_LEDGER_RELATIVE_PATH.as_posix()}: required review ledger is missing"]

    lines_by_review_id = {
        line.split("|", maxsplit=2)[1].strip().strip("`"): line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `LI-CR-")
    }

    errors: list[str] = []
    for review_id, required_fragments in REVIEW_LEDGER_MERGED_MAIN_ENTRIES.items():
        row = lines_by_review_id.get(review_id)
        if row is None:
            errors.append(
                f"{REVIEW_LEDGER_RELATIVE_PATH.as_posix()}: "
                f"missing merged-main review entry `{review_id}`"
            )
            continue
        if any(stale_fragment in row for stale_fragment in STALE_REVIEW_LEDGER_STATUS_FRAGMENTS):
            errors.append(
                f"{REVIEW_LEDGER_RELATIVE_PATH.as_posix()}: "
                f"`{review_id}` retains stale local/pending posture after merged-main closure"
            )
        if "| `Closed on main` |" not in row and "| `Hardened on main` |" not in row:
            errors.append(
                f"{REVIEW_LEDGER_RELATIVE_PATH.as_posix()}: "
                f"`{review_id}` must be marked closed or hardened on main"
            )
        for fragment in required_fragments:
            if fragment not in row:
                errors.append(
                    f"{REVIEW_LEDGER_RELATIVE_PATH.as_posix()}: "
                    f"`{review_id}` missing merged-main evidence fragment `{fragment}`"
                )
    return errors
