from __future__ import annotations

from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse

from app.api.problem_details import problem_details_response, service_unavailable_metadata
from app.api.runtime_dependencies import (
    DURABLE_REPOSITORY_NOT_CONFIGURED as DURABLE_REPOSITORY_NOT_CONFIGURED,
    RuntimeStoragePosture as RuntimeStoragePosture,
    idea_repository_runtime_posture,
)

DURABLE_REPOSITORY_REQUIRED_DETAIL = (
    "This runtime profile requires LOTUS_IDEA_DATABASE_URL before write-capable "
    "idea operations can run."
)


def durable_write_problem(repository: object | None = None) -> JSONResponse | None:
    posture = idea_repository_runtime_posture(repository)
    if posture.write_ready:
        return None
    return durable_repository_not_configured_problem()


def durable_repository_not_configured_problem() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=DURABLE_REPOSITORY_NOT_CONFIGURED,
        title="Durable repository not configured",
        detail=DURABLE_REPOSITORY_REQUIRED_DETAIL,
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
