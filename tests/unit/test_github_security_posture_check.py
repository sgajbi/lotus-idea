from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_security_posture_check() -> ModuleType:
    script_path = ROOT / "scripts" / "github_security_posture_check.py"
    spec = importlib.util.spec_from_file_location("github_security_posture_check", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _snapshot(module: ModuleType, **overrides: object) -> object:
    payload: dict[str, object] = {
        "repository": "sgajbi/lotus-idea",
        "default_branch": "main",
        "security_and_analysis": {
            "dependabot_security_updates": {"status": "enabled"},
            "secret_scanning": {"status": "enabled"},
            "secret_scanning_push_protection": {"status": "enabled"},
            "secret_scanning_non_provider_patterns": {"status": "disabled"},
            "secret_scanning_validity_checks": {"status": "disabled"},
        },
        "codeql_default_setup": {
            "languages": ["actions", "python"],
            "query_suite": "default",
            "schedule": "weekly",
            "state": "configured",
            "threat_model": "remote",
        },
        "private_vulnerability_reporting": {"enabled": True},
        "open_code_scanning_alerts": 0,
        "open_secret_scanning_alerts": 0,
        "open_dependabot_alerts": 0,
        "default_branch_security_policy_present": True,
        "default_branch_dependabot_config_present": True,
    }
    payload.update(overrides)
    return module.GitHubSecurityPostureSnapshot(**payload)


def test_security_posture_passes_with_current_required_controls() -> None:
    module = _load_security_posture_check()

    errors, warnings = module.validate_snapshot(_snapshot(module))

    assert errors == []
    assert "Secret scanning non-provider patterns is not enabled" in warnings[0]
    assert "Secret scanning validity checks is not enabled" in warnings[1]


def test_security_posture_blocks_weakened_required_control() -> None:
    module = _load_security_posture_check()
    security_and_analysis = {
        "dependabot_security_updates": {"status": "enabled"},
        "secret_scanning": {"status": "enabled"},
        "secret_scanning_push_protection": {"status": "disabled"},
    }

    errors, _warnings = module.validate_snapshot(
        _snapshot(module, security_and_analysis=security_and_analysis)
    )

    assert "Secret scanning push protection must be enabled; GitHub reports `disabled`" in errors


def test_security_posture_blocks_open_security_alerts() -> None:
    module = _load_security_posture_check()

    errors, _warnings = module.validate_snapshot(
        _snapshot(module, open_code_scanning_alerts=1, open_dependabot_alerts=2)
    )

    assert "Open code scanning alerts must be <= 0; GitHub reports 1" in errors
    assert "Open Dependabot alerts must be <= 0; GitHub reports 2" in errors


def test_security_posture_can_require_advanced_secret_scanning() -> None:
    module = _load_security_posture_check()

    errors, warnings = module.validate_snapshot(
        _snapshot(module),
        require_advanced_secret_scanning=True,
    )

    assert warnings == []
    assert "Secret scanning non-provider patterns is not enabled" in errors[0]
    assert "Secret scanning validity checks is not enabled" in errors[1]


def test_security_posture_warns_when_default_branch_security_files_are_not_merged() -> None:
    module = _load_security_posture_check()

    errors, warnings = module.validate_snapshot(
        _snapshot(
            module,
            default_branch_security_policy_present=False,
            default_branch_dependabot_config_present=False,
        )
    )

    assert errors == []
    assert (
        "SECURITY.md is not present on default branch `main`; GitHub Security tab will not "
        "expose that repo-authored control until it is merged"
    ) in warnings
    assert (
        ".github/dependabot.yml is not present on default branch `main`; GitHub Security tab will "
        "not expose that repo-authored control until it is merged"
    ) in warnings


def test_security_posture_can_require_default_branch_security_files() -> None:
    module = _load_security_posture_check()

    errors, warnings = module.validate_snapshot(
        _snapshot(module, default_branch_security_policy_present=False),
        require_default_branch_security_files=True,
    )

    assert warnings == [
        "Secret scanning non-provider patterns is not enabled; GitHub reports `disabled`",
        "Secret scanning validity checks is not enabled; GitHub reports `disabled`",
    ]
    assert (
        "SECURITY.md is not present on default branch `main`; GitHub Security tab will not "
        "expose that repo-authored control until it is merged"
    ) in errors


def test_security_posture_blocks_codeql_drift() -> None:
    module = _load_security_posture_check()
    codeql_default_setup = {
        "languages": ["python"],
        "query_suite": "security-extended",
        "schedule": "on-demand",
        "state": "not-configured",
        "threat_model": "local",
    }

    errors, _warnings = module.validate_snapshot(
        _snapshot(module, codeql_default_setup=codeql_default_setup)
    )

    assert "CodeQL default setup must be configured" in errors
    assert "CodeQL default setup must cover Python and GitHub Actions" in errors
    assert "CodeQL default setup must run weekly" in errors
    assert "CodeQL default setup must use the governed default query suite" in errors
    assert "CodeQL default setup must use the governed remote threat model" in errors
