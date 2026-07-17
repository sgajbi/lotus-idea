from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

from app.api.examples.health_readiness import (
    HEALTH_READINESS_OPERATION_PATH,
    build_health_readiness_response_examples,
)
from app.api.health_readiness import HealthReadinessResponse
from app.main import app


LEDGER_PATH = Path("docs/operations/endpoint-certification-ledger.json")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def test_health_readiness_examples_execute_production_response_assembly() -> None:
    examples_by_status = build_health_readiness_response_examples()

    assert tuple(examples_by_status) == ("200", "503")
    assert tuple(examples_by_status["200"]) == ("ready",)
    assert tuple(examples_by_status["503"]) == (
        "draining",
        "restoring",
        "durableRepositoryNotConfigured",
        "releaseIdentityBindingMissing",
    )
    assert all(
        HealthReadinessResponse.model_validate(payload)
        for examples in examples_by_status.values()
        for payload in examples.values()
    )
    assert examples_by_status["200"]["ready"]["status"] == "ready"
    assert examples_by_status["503"]["draining"]["configurationBlockers"] == [
        "service_recovery_draining"
    ]
    assert examples_by_status["503"]["restoring"]["configurationBlockers"] == [
        "service_recovery_restoring"
    ]
    assert examples_by_status["503"]["durableRepositoryNotConfigured"]["configurationBlockers"] == [
        "durable_repository_not_configured"
    ]
    assert examples_by_status["503"]["releaseIdentityBindingMissing"]["configurationBlockers"] == [
        "release_image_digest_binding_missing"
    ]


def test_health_readiness_examples_match_ledger_and_generated_openapi() -> None:
    expected = build_health_readiness_response_examples()

    assert _ledger_examples() == [
        *expected["200"].values(),
        *expected["503"].values(),
    ]
    assert _openapi_examples("200") == expected["200"]
    assert _openapi_examples("503") == expected["503"]


def test_health_readiness_contract_blocks_missing_503_mode() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint()
    openapi_spec = deepcopy(app.openapi())
    examples = openapi_spec["paths"][HEALTH_READINESS_OPERATION_PATH]["get"]["responses"]["503"][
        "content"
    ]["application/json"]["examples"]
    examples.pop("restoring")

    errors = module.validate_health_readiness_response_contract(endpoint, openapi_spec)

    assert errors == [
        "('GET', '/health/ready'): OpenAPI 503 examples must exactly match every named "
        "code-owned health-readiness response mode"
    ]


def test_health_readiness_contract_blocks_missing_recovery_behavior_evidence() -> None:
    module = _load_contract_module()
    endpoint = _ledger_endpoint()
    endpoint["test_evidence"].remove(module.HEALTH_READINESS_RECOVERY_TEST)

    errors = module.validate_health_readiness_response_contract(endpoint)

    assert any("recovery posture HTTP behavior test" in error for error in errors)


def _load_contract_module() -> ModuleType:
    script_path = ROOT / "scripts" / "endpoint_health_readiness_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "endpoint_health_readiness_contracts", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger_endpoint() -> dict[str, object]:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return deepcopy(
        next(
            endpoint
            for endpoint in ledger["endpoints"]
            if endpoint["method"] == "GET" and endpoint["path"] == HEALTH_READINESS_OPERATION_PATH
        )
    )


def _ledger_examples() -> list[dict[str, object]]:
    return [json.loads(value) for value in _ledger_endpoint()["response_examples"]]


def _openapi_examples(status_code: str) -> dict[str, dict[str, object]]:
    operation = app.openapi()["paths"][HEALTH_READINESS_OPERATION_PATH]["get"]
    examples = operation["responses"][status_code]["content"]["application/json"]["examples"]
    return {name: metadata["value"] for name, metadata in examples.items()}
