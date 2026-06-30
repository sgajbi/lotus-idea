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


def test_signal_api_contract_gate_passes_current_repository() -> None:
    module = _load_gate()

    assert module.validate_signal_api_contract(ROOT) == []


def test_signal_api_contract_gate_blocks_local_signal_permission_policy(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    module_path = Path("src/app/api/low_income_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "emit_signal_evaluation_event, signal_problem_responses, source_authority_from_refs\n"
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
    module_path = Path("src/app/api/bond_maturity_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "emit_signal_evaluation_event, signal_problem_responses, source_authority_from_refs\n\n"
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
        "`signal_permission_problem_or_none` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`signal_problem_responses` support",
        "src/app/api/missing_benchmark_signals.py: caller-supplied signal APIs must use shared "
        "`source_authority_from_refs` support",
    ]


def test_signal_api_contract_gate_requires_shared_problem_response_metadata(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    module_path = Path("src/app/api/concentration_risk_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "emit_signal_evaluation_event, signal_problem_responses, source_authority_from_refs\n\n"
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
    module_path = Path("src/app/api/underperformance_signals.py")
    _write_signal_module(
        tmp_path,
        module_path,
        "from fastapi import Header\n"
        "from app.api.caller_headers import CallerContextHeaders\n"
        "from app.api.signal_api_support import signal_permission_problem_or_none, "
        "emit_signal_evaluation_event, signal_problem_responses, source_authority_from_refs\n\n"
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
