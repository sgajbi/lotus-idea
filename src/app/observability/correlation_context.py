from __future__ import annotations

from collections.abc import Callable
import re
import uuid

_MAX_CONTEXT_ID_LENGTH = 96
_CONTEXT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.:-]{0,95}$")
_SENSITIVE_CONTEXT_FRAGMENTS = (
    "access_token",
    "api-key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "password",
    "secret",
    "token",
)
_PORTFOLIO_LIKE_PATTERN = re.compile(r"\bPB_[A-Z0-9_]{6,}\b", re.IGNORECASE)


def generated_correlation_id() -> str:
    return f"corr-{uuid.uuid4()}"


def generated_trace_id() -> str:
    return f"trace-{uuid.uuid4()}"


def is_product_safe_context_id(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    if not normalized or len(normalized) > _MAX_CONTEXT_ID_LENGTH:
        return False
    if not _CONTEXT_ID_PATTERN.fullmatch(normalized):
        return False
    lowered = normalized.lower()
    if any(fragment in lowered for fragment in _SENSITIVE_CONTEXT_FRAGMENTS):
        return False
    return _PORTFOLIO_LIKE_PATTERN.search(normalized) is None


def require_product_safe_context_id(value: str | None, field_name: str) -> str:
    if not is_product_safe_context_id(value):
        raise ValueError(f"{field_name} must be a product-safe diagnostic identifier")
    assert value is not None
    return value.strip()


def sanitize_or_generate_context_id(
    value: str | None,
    generator: Callable[[], str],
) -> str:
    if value is not None and is_product_safe_context_id(value):
        return value.strip()
    return generator()
