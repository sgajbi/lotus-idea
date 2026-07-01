from __future__ import annotations

from collections.abc import Callable, Collection, Mapping


def forbidden_content_validator(
    forbidden_keys: Collection[str],
    forbidden_text_fragments: Collection[str],
) -> Callable[..., None]:
    def validator(value: object, errors: list[str], path: str = "$") -> None:
        validate_forbidden_content(
            value,
            errors,
            forbidden_keys,
            forbidden_text_fragments,
            path,
        )

    return validator


def validate_forbidden_content(
    value: object,
    errors: list[str],
    forbidden_keys: Collection[str],
    forbidden_text_fragments: Collection[str],
    path: str = "$",
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text in forbidden_keys:
                errors.append(f"{next_path}: forbidden source-sensitive key is present")
            validate_forbidden_content(
                nested,
                errors,
                forbidden_keys,
                forbidden_text_fragments,
                next_path,
            )
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            validate_forbidden_content(
                nested,
                errors,
                forbidden_keys,
                forbidden_text_fragments,
                f"{path}[{index}]",
            )
        return
    if isinstance(value, str):
        for fragment in forbidden_text_fragments:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")
