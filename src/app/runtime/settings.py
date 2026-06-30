from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

DATABASE_URL_ENV = "LOTUS_IDEA_DATABASE_URL"
RUNTIME_PROFILE_ENV = "LOTUS_IDEA_RUNTIME_PROFILE"

DURABLE_REPOSITORY_NOT_CONFIGURED = "durable_repository_not_configured"
INVALID_RUNTIME_PROFILE = "invalid_runtime_profile"


class RuntimeProfile(StrEnum):
    LOCAL = "local"
    TEST = "test"
    DEMO = "demo"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def allows_process_local_repository(self) -> bool:
        return self in {RuntimeProfile.LOCAL, RuntimeProfile.TEST}

    @property
    def requires_durable_write_repository(self) -> bool:
        return not self.allows_process_local_repository


@dataclass(frozen=True)
class LotusIdeaRuntimeSettings:
    runtime_profile: RuntimeProfile
    database_url: str | None

    @property
    def durable_repository_configured(self) -> bool:
        return self.database_url is not None

    @property
    def process_local_repository_allowed(self) -> bool:
        return self.runtime_profile.allows_process_local_repository

    @property
    def durable_write_repository_required(self) -> bool:
        return self.runtime_profile.requires_durable_write_repository


@dataclass(frozen=True)
class RuntimeStoragePosture:
    runtime_profile: RuntimeProfile
    durable_repository_configured: bool
    durable_storage_backed: bool
    process_local_repository_allowed: bool
    durable_write_repository_required: bool
    configuration_blockers: tuple[str, ...]

    @property
    def write_ready(self) -> bool:
        return not self.configuration_blockers


def load_runtime_settings() -> LotusIdeaRuntimeSettings:
    return LotusIdeaRuntimeSettings(
        runtime_profile=_runtime_profile_from_environment(),
        database_url=_optional_environment_value(DATABASE_URL_ENV),
    )


def runtime_storage_posture(
    *,
    settings: LotusIdeaRuntimeSettings | None = None,
    durable_storage_backed: bool = False,
) -> RuntimeStoragePosture:
    active_settings = settings or load_runtime_settings()
    blockers: list[str] = []
    if (
        active_settings.durable_write_repository_required
        and not active_settings.durable_repository_configured
    ):
        blockers.append(DURABLE_REPOSITORY_NOT_CONFIGURED)
    if (
        active_settings.durable_write_repository_required
        and active_settings.durable_repository_configured
        and not durable_storage_backed
    ):
        blockers.append(DURABLE_REPOSITORY_NOT_CONFIGURED)
    return RuntimeStoragePosture(
        runtime_profile=active_settings.runtime_profile,
        durable_repository_configured=active_settings.durable_repository_configured,
        durable_storage_backed=durable_storage_backed,
        process_local_repository_allowed=active_settings.process_local_repository_allowed,
        durable_write_repository_required=active_settings.durable_write_repository_required,
        configuration_blockers=tuple(blockers),
    )


def _runtime_profile_from_environment() -> RuntimeProfile:
    raw_profile = os.getenv(RUNTIME_PROFILE_ENV, RuntimeProfile.LOCAL.value).strip().lower()
    if not raw_profile:
        return RuntimeProfile.LOCAL
    try:
        return RuntimeProfile(raw_profile)
    except ValueError as exc:
        raise RuntimeConfigurationError(
            f"{RUNTIME_PROFILE_ENV} must be one of: "
            f"{', '.join(profile.value for profile in RuntimeProfile)}"
        ) from exc


def _optional_environment_value(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


class RuntimeConfigurationError(RuntimeError):
    """Raised when runtime configuration cannot be interpreted safely."""
