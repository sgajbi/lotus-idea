from __future__ import annotations

from typing import Any

from endpoint_contract_support import validate_named_response_status_contract


HEALTH_READINESS_OPERATION = ("GET", "/health/ready")
HEALTH_READINESS_READY_TEST = "tests/integration/test_health.py::test_health_endpoints"
HEALTH_READINESS_DRAINING_TEST = (
    "tests/integration/test_health.py::test_readiness_reports_draining_state"
)
HEALTH_READINESS_DURABLE_REPOSITORY_TEST = (
    "tests/integration/test_health.py::"
    "test_readiness_degrades_when_production_profile_lacks_durable_repository"
)
HEALTH_READINESS_RECOVERY_TEST = (
    "tests/integration/test_health.py::test_readiness_fails_closed_for_recovery_posture"
)
HEALTH_READINESS_CONTRACT_TEST = (
    "tests/unit/api_examples/test_health_readiness_examples.py::"
    "test_health_readiness_examples_match_ledger_and_generated_openapi"
)


def validate_health_readiness_response_contract(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    from app.api.examples.health_readiness import build_health_readiness_response_examples

    examples = build_health_readiness_response_examples()
    return validate_named_response_status_contract(
        endpoint=endpoint,
        openapi_spec=openapi_spec,
        operation=HEALTH_READINESS_OPERATION,
        expected_by_status=(("200", examples["200"]), ("503", examples["503"])),
        workflow_name="health-readiness",
        required_test_evidence=(
            (HEALTH_READINESS_READY_TEST, "ready HTTP behavior test"),
            (HEALTH_READINESS_DRAINING_TEST, "draining HTTP behavior test"),
            (
                HEALTH_READINESS_DURABLE_REPOSITORY_TEST,
                "durable-repository degraded HTTP behavior test",
            ),
            (HEALTH_READINESS_RECOVERY_TEST, "recovery posture HTTP behavior test"),
            (HEALTH_READINESS_CONTRACT_TEST, "complete health-readiness response contract test"),
        ),
        mode_kind="response",
    )


__all__ = ["validate_health_readiness_response_contract"]
