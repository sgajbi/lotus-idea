from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "caller_context_contract_gate.py"
    spec = importlib.util.spec_from_file_location("caller_context_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_module(root: Path, relative_path: Path, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_minimum_caller_headers(root: Path) -> None:
    _write_module(
        root,
        Path("src/app/api/caller_headers.py"),
        "from fastapi import Header\n"
        "from app.api.problem_details import ProblemDetailsHTTPException\n\n"
        "TRUSTED_CALLER_CONTEXT_HEADER = 'X-Lotus-Trusted-Caller-Context'\n\n"
        "def caller_context_from_headers(*, subject, roles, capabilities, "
        "trusted_caller_context=None):\n"
        "    return None\n\n"
        "def caller_context_from_standard_headers(\n"
        "    x_lotus_trusted_caller_context = Header("
        "default=None, alias=TRUSTED_CALLER_CONTEXT_HEADER),\n"
        "):\n"
        "    return caller_context_from_headers(\n"
        "        subject=None,\n"
        "        roles=None,\n"
        "        capabilities=None,\n"
        "        trusted_caller_context=x_lotus_trusted_caller_context,\n"
        "    )\n" + _stable_problem_fragments(),
    )


def _stable_problem_fragments() -> str:
    return (
        "ProblemDetailsHTTPException(\n"
        '    code="invalid_request",\n'
        '    error_category="caller_context_invalid_request",\n'
        ")\n"
        "ProblemDetailsHTTPException(\n"
        '    code="permission_denied",\n'
        '    error_category="caller_context_permission_denied",\n'
        ")\n"
    )


def test_caller_context_contract_gate_passes_current_repository() -> None:
    module = _load_gate()

    assert module.validate_caller_context_contract(ROOT) == []


def test_caller_context_contract_gate_blocks_parser_without_trusted_input(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_module(
        tmp_path,
        Path("src/app/api/caller_headers.py"),
        "def caller_context_from_headers(*, subject, roles, capabilities):\n"
        "    return None\n\n"
        "def caller_context_from_standard_headers():\n"
        "    return caller_context_from_headers(subject=None, roles=None, capabilities=None)\n",
    )

    errors = module.validate_caller_context_contract(tmp_path)

    assert errors == [
        "src/app/api/caller_headers.py:1: caller_context_from_headers must require "
        "trusted_caller_context provenance input",
        "src/app/api/caller_headers.py:4: caller_context_from_standard_headers must bind "
        "`X-Lotus-Trusted-Caller-Context`",
    ]


def test_caller_context_contract_gate_blocks_route_local_header_without_trusted_marker(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_minimum_caller_headers(tmp_path)
    _write_module(
        tmp_path,
        Path("src/app/api/review_queues.py"),
        "from fastapi import Header\n"
        "from app.api.caller_headers import caller_context_from_headers\n\n"
        "def get_queue(\n"
        "    x_caller_subject: str | None = Header("
        "default=None, alias='X-Caller-Subject'),\n"
        "):\n"
        "    return caller_context_from_headers(\n"
        "        subject=x_caller_subject,\n"
        "        roles=None,\n"
        "        capabilities=None,\n"
        "    )\n",
    )

    errors = module.validate_caller_context_contract(tmp_path)

    assert errors == [
        "src/app/api/review_queues.py:4: route-local caller context headers must also bind "
        "`X-Lotus-Trusted-Caller-Context`",
        "src/app/api/review_queues.py:7: route-local caller_context_from_headers calls must "
        "forward trusted_caller_context",
    ]


def test_caller_context_contract_gate_scans_nested_api_route_modules(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_minimum_caller_headers(tmp_path)
    _write_module(
        tmp_path,
        Path("src/app/api/review_queue/routes.py"),
        "from fastapi import Header\n"
        "from app.api.caller_headers import caller_context_from_headers\n\n"
        "def get_queue(\n"
        "    x_caller_capabilities: str | None = Header("
        "default=None, alias='X-Caller-Capabilities'),\n"
        "):\n"
        "    return caller_context_from_headers(\n"
        "        subject=None,\n"
        "        roles=None,\n"
        "        capabilities=x_caller_capabilities,\n"
        "    )\n",
    )

    errors = module.validate_caller_context_contract(tmp_path)

    assert errors == [
        "src/app/api/review_queue/routes.py:4: route-local caller context headers must also bind "
        "`X-Lotus-Trusted-Caller-Context`",
        "src/app/api/review_queue/routes.py:7: route-local caller_context_from_headers calls must "
        "forward trusted_caller_context",
    ]


def test_caller_context_contract_gate_accepts_route_local_trusted_forwarding(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_minimum_caller_headers(tmp_path)
    _write_module(
        tmp_path,
        Path("src/app/api/review_queues.py"),
        "from fastapi import Header\n"
        "from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, "
        "caller_context_from_headers\n\n"
        "def get_queue(\n"
        "    x_caller_subject: str | None = Header("
        "default=None, alias='X-Caller-Subject'),\n"
        "    x_lotus_trusted_caller_context: str | None = Header("
        "default=None, alias=TRUSTED_CALLER_CONTEXT_HEADER),\n"
        "):\n"
        "    return caller_context_from_headers(\n"
        "        subject=x_caller_subject,\n"
        "        roles=None,\n"
        "        capabilities=None,\n"
        "        trusted_caller_context=x_lotus_trusted_caller_context,\n"
        "    )\n",
    )

    assert module.validate_caller_context_contract(tmp_path) == []


def test_caller_context_contract_gate_blocks_role_or_capability_route_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_minimum_caller_headers(tmp_path)
    _write_module(
        tmp_path,
        Path("src/app/api/review_queues.py"),
        "from app.security.caller_context import CapabilityPolicy, require_capability\n\n"
        "_READ_ADVISOR_QUEUE_POLICY = CapabilityPolicy.for_roles(\n"
        "    required_capability='idea.review.queue.read',\n"
        "    allowed_roles=('advisor',),\n"
        ")\n\n"
        "def get_queue(caller):\n"
        "    return require_capability(caller, _READ_ADVISOR_QUEUE_POLICY)\n",
    )

    errors = module.validate_caller_context_contract(tmp_path)

    assert errors == [
        "src/app/api/review_queues.py:9: `_READ_ADVISOR_QUEUE_POLICY` names both "
        "allowed_roles and an idea.* capability, so route authorization must use "
        "`require_role_and_capability`"
    ]


def test_caller_context_contract_gate_accepts_strict_role_and_capability_route_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_minimum_caller_headers(tmp_path)
    _write_module(
        tmp_path,
        Path("src/app/api/review_queues.py"),
        "from app.security.caller_context import CapabilityPolicy, require_role_and_capability\n\n"
        "_READ_ADVISOR_QUEUE_POLICY = CapabilityPolicy.for_roles(\n"
        "    required_capability='idea.review.queue.read',\n"
        "    allowed_roles=('advisor',),\n"
        ")\n\n"
        "def get_queue(caller):\n"
        "    return require_role_and_capability(caller, _READ_ADVISOR_QUEUE_POLICY)\n",
    )

    assert module.validate_caller_context_contract(tmp_path) == []
