from __future__ import annotations

from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse

from app.api.problem_details import (
    merged_problem_response_metadata,
    problem_details_response,
    service_unavailable_metadata,
)
from app.api.runtime_dependencies import (
    DURABLE_REPOSITORY_NOT_CONFIGURED as DURABLE_REPOSITORY_NOT_CONFIGURED,
    DURABLE_REPOSITORY_UNAVAILABLE as DURABLE_REPOSITORY_UNAVAILABLE,
    RuntimeStoragePosture as RuntimeStoragePosture,
    idea_repository_runtime_posture,
    load_recovery_runtime_state,
)
from app.domain.recovery_posture import ServiceRecoveryPosture

DURABLE_REPOSITORY_REQUIRED_DETAIL = (
    "This runtime profile requires LOTUS_IDEA_DATABASE_URL before write-capable "
    "idea operations can run."
)
DURABLE_REPOSITORY_UNAVAILABLE_DETAIL = (
    "The configured durable repository is unavailable. Check database connectivity "
    "and configuration before running write-capable idea operations."
)
RECOVERY_PROBLEM_DETAILS = {
    ServiceRecoveryPosture.RESTORING: (
        "service_restoring",
        "Service restore in progress",
        "Lotus Idea is validating restored durable state and cannot accept writes.",
    ),
    ServiceRecoveryPosture.DEGRADED: (
        "service_recovery_degraded",
        "Service recovery posture degraded",
        "Lotus Idea recovery posture is degraded or invalid and cannot accept writes.",
    ),
    ServiceRecoveryPosture.DRAINING: (
        "service_draining",
        "Service draining",
        "Lotus Idea is draining for an operator-authorized cutover and cannot accept writes.",
    ),
}


def durable_write_problem(repository: object | None = None) -> JSONResponse | None:
    recovery_decision = load_recovery_runtime_state().decision
    if not recovery_decision.write_ready:
        return recovery_posture_problem(recovery_decision.posture)
    posture = idea_repository_runtime_posture(repository)
    if posture.write_ready:
        return None
    if DURABLE_REPOSITORY_UNAVAILABLE in posture.configuration_blockers:
        return durable_repository_unavailable_problem()
    return durable_repository_not_configured_problem()


def recovery_posture_problem(posture: ServiceRecoveryPosture) -> JSONResponse:
    code, title, detail = RECOVERY_PROBLEM_DETAILS[posture]
    return problem_details_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=code,
        title=title,
        detail=detail,
    )


def durable_repository_not_configured_problem() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=DURABLE_REPOSITORY_NOT_CONFIGURED,
        title="Durable repository not configured",
        detail=DURABLE_REPOSITORY_REQUIRED_DETAIL,
    )


def durable_repository_unavailable_problem() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=DURABLE_REPOSITORY_UNAVAILABLE,
        title="Durable repository unavailable",
        detail=DURABLE_REPOSITORY_UNAVAILABLE_DETAIL,
    )


def durable_repository_not_configured_metadata() -> dict[int | str, dict[str, Any]]:
    return service_unavailable_metadata(
        code=DURABLE_REPOSITORY_NOT_CONFIGURED,
        title="Durable repository not configured",
        detail=DURABLE_REPOSITORY_REQUIRED_DETAIL,
        description=(
            "The runtime profile requires durable repository configuration before "
            "write-capable idea operations can run."
        ),
    )


def durable_repository_unavailable_metadata() -> dict[int | str, dict[str, Any]]:
    return service_unavailable_metadata(
        code=DURABLE_REPOSITORY_UNAVAILABLE,
        title="Durable repository unavailable",
        detail=DURABLE_REPOSITORY_UNAVAILABLE_DETAIL,
        description="Configured durable repository is unavailable.",
    )


def durable_repository_write_unavailable_metadata() -> dict[int | str, dict[str, Any]]:
    return merged_problem_response_metadata(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        description="Durable repository is not write-ready.",
        responses=(
            durable_repository_not_configured_metadata(),
            durable_repository_unavailable_metadata(),
            *(
                recovery_posture_metadata(posture)
                for posture in (
                    ServiceRecoveryPosture.RESTORING,
                    ServiceRecoveryPosture.DEGRADED,
                    ServiceRecoveryPosture.DRAINING,
                )
            ),
        ),
    )


def recovery_posture_metadata(
    posture: ServiceRecoveryPosture,
) -> dict[int | str, dict[str, Any]]:
    code, title, detail = RECOVERY_PROBLEM_DETAILS[posture]
    return service_unavailable_metadata(
        code=code,
        title=title,
        detail=detail,
        description=f"Service is {posture.value} and durable writes are disabled.",
    )


def durable_write_readiness_payload(posture: RuntimeStoragePosture) -> dict[str, object]:
    status_value = "ready" if posture.write_ready else "degraded"
    return {
        "status": status_value,
        "runtimeProfile": posture.runtime_profile.value,
        "durableRepositoryConfigured": posture.durable_repository_configured,
        "durableStorageBacked": posture.durable_storage_backed,
        "processLocalRepositoryAllowed": posture.process_local_repository_allowed,
        "durableWriteRepositoryRequired": posture.durable_write_repository_required,
        "configurationBlockers": list(posture.configuration_blockers),
    }
