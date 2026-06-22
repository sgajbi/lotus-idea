from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_ci_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "ci_contract_gate.py"
    spec = importlib.util.spec_from_file_location("ci_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_contract_gate_passes_current_repository_contract() -> None:
    module = _load_ci_contract_gate()

    assert module.validate_ci_contract() == []


def test_ci_contract_gate_rejects_floating_action_tags() -> None:
    module = _load_ci_contract_gate()
    workflow = """
jobs:
  workflow-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v7
"""

    errors = module._validate_action_pins("feature-lane.yml", workflow)

    assert errors == [
        "feature-lane.yml:7: actions/checkout must use an immutable 40-character "
        "SHA pin, not a floating tag or branch"
    ]


def test_ci_contract_gate_rejects_unverified_action_sha() -> None:
    module = _load_ci_contract_gate()
    workflow = """
jobs:
  workflow-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/setup-python@0000000000000000000000000000000000000000 # v6.2.0
"""

    errors = module._validate_action_pins("pr-merge-gate.yml", workflow)

    assert errors == [
        "pr-merge-gate.yml:7: actions/setup-python must pin "
        "a309ff8b426b58ec0e2a45f0f869d46889d02405 for verified v6.2.0"
    ]


def test_ci_contract_gate_requires_action_version_provenance_comment() -> None:
    module = _load_ci_contract_gate()
    workflow = """
jobs:
  workflow-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: docker/setup-buildx-action@d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5
"""

    errors = module._validate_action_pins("main-releasability.yml", workflow)

    assert errors == [
        "main-releasability.yml:7: docker/setup-buildx-action SHA pin must carry "
        "`# v4.1.0` provenance"
    ]
