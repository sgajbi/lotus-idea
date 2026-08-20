from __future__ import annotations


IMMUTABLE_DISPATCH_REF_LOOKUP_CONDITIONS = (
    (
        'if existing_ref_sha="$(gh api '
        '"repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" '
        '--jq .object.sha 2>/dev/null)"; then'
    ),
    (
        'if existing_ref_sha="$(gh api '
        '"repos/$GITHUB_REPOSITORY/git/ref/tags/${dispatch_ref}" '
        '--jq .object.sha 2>/dev/null)"; then'
    ),
)
IMMUTABLE_DISPATCH_REF_MISMATCH_CONDITION = (
    'if [ "$existing_ref_sha" != "$MERGE_COMMIT_SHA" ]; then'
)
IMMUTABLE_DISPATCH_REF_CREATION_CONDITION = 'if [ -z "$existing_ref_sha" ]; then'
IMMUTABLE_DISPATCH_REF_CREATION_COMMAND = 'gh api "repos/$GITHUB_REPOSITORY/git/refs"'
IMMUTABLE_DISPATCH_REF_CREATION_REF_FIELD = '-f ref="refs/tags/$dispatch_ref"'
IMMUTABLE_DISPATCH_REF_CREATION_SHA_FIELD = '-f sha="$MERGE_COMMIT_SHA"'
MAIN_RELEASABILITY_DISPATCH_COMMAND = "gh workflow run main-releasability.yml"


def _step_block(text: str, step_name: str) -> str:
    start = text.find(f"- name: {step_name}")
    if start == -1:
        return ""
    next_step = text.find("\n      - ", start + 1)
    end = next_step if next_step != -1 else len(text)
    return text[start:end]


def _strip_shell_inline_comment(stripped_line: str) -> str:
    in_single_quote = False
    in_double_quote = False
    for index, character in enumerate(stripped_line):
        if character == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif character == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif (
            character == "#"
            and not in_single_quote
            and not in_double_quote
            and (index == 0 or stripped_line[index - 1].isspace())
        ):
            return stripped_line[:index].rstrip()
    return stripped_line


def _continued_shell_command(lines: list[str], start_index: int) -> tuple[str, int]:
    command_parts: list[str] = []
    index = start_index
    while index < len(lines):
        stripped = _strip_shell_inline_comment(lines[index].strip())
        if stripped.endswith("\\"):
            command_parts.append(stripped[:-1].rstrip())
            index += 1
            continue
        command_parts.append(stripped)
        break
    return " ".join(command_parts), index


def validate_merged_pr_main_releasability_dispatch(
    workflow_name: str,
    workflow: str,
) -> list[str]:
    if workflow_name != "merged-pr-main-releasability.yml":
        return []

    errors: list[str] = []
    dispatch_step_text = _step_block(workflow, "Dispatch main releasability gate")
    if not dispatch_step_text:
        errors.append(
            "merged-pr-main-releasability.yml must keep lookup, conditional ref creation, "
            "and workflow dispatch in one named run step"
        )
    dispatch_contract_text = dispatch_step_text or workflow
    if not _has_conditionally_guarded_immutable_ref_lookup(dispatch_contract_text):
        errors.append(
            "merged-pr-main-releasability.yml must guard immutable-ref lookup "
            "with an if/else reset before dispatch"
        )
    elif not _guarded_lookup_success_arms_fail_on_ref_mismatch(dispatch_contract_text):
        errors.append(
            "merged-pr-main-releasability.yml must fail closed with exit 1 when "
            "an existing immutable dispatch ref points to a different SHA"
        )
    if any("||" in block for block in _immutable_ref_lookup_blocks(dispatch_contract_text)):
        errors.append(
            "merged-pr-main-releasability.yml must not mask immutable-ref lookup "
            "failures with shell OR fallbacks"
        )
    if not _conditionally_creates_absent_immutable_ref(dispatch_contract_text):
        errors.append(
            "merged-pr-main-releasability.yml must create the immutable dispatch ref only "
            "inside the empty existing-ref branch with exact ref and SHA fields"
        )
    elif not _dispatches_after_absent_ref_creation(dispatch_contract_text):
        errors.append(
            "merged-pr-main-releasability.yml must run the main releasability dispatch "
            "only after the absent immutable-ref creation branch has completed"
        )
    return errors


def _opens_nested_shell_scope(stripped_line: str) -> bool:
    return (
        stripped_line == "("
        or stripped_line.startswith("(")
        or stripped_line.startswith(("if ", "for ", "while ", "until ", "case "))
        or stripped_line.startswith("function ")
        or stripped_line.endswith("() {")
        or stripped_line.endswith("(){")
        or stripped_line.endswith(" {")
    )


def _closes_nested_shell_scope(stripped_line: str) -> bool:
    return stripped_line in {"fi", "done", "esac", "}"} or stripped_line.startswith(")")


def _is_shell_comment(stripped_line: str) -> bool:
    return stripped_line.startswith("#")


def _contains_immutable_dispatch_ref_lookup(text: str) -> bool:
    return "git/ref/tags/$dispatch_ref" in text or "git/ref/tags/${dispatch_ref}" in text


def _immutable_ref_creation_commands(text: str) -> list[str]:
    lines = text.splitlines()
    commands: list[str] = []
    index = 0
    while index < len(lines):
        stripped_line = lines[index].strip()
        if not _is_shell_comment(stripped_line) and (
            stripped_line == IMMUTABLE_DISPATCH_REF_CREATION_COMMAND
            or stripped_line.startswith(f"{IMMUTABLE_DISPATCH_REF_CREATION_COMMAND} ")
        ):
            command, index = _continued_shell_command(lines, index)
            commands.append(command)
        index += 1
    return commands


def _is_exact_immutable_ref_creation_command(command: str) -> bool:
    return (
        (
            command == IMMUTABLE_DISPATCH_REF_CREATION_COMMAND
            or command.startswith(f"{IMMUTABLE_DISPATCH_REF_CREATION_COMMAND} ")
        )
        and "||" not in command
        and not command.rstrip().endswith("&")
        and not _has_disallowed_immutable_ref_creation_shell_control(command)
        and not _has_disallowed_immutable_ref_creation_override(command)
        and IMMUTABLE_DISPATCH_REF_CREATION_REF_FIELD in command
        and IMMUTABLE_DISPATCH_REF_CREATION_SHA_FIELD in command
    )


def _has_disallowed_immutable_ref_creation_shell_control(command: str) -> bool:
    return ";" in command or "&&" in command


def _has_disallowed_immutable_ref_creation_override(command: str) -> bool:
    tokens = command.split()
    for index, token in enumerate(tokens):
        if token == "--input" or token.startswith("--input="):
            return True
        if token == "--method":
            return index + 1 >= len(tokens) or tokens[index + 1].upper() != "POST"
        if token.startswith("--method="):
            return token.partition("=")[2].upper() != "POST"
        if token == "-X":
            return index + 1 >= len(tokens) or tokens[index + 1].upper() != "POST"
        if token.startswith("-X") and len(token) > 2:
            return token[2:].upper() != "POST"
    return False


def _immutable_ref_lookup_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if _is_shell_comment(stripped_line) or not _contains_immutable_dispatch_ref_lookup(line):
            continue

        block_lines = [line]
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
    outer_depth = 0
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line not in IMMUTABLE_DISPATCH_REF_LOOKUP_CONDITIONS or outer_depth != 0:
            if not stripped_line or _is_shell_comment(stripped_line):
                continue
            if _opens_nested_shell_scope(stripped_line):
                outer_depth += 1
            if _closes_nested_shell_scope(stripped_line):
                outer_depth -= 1
            continue

        block_lines = [line]
        depth = 1
        for follow in lines[index + 1 :]:
            block_lines.append(follow)
            stripped_follow = follow.strip()
            if _opens_nested_shell_scope(stripped_follow):
                depth += 1
            if _closes_nested_shell_scope(stripped_follow):
                depth -= 1
            if depth == 0:
                break
        blocks.append("\n".join(block_lines))
        if _opens_nested_shell_scope(stripped_line):
            outer_depth += 1
        if _closes_nested_shell_scope(stripped_line):
            outer_depth -= 1
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
        if _opens_nested_shell_scope(stripped):
            depth += 1
        if _closes_nested_shell_scope(stripped):
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
        if _opens_nested_shell_scope(stripped):
            depth += 1
        if _closes_nested_shell_scope(stripped):
            depth -= 1
    return executable_commands == ['existing_ref_sha=""']


def _outer_lookup_then_arm_has_mismatch_exit(block: str) -> bool:
    lines = block.splitlines()
    then_arm: list[str] = []
    depth = 1
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "else" and depth == 1:
            break
        then_arm.append(line)
        if _opens_nested_shell_scope(stripped):
            depth += 1
        if _closes_nested_shell_scope(stripped):
            depth -= 1

    condition_depth = 1
    for index, line in enumerate(then_arm):
        stripped_line = line.strip()
        if stripped_line != IMMUTABLE_DISPATCH_REF_MISMATCH_CONDITION or condition_depth != 1:
            if _opens_nested_shell_scope(stripped_line):
                condition_depth += 1
            if _closes_nested_shell_scope(stripped_line):
                condition_depth -= 1
            continue

        direct_executable_commands: list[str] = []
        depth = 1
        for follow in then_arm[index + 1 :]:
            stripped_follow = follow.strip()
            if stripped_follow == "fi" and depth == 1:
                break
            if not stripped_follow or stripped_follow.startswith("#"):
                continue
            if depth == 1:
                direct_executable_commands.append(stripped_follow)
            if _opens_nested_shell_scope(stripped_follow):
                depth += 1
            if _closes_nested_shell_scope(stripped_follow):
                depth -= 1
        return "exit 1" in direct_executable_commands
    return False


def _is_conditionally_guarded_immutable_ref_lookup_block(block: str) -> bool:
    return (
        _contains_immutable_dispatch_ref_lookup(block)
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


def _guarded_lookup_success_arms_fail_on_ref_mismatch(text: str) -> bool:
    guarded_blocks = _immutable_ref_lookup_guard_blocks(text)
    return bool(guarded_blocks) and all(
        _outer_lookup_then_arm_has_mismatch_exit(block) for block in guarded_blocks
    )


def _conditionally_creates_absent_immutable_ref(text: str) -> bool:
    lines = text.splitlines()
    creation_commands = _immutable_ref_creation_commands(text)
    guarded_creation_commands: list[str] = []
    depth = 0
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line == IMMUTABLE_DISPATCH_REF_CREATION_CONDITION and depth == 0:
            creation_depth = 1
            follow_index = index + 1
            while follow_index < len(lines):
                follow = lines[follow_index]
                stripped_follow = follow.strip()
                if stripped_follow == "fi" and creation_depth == 1:
                    break
                if not stripped_follow or _is_shell_comment(stripped_follow):
                    follow_index += 1
                    continue
                if creation_depth == 1 and (
                    stripped_follow == IMMUTABLE_DISPATCH_REF_CREATION_COMMAND
                    or stripped_follow.startswith(f"{IMMUTABLE_DISPATCH_REF_CREATION_COMMAND} ")
                ):
                    command, follow_index = _continued_shell_command(lines, follow_index)
                    guarded_creation_commands.append(command)
                    follow_index += 1
                    continue
                if _opens_nested_shell_scope(stripped_follow):
                    creation_depth += 1
                if _closes_nested_shell_scope(stripped_follow):
                    creation_depth -= 1
                follow_index += 1
        if not stripped_line or _is_shell_comment(stripped_line):
            continue
        if _opens_nested_shell_scope(stripped_line):
            depth += 1
        if _closes_nested_shell_scope(stripped_line):
            depth -= 1
    return (
        bool(guarded_creation_commands)
        and len(guarded_creation_commands) == len(creation_commands)
        and all(
            _is_exact_immutable_ref_creation_command(command)
            for command in guarded_creation_commands
        )
    )


def _main_releasability_dispatch_command_indices(text: str) -> list[int]:
    lines = text.splitlines()
    indices: list[int] = []
    index = 0
    while index < len(lines):
        stripped_line = lines[index].strip()
        if not _is_shell_comment(stripped_line) and (
            stripped_line == MAIN_RELEASABILITY_DISPATCH_COMMAND
            or stripped_line.startswith(f"{MAIN_RELEASABILITY_DISPATCH_COMMAND} ")
        ):
            _, index = _continued_shell_command(lines, index)
            indices.append(index)
        index += 1
    return indices


def _absent_ref_creation_block_end_index(text: str) -> int | None:
    lines = text.splitlines()
    depth = 0
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line == IMMUTABLE_DISPATCH_REF_CREATION_CONDITION and depth == 0:
            saw_creation_command = False
            creation_depth = 1
            follow_index = index + 1
            while follow_index < len(lines):
                follow = lines[follow_index]
                stripped_follow = follow.strip()
                if stripped_follow == "fi" and creation_depth == 1:
                    return follow_index if saw_creation_command else None
                if not stripped_follow or _is_shell_comment(stripped_follow):
                    follow_index += 1
                    continue
                if creation_depth == 1 and (
                    stripped_follow == IMMUTABLE_DISPATCH_REF_CREATION_COMMAND
                    or stripped_follow.startswith(f"{IMMUTABLE_DISPATCH_REF_CREATION_COMMAND} ")
                ):
                    command, follow_index = _continued_shell_command(lines, follow_index)
                    saw_creation_command = _is_exact_immutable_ref_creation_command(command)
                    follow_index += 1
                    continue
                if _opens_nested_shell_scope(stripped_follow):
                    creation_depth += 1
                if _closes_nested_shell_scope(stripped_follow):
                    creation_depth -= 1
                follow_index += 1
        if not stripped_line or _is_shell_comment(stripped_line):
            continue
        if _opens_nested_shell_scope(stripped_line):
            depth += 1
        if _closes_nested_shell_scope(stripped_line):
            depth -= 1
    return None


def _dispatches_after_absent_ref_creation(text: str) -> bool:
    dispatch_indices = _main_releasability_dispatch_command_indices(text)
    creation_block_end_index = _absent_ref_creation_block_end_index(text)
    return (
        len(dispatch_indices) == 1
        and creation_block_end_index is not None
        and dispatch_indices[0] > creation_block_end_index
    )
