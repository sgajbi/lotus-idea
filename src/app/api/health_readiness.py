from __future__ import annotations

from collections.abc import Iterable

from fastapi import status
from pydantic import Field

from app.api.base_model import CamelModel
from app.domain.recovery_posture import RecoveryReadinessDecision


class HealthReadinessResponse(CamelModel):
    """Source-safe operational posture for the service readiness probe."""

    status: str
    recovery_posture: str = Field(..., alias="recoveryPosture")
    runtime_profile: str = Field(..., alias="runtimeProfile")
    durable_repository_configured: bool = Field(..., alias="durableRepositoryConfigured")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    process_local_repository_allowed: bool = Field(..., alias="processLocalRepositoryAllowed")
    durable_write_repository_required: bool = Field(..., alias="durableWriteRepositoryRequired")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")


def build_health_readiness_response(
    *,
    runtime_profile: str,
    durable_repository_configured: bool,
    durable_storage_backed: bool,
    process_local_repository_allowed: bool,
    durable_write_repository_required: bool,
    configuration_blockers: Iterable[str],
    recovery_decision: RecoveryReadinessDecision,
    identity_blockers: Iterable[str] = (),
) -> HealthReadinessResponse:
    """Assemble the exact probe payload without exposing runtime configuration values."""

    blockers = list(configuration_blockers)
    normalized_identity_blockers = tuple(identity_blockers)
    readiness_status = "ready" if not blockers else "degraded"

    for blocker in normalized_identity_blockers:
        if blocker not in blockers:
            blockers.append(blocker)
    if normalized_identity_blockers:
        readiness_status = "degraded"

    if not recovery_decision.write_ready:
        readiness_status = recovery_decision.readiness_status
        if recovery_decision.blocker is not None and recovery_decision.blocker not in blockers:
            blockers.append(recovery_decision.blocker)

    return HealthReadinessResponse(
        status=readiness_status,
        recoveryPosture=recovery_decision.posture.value,
        runtimeProfile=runtime_profile,
        durableRepositoryConfigured=durable_repository_configured,
        durableStorageBacked=durable_storage_backed,
        processLocalRepositoryAllowed=process_local_repository_allowed,
        durableWriteRepositoryRequired=durable_write_repository_required,
        configurationBlockers=tuple(blockers),
    )


def health_readiness_status_code(payload: HealthReadinessResponse) -> int:
    return status.HTTP_200_OK if payload.status == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE


__all__ = [
    "HealthReadinessResponse",
    "build_health_readiness_response",
    "health_readiness_status_code",
]
