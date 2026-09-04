from __future__ import annotations


DISPATCH_STEP_NAME = "Dispatch main releasability gate"
DISPATCH_ENTRYPOINT = "python scripts/main_releasability_dispatch.py"
EXPECTED_ACTIVE_STEP_LINES = (
    f"- name: {DISPATCH_STEP_NAME}",
    "env:",
    "GH_TOKEN: ${{ github.token }}",
    f"run: {DISPATCH_ENTRYPOINT}",
)


def validate_merged_pr_main_releasability_dispatch(
    workflow_name: str,
    workflow: str,
) -> list[str]:
    """Require one declarative call into the typed mainline dispatcher."""
    if workflow_name != "merged-pr-main-releasability.yml":
        return []

    step = _extract_named_step(workflow, DISPATCH_STEP_NAME)
    active_lines = tuple(
        line.strip()
        for line in step.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if active_lines != EXPECTED_ACTIVE_STEP_LINES:
        return [
            "merged-pr-main-releasability.yml must keep mainline dispatch in one "
            f"declarative `{DISPATCH_ENTRYPOINT}` step with only the GitHub token supplied"
        ]
    if workflow.count(DISPATCH_ENTRYPOINT) != 1:
        return [
            "merged-pr-main-releasability.yml must invoke the typed mainline dispatcher "
            "exactly once"
        ]
    return []


def _extract_named_step(workflow: str, step_name: str) -> str:
    start = workflow.find(f"- name: {step_name}")
    if start == -1:
        return ""
    next_step = workflow.find("\n      - ", start + 1)
    return workflow[start : next_step if next_step != -1 else len(workflow)]
