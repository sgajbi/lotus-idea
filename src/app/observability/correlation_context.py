from __future__ import annotations

from collections.abc import Callable
import uuid

from app.domain.diagnostic_context import (
    is_product_safe_context_id as is_product_safe_context_id,
    require_product_safe_context_id as require_product_safe_context_id,
)


def generated_correlation_id() -> str:
    return f"corr-{uuid.uuid4()}"


def generated_trace_id() -> str:
    return f"trace-{uuid.uuid4()}"


def sanitize_or_generate_context_id(
    value: str | None,
    generator: Callable[[], str],
) -> str:
    if value is not None and is_product_safe_context_id(value):
        return value.strip()
    return generator()
