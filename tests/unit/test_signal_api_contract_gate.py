from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "signal_api_contract_gate.py"
    spec = importlib.util.spec_from_file_location("signal_api_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_signal_module(root: Path, relative_path: Path, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_valid_signal_support(root: Path) -> None:
    _write_signal_module(
        root,
        Path("src/app/api/signal_api_support.py"),
        "SIGNAL_EVALUATION_POLICY = CapabilityPolicy.for_roles(\n"
        "    required_capability='idea.signal.evaluate', allowed_roles=('advisor',)\n"
        ")\n\n"
        "def signal_permission_problem_or_none(caller, policy):\n"
        "    return require_role_and_capability(caller, SIGNAL_EVALUATION_POLICY)\n",
    )


def test_signal_api_contract_gate_passes_current_repository() -> None:
    module = _load_gate()

    assert module.validate_signal_api_contract(ROOT) == []


def test_signal_api_contract_gate_blocks_local_signal_permission_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/low_income_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "evaluate_caller_supplied_signal, signal_source_ref_contract_problem_or_none, emit_signal_evaluation_event, "
        "signal_problem_responses, source_authority_from_contracts\n"
        "from app.security.caller_context import CapabilityPolicy\n\n"
        "LOCAL_POLICY = CapabilityPolicy.for_roles(\n"
        "    required_capability='idea.signal.evaluate', allowed_roles=('advisor',)\n"
        ")\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/low_income_signals.py:5: signal evaluation permission policy "
        "must be centralized in signal_api_support"
    ]


def test_signal_api_contract_gate_blocks_local_signal_outcome_helper(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/bond_maturity_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "evaluate_caller_supplied_signal, signal_source_ref_contract_problem_or_none, emit_signal_evaluation_event, "
        "signal_problem_responses, source_authority_from_contracts\n\n"
        "def _operation_outcome_from_signal_evaluation(result):\n"
        "    return 'accepted'\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/bond_maturity_signals.py:4: signal API modules must use "
        "`operation_outcome_from_signal_evaluation` from signal_api_support"
    ]


def test_signal_api_contract_gate_requires_shared_signal_helpers(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/missing_benchmark_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "def evaluate_missing_benchmark_signal():\n    return None\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`CallerContextHeaders` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`emit_signal_evaluation_event` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`evaluate_caller_supplied_signal` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`signal_permission_problem_or_none` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`signal_problem_responses` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "source-authority support (`source_authority_from_refs` or "
        "`source_authority_from_contracts`)",
    ]


def test_signal_api_contract_gate_requires_shared_source_boundary(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/missing_benchmark_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import (\n"
        "    signal_permission_problem_or_none, evaluate_caller_supplied_signal,\n"
        "    emit_signal_evaluation_event, signal_problem_responses,\n"
        "    source_authority_from_contracts,\n"
        ")\n\n"
        "def evaluate_missing_benchmark_signal_from_source():\n"
        "    return None\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/missing_benchmark_signals.py: source-backed signal APIs must use shared "
        "`evaluate_source_signal` orchestration"
    ]


def test_signal_api_contract_gate_requires_strict_shared_signal_authorization(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    support_path = Path("src/app/api/signal_api_support.py")
    _write_signal_module(
        tmp_path,
        support_path,
        "SIGNAL_EVALUATION_POLICY = CapabilityPolicy.for_roles(\n"
        "    required_capability='idea.signal.evaluate', allowed_roles=('advisor',)\n"
        ")\n\n"
        "def signal_permission_problem_or_none(caller, policy):\n"
        "    return require_capability(caller, policy)\n",
    )
    setattr(module, "SIGNAL_API_SUPPORT_MODULE", support_path)
    setattr(module, "SIGNAL_API_MODULES", ())

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/signal_api_support.py: signal evaluation must use "
        "`require_role_and_capability` for least-privilege route authorization",
        "src/app/api/signal_api_support.py:6: signal evaluation must require both "
        "`advisor` role and `idea.signal.evaluate` capability",
    ]


def test_signal_api_contract_gate_requires_advisor_role_in_shared_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    support_path = Path("src/app/api/signal_api_support.py")
    _write_signal_module(
        tmp_path,
        support_path,
        "SIGNAL_EVALUATION_POLICY = CapabilityPolicy.for_roles(\n"
        "    required_capability='idea.signal.evaluate'\n"
        ")\n\n"
        "def signal_permission_problem_or_none(caller, policy):\n"
        "    return require_role_and_capability(caller, SIGNAL_EVALUATION_POLICY)\n",
    )
    setattr(module, "SIGNAL_API_SUPPORT_MODULE", support_path)
    setattr(module, "SIGNAL_API_MODULES", ())

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/signal_api_support.py:1: signal evaluation policy must require "
        "`idea.signal.evaluate` capability and `advisor` role"
    ]


def test_signal_api_contract_gate_requires_shared_problem_response_metadata(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/concentration_risk_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "evaluate_caller_supplied_signal, signal_source_ref_contract_problem_or_none, emit_signal_evaluation_event, "
        "signal_problem_responses, source_authority_from_contracts\n\n"
        "CONCENTRATION_RISK_EVALUATE_ROUTE = {\n"
        "    'responses': {\n"
        "        200: {'description': 'ok'},\n"
        "        400: {'description': 'Request validation failed.'},\n"
        "        403: {'description': 'Caller lacks permission.'},\n"
        "    },\n"
        "}\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/concentration_risk_signals.py:4: signal evaluation routes must compose "
        "`signal_problem_responses()` for product-safe OpenAPI 400/403 examples"
    ]


def test_signal_api_contract_gate_blocks_route_local_caller_context_headers(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/underperformance_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from fastapi import Header\n"
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "evaluate_caller_supplied_signal, signal_source_ref_contract_problem_or_none, emit_signal_evaluation_event, "
        "signal_problem_responses, source_authority_from_contracts\n\n"
        "def evaluate_underperformance_signal(\n"
        "    x_caller_subject: str | None = Header(default=None, alias='X-Caller-Subject'),\n"
        "):\n"
        "    return None\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/underperformance_signals.py:6: signal API caller context headers "
        "must use `CallerContextHeaders` from caller_headers"
    ]


def test_signal_api_contract_gate_requires_requested_access_scope_permission_check(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    _write_valid_signal_support(tmp_path)
    module_path = Path("src/app/api/concentration_risk_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "evaluate_caller_supplied_signal, signal_source_ref_contract_problem_or_none, emit_signal_evaluation_event, "
        "signal_problem_responses, source_authority_from_contracts\n\n"
        "def evaluate_concentration_risk_signal(request, caller: CallerContextHeaders):\n"
        "    return signal_permission_problem_or_none(\n"
        "        caller=caller,\n"
        "        source_authority='lotus-risk',\n"
        "        emit_event=lambda *args, **kwargs: None,\n"
        "    )\n",
    )
    setattr(module, "SIGNAL_API_MODULES", (module_path,))

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "src/app/api/concentration_risk_signals.py:5: signal permission checks must pass "
        "`requested_access_scope` for entitlement-scope intersection"
    ]


def test_signal_api_contract_gate_requires_explicit_core_live_proof_tenant(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True)
    script_path = scripts_dir / "generate_core_proof.py"
    script_path.write_text(
        "request = CoreRequest(portfolio_id=args.portfolio_id)\n", encoding="utf-8"
    )
    setattr(module, "CORE_LIVE_PROOF_SCRIPTS", (Path("scripts/generate_core_proof.py"),))
    setattr(module, "SIGNAL_API_MODULES", ())
    _write_valid_signal_support(tmp_path)

    errors = module.validate_signal_api_contract(tmp_path)

    assert errors == [
        "scripts/generate_core_proof.py: Core live proof must pass tenant to its request port",
        "scripts/generate_core_proof.py: Core live proof must require explicit `--tenant-id`",
    ]
