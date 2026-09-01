from __future__ import annotations


REQUIRED_REVISION_CONTRACT = (
    "COMMIT_COUNT: ${{ github.event.pull_request.commits }}",
    'revisions="$(git rev-list -n "$COMMIT_COUNT" "$MERGE_COMMIT_SHA" | tac)"',
    "for revision in $revisions; do",
    'dispatch_ref="main-releasability-${revision}"',
    'if [ "$merge_methods" != "false,false,true" ]; then',
)
REVISION_CONTRACT_ERROR = (
    "merged-pr-main-releasability.yml must enumerate every rebase-merged revision "
    "oldest-first and fail closed unless repository merge policy is rebase-only"
)


def extract_named_run_step(workflow: str, step_name: str) -> str:
    start = workflow.find(f"- name: {step_name}")
    if start == -1:
        return ""
    next_step = workflow.find("\n      - ", start + 1)
    return workflow[start : next_step if next_step != -1 else len(workflow)]


def validate_revision_dispatch_scope(dispatch_step: str) -> tuple[str, list[str]]:
    """Return the governed loop body and any revision-enumeration errors."""
    body = _revision_dispatch_loop_body(dispatch_step)
    active_lines = {
        line.strip()
        for line in dispatch_step.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    errors: list[str] = []
    if (
        not dispatch_step
        or not body
        or any(pattern not in active_lines for pattern in REQUIRED_REVISION_CONTRACT)
    ):
        errors.append(REVISION_CONTRACT_ERROR)
    return body, errors


def _revision_dispatch_loop_body(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "for revision in $revisions; do":
            continue
        body: list[str] = []
        depth = 1
        for follow in lines[index + 1 :]:
            stripped = follow.strip()
            if _opens_shell_scope(stripped):
                depth += 1
            if _closes_shell_scope(stripped):
                depth -= 1
                if depth == 0:
                    return "\n".join(body)
            body.append(follow)
        return ""
    return ""


def _opens_shell_scope(line: str) -> bool:
    return (
        line == "("
        or line.startswith("(")
        or line.startswith(("if ", "for ", "while ", "until ", "case "))
        or line.startswith("function ")
        or line.endswith("() {")
        or line.endswith("(){")
        or line.endswith(" {")
    )


def _closes_shell_scope(line: str) -> bool:
    return line in {"fi", "done", "esac", "}"} or line.startswith(")")
