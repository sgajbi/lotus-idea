from __future__ import annotations


def validate_merged_pr_main_releasability_dispatch(
    workflow_name: str,
    workflow: str,
) -> list[str]:
    if workflow_name != "merged-pr-main-releasability.yml":
        return []

    if _has_conditionally_guarded_immutable_ref_lookup(workflow):
        return []
    return [
        "merged-pr-main-releasability.yml must guard immutable-ref lookup "
        "with an if/else reset before dispatch"
    ]


def _immutable_ref_lookup_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        if "git/ref/tags/$dispatch_ref" not in line:
            continue

        block_lines = [line]
        stripped_line = line.strip()
        if (
            stripped_line == "then"
            or stripped_line.endswith("; then")
            or stripped_line.endswith(')"')
        ):
            blocks.append("\n".join(block_lines))
            continue
        for follow in lines[index + 1 :]:
            block_lines.append(follow)
            stripped = follow.strip()
            if stripped == "then" or stripped.endswith("; then"):
                break
            if not follow.rstrip().endswith("\\") and stripped.endswith(')"'):
                break
        blocks.append("\n".join(block_lines))
    return blocks


def _immutable_ref_lookup_guard_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if "git/ref/tags/$dispatch_ref" not in line or not stripped_line.startswith(
            'if existing_ref_sha="$(gh api '
        ):
            continue

        block_lines = [line]
        depth = 1
        for follow in lines[index + 1 :]:
            block_lines.append(follow)
            stripped_follow = follow.strip()
            if stripped_follow.startswith("if "):
                depth += 1
            if stripped_follow == "fi":
                depth -= 1
            if depth == 0:
                break
        blocks.append("\n".join(block_lines))
    return blocks


def _outer_lookup_else_arm_has_unconditional_reset(block: str) -> bool:
    lines = block.splitlines()
    else_index: int | None = None
    depth = 1
    for index, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if stripped == "else" and depth == 1:
            else_index = index
            break
        if stripped.startswith("if "):
            depth += 1
        if stripped == "fi":
            depth -= 1

    if else_index is None:
        return False

    executable_commands: list[str] = []
    depth = 1
    for line in lines[else_index + 1 :]:
        stripped = line.strip()
        if stripped == "fi" and depth == 1:
            break
        if not stripped or stripped.startswith("#"):
            continue
        executable_commands.append(stripped)
        if stripped.startswith("if "):
            depth += 1
        if stripped == "fi":
            depth -= 1
    return executable_commands == ['existing_ref_sha=""']


def _is_conditionally_guarded_immutable_ref_lookup_block(block: str) -> bool:
    return (
        "git/ref/tags/$dispatch_ref" in block
        and "\n" in block
        and "else" in block
        and _outer_lookup_else_arm_has_unconditional_reset(block)
        and block.strip().endswith("fi")
    )


def _has_conditionally_guarded_immutable_ref_lookup(text: str) -> bool:
    lookup_blocks = _immutable_ref_lookup_blocks(text)
    guarded_blocks = _immutable_ref_lookup_guard_blocks(text)
    return (
        bool(lookup_blocks)
        and len(lookup_blocks) == len(guarded_blocks)
        and all(
            _is_conditionally_guarded_immutable_ref_lookup_block(block) for block in guarded_blocks
        )
    )
