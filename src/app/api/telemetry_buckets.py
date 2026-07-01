from __future__ import annotations


def bounded_count_bucket(value: int, *, overflow_label: str = "100+") -> str:
    if value == 0:
        return "0"
    if value <= 10:
        return "1-10"
    if value <= 100:
        return "11-100"
    return overflow_label
