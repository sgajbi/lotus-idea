from __future__ import annotations

from typing import Any, Iterable

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def validate_approved_direct_dependencies(
    contract: dict[str, Any],
    runtime_roots: Iterable[str],
    dev_roots: Iterable[str],
) -> list[str]:
    policy = contract.get("approved_direct_dependency_policy")
    approved_dependencies = contract.get("approved_direct_dependencies")
    if not isinstance(policy, dict):
        return ["approved_direct_dependency_policy is required"]
    if not isinstance(approved_dependencies, list):
        return ["approved_direct_dependencies must be a list"]

    expected_policy = {
        "required_for_every_direct_dependency": True,
        "required_maturity_posture": "mature_widely_deployed_well_documented_scanner_supported",
        "required_documentation_status": "public_documentation_available",
        "required_tooling_support": "broad_training_and_scanner_support",
        "issue_backed_exception_required": True,
    }
    errors = [
        f"approved_direct_dependency_policy.{key} must be {value!r}"
        for key, value in expected_policy.items()
        if policy.get(key) != value
    ]
    actual_scopes = _direct_dependency_scopes(runtime_roots, dev_roots)
    approved_by_name, approval_errors = _approved_dependency_entries(approved_dependencies)
    errors.extend(approval_errors)
    errors.extend(_validate_approval_coverage(actual_scopes, approved_by_name))
    errors.extend(_validate_approval_entries(actual_scopes, approved_by_name, policy))
    return errors


def _approved_dependency_entries(
    approved_dependencies: list[object],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    approved_by_name: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for entry in approved_dependencies:
        if not isinstance(entry, dict):
            errors.append("approved_direct_dependencies entries must be objects")
            continue
        name = canonicalize_name(str(entry.get("name", "")))
        if not name:
            errors.append("approved_direct_dependencies entries must name a dependency")
            continue
        if name in approved_by_name:
            errors.append(f"approved_direct_dependencies contains duplicate `{name}`")
        approved_by_name[name] = entry
    return approved_by_name, errors


def _validate_approval_coverage(
    actual_scopes: dict[str, set[str]],
    approved_by_name: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    missing_approvals = sorted(set(actual_scopes) - set(approved_by_name))
    if missing_approvals:
        errors.append(
            "approved_direct_dependencies missing direct dependencies: "
            + ", ".join(missing_approvals)
        )
    stale_approvals = sorted(set(approved_by_name) - set(actual_scopes))
    if stale_approvals:
        errors.append(
            "approved_direct_dependencies contains non-root dependencies: "
            + ", ".join(stale_approvals)
        )
    return errors


def _validate_approval_entries(
    actual_scopes: dict[str, set[str]],
    approved_by_name: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for name, scopes in sorted(actual_scopes.items()):
        entry = approved_by_name.get(name)
        if entry is None:
            continue
        errors.extend(_validate_approval_entry(name, scopes, entry, policy))
    return errors


def _validate_approval_entry(
    name: str,
    scopes: set[str],
    entry: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    entry_scopes = {str(scope) for scope in entry.get("scopes", [])}
    if entry_scopes != scopes:
        errors.append(
            f"approved_direct_dependencies.{name}.scopes must be " + ", ".join(sorted(scopes))
        )
    if entry.get("maturity_posture") != policy["required_maturity_posture"]:
        errors.append(f"approved_direct_dependencies.{name} has unapproved maturity posture")
    if entry.get("documentation_status") != policy["required_documentation_status"]:
        errors.append(f"approved_direct_dependencies.{name} lacks public documentation status")
    if entry.get("tooling_support") != policy["required_tooling_support"]:
        errors.append(f"approved_direct_dependencies.{name} lacks broad tooling support")
    exception_issue = entry.get("exception_issue")
    if exception_issue is not None and not str(exception_issue).startswith(
        "https://github.com/sgajbi/lotus-idea/issues/"
    ):
        errors.append(
            f"approved_direct_dependencies.{name}.exception_issue must cite a lotus-idea issue"
        )
    return errors


def _direct_dependency_scopes(
    runtime_roots: Iterable[str],
    dev_roots: Iterable[str],
) -> dict[str, set[str]]:
    scopes: dict[str, set[str]] = {}
    for scope, roots in {"runtime": runtime_roots, "ci": dev_roots}.items():
        for raw in roots:
            name = canonicalize_name(Requirement(raw).name)
            scopes.setdefault(name, set()).add(scope)
    return scopes
