from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

BLUEPRINT_COVERAGE_CONTRACT_PATH = Path(
    "contracts/implementation-proof/rfc0002-blueprint-scope-coverage.v1.json"
)
BLUEPRINT_PATH = Path("docs/LOTUS_IDEA_BLUEPRINT.md")
SCHEMA_VERSION = "lotus-idea.rfc0002.blueprint-scope-coverage.v1"
REPOSITORY = "lotus-idea"
RFC_ID = "RFC-0002"
TRACKING_ISSUE = "https://github.com/sgajbi/lotus-idea/issues/701"
SUPPORTED_FEATURE_POSTURE = "foundation_only_not_promoted"

_SECTION_HEADING_RE = re.compile(r"^##\s+(?P<title>.+)$", re.MULTILINE)
_NUMBERED_ITEM_RE = re.compile(r"^\d+\.\s+(?P<item>.+)$")


def blueprint_scope_coverage_errors(
    *,
    blueprint_markdown: str,
    contract: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    _validate_header(contract, errors)
    owned = _section_numbered_items(blueprint_markdown, "Owned Capabilities")
    non_owned = _section_numbered_items(blueprint_markdown, "Non-Owned Capabilities")
    families = _section_numbered_items(blueprint_markdown, "Target Opportunity Families")
    _validate_entry_group(
        contract,
        key="ownedCapabilities",
        expected=owned,
        item_key="capability",
        errors=errors,
        require_no_supported_claim=True,
    )
    _validate_entry_group(
        contract,
        key="nonOwnedAuthorityBoundaries",
        expected=non_owned,
        item_key="boundary",
        errors=errors,
        require_no_supported_claim=True,
    )
    _validate_entry_group(
        contract,
        key="targetOpportunityFamilies",
        expected=families,
        item_key="family",
        errors=errors,
        require_no_supported_claim=True,
    )
    return errors


def _validate_header(contract: Mapping[str, Any], errors: list[str]) -> None:
    expected = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": REPOSITORY,
        "rfc": RFC_ID,
        "trackingIssue": TRACKING_ISSUE,
        "blueprintSource": str(BLUEPRINT_PATH.as_posix()),
        "supportedFeaturePosture": SUPPORTED_FEATURE_POSTURE,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"{BLUEPRINT_COVERAGE_CONTRACT_PATH}: `{key}` must be `{value}`")


def _validate_entry_group(
    contract: Mapping[str, Any],
    *,
    key: str,
    expected: Sequence[str],
    item_key: str,
    errors: list[str],
    require_no_supported_claim: bool,
) -> None:
    entries = contract.get(key)
    if not isinstance(entries, list):
        errors.append(f"{BLUEPRINT_COVERAGE_CONTRACT_PATH}: `{key}` must be a list")
        return
    indexed = {
        cast(str, entry.get(item_key)): cast(Mapping[str, Any], entry)
        for entry in entries
        if isinstance(entry, Mapping) and isinstance(entry.get(item_key), str)
    }
    for item in expected:
        if item not in indexed:
            errors.append(f"{key}: missing blueprint item `{item}`")
    for item in indexed:
        if item not in expected:
            errors.append(f"{key}: stale item `{item}` is not in the blueprint")
    for item, entry in indexed.items():
        _validate_entry(item, entry, key=key, errors=errors)
        if require_no_supported_claim and entry.get("supportedFeaturePosture") != (
            SUPPORTED_FEATURE_POSTURE
        ):
            errors.append(
                f"{key}: `{item}` must keep supportedFeaturePosture `{SUPPORTED_FEATURE_POSTURE}`"
            )


def _validate_entry(
    item: str,
    entry: Mapping[str, Any],
    *,
    key: str,
    errors: list[str],
) -> None:
    if not _string_list(entry.get("sliceIds")):
        errors.append(f"{key}: `{item}` must name at least one RFC-0002 slice")
    issue_refs = _issue_refs(entry.get("issues"))
    if not issue_refs:
        errors.append(f"{key}: `{item}` must name at least one GitHub issue")
    invalid_issue_refs = _invalid_issue_refs(entry.get("issues"))
    for ref in invalid_issue_refs:
        errors.append(f"{key}: `{item}` has malformed GitHub issue reference `{ref}`")
    if not _string_list(entry.get("evidenceRefs")):
        errors.append(f"{key}: `{item}` must name at least one evidence reference")
    status = entry.get("status")
    if status not in {
        "implemented_foundation",
        "blocked_pending_external_proof",
        "blocked_pending_local_proof",
        "narrowed_non_owned_authority",
        "planned_not_supported",
    }:
        errors.append(f"{key}: `{item}` has unsupported status `{status}`")


def _issue_refs(value: object) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    refs = tuple(cast(Mapping[str, Any], item) for item in value if isinstance(item, Mapping))
    return tuple(ref for ref in refs if _issue_ref_is_valid(ref))


def _invalid_issue_refs(value: object) -> tuple[Mapping[str, Any] | object, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        item
        for item in value
        if not isinstance(item, Mapping) or not _issue_ref_is_valid(cast(Mapping[str, Any], item))
    )


def _issue_ref_is_valid(ref: Mapping[str, Any]) -> bool:
    repository = ref.get("repository")
    number = ref.get("number")
    url = ref.get("url")
    return (
        isinstance(repository, str)
        and repository.startswith("sgajbi/lotus-")
        and isinstance(number, int)
        and number > 0
        and url == f"https://github.com/{repository}/issues/{number}"
    )


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _section_numbered_items(markdown: str, title: str) -> tuple[str, ...]:
    section = _section(markdown, title)
    items: list[str] = []
    current: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                items.append(_normalize_numbered_item(" ".join(current)))
                current = []
            continue
        match = _NUMBERED_ITEM_RE.match(line)
        if match:
            if current:
                items.append(_normalize_numbered_item(" ".join(current)))
            current = [match.group("item")]
        elif current and raw_line.startswith((" ", "\t")) and not line.startswith("|"):
            current.append(line)
    if current:
        items.append(_normalize_numbered_item(" ".join(current)))
    return tuple(items)


def _normalize_numbered_item(value: str) -> str:
    return value.strip().rstrip(".,;")


def _section(markdown: str, title: str) -> str:
    headings = tuple(_SECTION_HEADING_RE.finditer(markdown))
    for index, heading in enumerate(headings):
        if heading.group("title").strip() != title:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        return markdown[heading.end() : end]
    return ""
