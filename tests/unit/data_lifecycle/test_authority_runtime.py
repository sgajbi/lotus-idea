import pytest

from app.runtime.lifecycle_authority_state import (
    LIFECYCLE_AUTHORITY_BASE_URL_ENV,
    LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV,
    get_lifecycle_authority_dependencies,
    reset_lifecycle_authority_dependencies,
)


def test_runtime_builds_and_caches_lifecycle_authority_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_lifecycle_authority_dependencies()
    monkeypatch.setenv(
        LIFECYCLE_AUTHORITY_BASE_URL_ENV,
        "https://lifecycle-authority.internal",
    )
    monkeypatch.setenv(LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV, "1.5")

    first = get_lifecycle_authority_dependencies()
    second = get_lifecycle_authority_dependencies()

    assert first[0] is second[0]
    assert first[1] is second[1]
    reset_lifecycle_authority_dependencies()


@pytest.mark.parametrize("timeout", ["invalid", "0", "10.1"])
def test_runtime_rejects_invalid_lifecycle_authority_timeout(
    monkeypatch: pytest.MonkeyPatch,
    timeout: str,
) -> None:
    reset_lifecycle_authority_dependencies()
    monkeypatch.setenv(
        LIFECYCLE_AUTHORITY_BASE_URL_ENV,
        "https://lifecycle-authority.internal",
    )
    monkeypatch.setenv(LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV, timeout)

    with pytest.raises(RuntimeError, match=LIFECYCLE_AUTHORITY_TIMEOUT_SECONDS_ENV):
        get_lifecycle_authority_dependencies()

    reset_lifecycle_authority_dependencies()


def test_runtime_requires_lifecycle_authority_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_lifecycle_authority_dependencies()
    monkeypatch.delenv(LIFECYCLE_AUTHORITY_BASE_URL_ENV, raising=False)

    with pytest.raises(RuntimeError, match=LIFECYCLE_AUTHORITY_BASE_URL_ENV):
        get_lifecycle_authority_dependencies()
