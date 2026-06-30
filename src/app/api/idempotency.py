from __future__ import annotations

IDEMPOTENCY_KEY_REQUIRED_MESSAGE = "idempotency key is required"


def validate_idempotency_key(idempotency_key: str) -> None:
    if not idempotency_key.strip():
        raise ValueError(IDEMPOTENCY_KEY_REQUIRED_MESSAGE)
