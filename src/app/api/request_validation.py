from __future__ import annotations

from typing import TypeVar

_T = TypeVar("_T")


def require_non_empty_reason_codes(value: tuple[_T, ...]) -> tuple[_T, ...]:
    if not value:
        raise ValueError("reasonCodes is required")
    return tuple(value)
