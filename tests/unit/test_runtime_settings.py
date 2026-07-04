from __future__ import annotations

import pytest

from app.runtime.settings import (
    DATABASE_URL_ENV,
    DURABLE_REPOSITORY_NOT_CONFIGURED,
    DURABLE_REPOSITORY_UNAVAILABLE,
    RUNTIME_PROFILE_ENV,
    LotusIdeaRuntimeSettings,
    RuntimeConfigurationError,
    RuntimeProfile,
    load_runtime_settings,
    runtime_storage_posture,
)


def test_runtime_settings_default_blank_profile_to_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, " ")
    monkeypatch.setenv(DATABASE_URL_ENV, " ")

    settings = load_runtime_settings()

    assert settings.runtime_profile is RuntimeProfile.LOCAL
    assert settings.database_url is None


def test_runtime_settings_reject_invalid_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_PROFILE_ENV, "not-a-profile")

    with pytest.raises(RuntimeConfigurationError, match=f"{RUNTIME_PROFILE_ENV} must be one of"):
        load_runtime_settings()


def test_runtime_storage_posture_requires_backed_repository_when_database_configured() -> None:
    settings = LotusIdeaRuntimeSettings(
        runtime_profile=RuntimeProfile.PRODUCTION,
        database_url="postgresql://lotus-idea.example/idea",
    )

    posture = runtime_storage_posture(settings=settings, durable_storage_backed=False)

    assert posture.configuration_blockers == (DURABLE_REPOSITORY_NOT_CONFIGURED,)
    assert posture.write_ready is False


def test_runtime_storage_posture_treats_repository_initialization_failure_as_blocker() -> None:
    settings = LotusIdeaRuntimeSettings(
        runtime_profile=RuntimeProfile.LOCAL,
        database_url="postgresql://lotus-idea.example/idea",
    )

    posture = runtime_storage_posture(
        settings=settings,
        durable_storage_backed=False,
        durable_repository_initialization_blocker=DURABLE_REPOSITORY_UNAVAILABLE,
    )

    assert posture.configuration_blockers == (DURABLE_REPOSITORY_UNAVAILABLE,)
    assert posture.write_ready is False
