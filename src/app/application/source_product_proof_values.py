from __future__ import annotations


def text_sequence(
    value: object,
    *,
    default: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)
