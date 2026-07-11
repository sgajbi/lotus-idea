import pytest

from app.runtime.lotus_ai_attestation_state import (
    LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV,
    LOTUS_AI_BASE_URL_ENV,
    get_lotus_ai_attestation_dependencies,
    reset_lotus_ai_attestation_dependencies,
)


def test_runtime_builds_and_caches_configured_attestation_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_lotus_ai_attestation_dependencies()
    monkeypatch.setenv(LOTUS_AI_BASE_URL_ENV, "https://lotus-ai.internal")
    monkeypatch.setenv(LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV, "1.5")

    first = get_lotus_ai_attestation_dependencies()
    second = get_lotus_ai_attestation_dependencies()

    assert first[0] is second[0]
    assert first[1] is second[1]
    reset_lotus_ai_attestation_dependencies()


@pytest.mark.parametrize("timeout", ["invalid", "0", "10.1"])
def test_runtime_rejects_missing_or_invalid_trust_configuration(
    monkeypatch: pytest.MonkeyPatch, timeout: str
) -> None:
    reset_lotus_ai_attestation_dependencies()
    monkeypatch.setenv(LOTUS_AI_BASE_URL_ENV, "https://lotus-ai.internal")
    monkeypatch.setenv(LOTUS_AI_ATTESTATION_TIMEOUT_SECONDS_ENV, timeout)

    with pytest.raises(RuntimeError):
        get_lotus_ai_attestation_dependencies()

    reset_lotus_ai_attestation_dependencies()


def test_runtime_requires_lotus_ai_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_lotus_ai_attestation_dependencies()
    monkeypatch.delenv(LOTUS_AI_BASE_URL_ENV, raising=False)

    with pytest.raises(RuntimeError, match=LOTUS_AI_BASE_URL_ENV):
        get_lotus_ai_attestation_dependencies()
