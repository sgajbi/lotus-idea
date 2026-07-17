from __future__ import annotations

from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.health_readiness import build_health_readiness_response
from app.domain.recovery_posture import ServiceRecoveryPosture, evaluate_recovery_readiness


HEALTH_READINESS_OPERATION_PATH = "/health/ready"
HEALTH_READINESS_200_EXAMPLE_SUMMARIES = {
    "ready": "The local/test service is ready to receive write traffic",
}
HEALTH_READINESS_503_EXAMPLE_SUMMARIES = {
    "draining": "Traffic is refused while the service drains",
    "restoring": "Traffic is refused while recovery is restoring durable state",
    "durableRepositoryNotConfigured": "A production profile lacks its required durable repository",
    "releaseIdentityBindingMissing": "A release profile lacks the required digest identity binding",
}


def build_health_readiness_response_examples() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "200": {
            "ready": _payload(
                **_local_readiness_values(),
                recovery_posture=ServiceRecoveryPosture.NORMAL,
            ),
        },
        "503": {
            "draining": _payload(
                **_local_readiness_values(),
                recovery_posture=ServiceRecoveryPosture.DRAINING,
            ),
            "restoring": _payload(
                **_local_readiness_values(),
                recovery_posture=ServiceRecoveryPosture.RESTORING,
            ),
            "durableRepositoryNotConfigured": _payload(
                **_production_readiness_values(),
                configuration_blockers=("durable_repository_not_configured",),
                recovery_posture=ServiceRecoveryPosture.NORMAL,
            ),
            "releaseIdentityBindingMissing": _payload(
                **_production_readiness_values(),
                recovery_posture=ServiceRecoveryPosture.NORMAL,
                identity_blockers=("release_image_digest_binding_missing",),
            ),
        },
    }


def apply_health_readiness_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    examples = build_health_readiness_response_examples()
    apply_named_response_examples(
        openapi_schema,
        operation_path=HEALTH_READINESS_OPERATION_PATH,
        operation_method="get",
        response_status_code="200",
        examples=build_named_openapi_examples(
            examples["200"], HEALTH_READINESS_200_EXAMPLE_SUMMARIES
        ),
    )
    apply_named_response_examples(
        openapi_schema,
        operation_path=HEALTH_READINESS_OPERATION_PATH,
        operation_method="get",
        response_status_code="503",
        examples=build_named_openapi_examples(
            examples["503"], HEALTH_READINESS_503_EXAMPLE_SUMMARIES
        ),
    )
    return openapi_schema


def _payload(
    *,
    runtime_profile: str,
    durable_repository_configured: bool,
    durable_storage_backed: bool,
    process_local_repository_allowed: bool,
    durable_write_repository_required: bool,
    configuration_blockers: tuple[str, ...] = (),
    recovery_posture: ServiceRecoveryPosture,
    identity_blockers: tuple[str, ...] = (),
) -> dict[str, Any]:
    return build_health_readiness_response(
        runtime_profile=runtime_profile,
        durable_repository_configured=durable_repository_configured,
        durable_storage_backed=durable_storage_backed,
        process_local_repository_allowed=process_local_repository_allowed,
        durable_write_repository_required=durable_write_repository_required,
        configuration_blockers=configuration_blockers,
        recovery_decision=evaluate_recovery_readiness(recovery_posture),
        identity_blockers=identity_blockers,
    ).model_dump(mode="json", by_alias=True)


def _local_readiness_values() -> dict[str, Any]:
    return {
        "runtime_profile": "local",
        "durable_repository_configured": False,
        "durable_storage_backed": False,
        "process_local_repository_allowed": True,
        "durable_write_repository_required": False,
    }


def _production_readiness_values() -> dict[str, Any]:
    return {
        "runtime_profile": "production",
        "durable_repository_configured": False,
        "durable_storage_backed": False,
        "process_local_repository_allowed": False,
        "durable_write_repository_required": True,
    }


__all__ = [
    "HEALTH_READINESS_200_EXAMPLE_SUMMARIES",
    "HEALTH_READINESS_503_EXAMPLE_SUMMARIES",
    "HEALTH_READINESS_OPERATION_PATH",
    "apply_health_readiness_openapi_examples",
    "build_health_readiness_response_examples",
]
