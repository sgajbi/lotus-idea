from __future__ import annotations

from collections.abc import Mapping, Sequence


def validate_forbidden_contract_text(
    value: object,
    errors: list[str],
    forbidden_text_fragments: Sequence[str],
    path: str = "$",
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            validate_forbidden_contract_text(
                nested,
                errors,
                forbidden_text_fragments,
                f"{path}.{key}",
            )
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, nested in enumerate(value):
            validate_forbidden_contract_text(
                nested,
                errors,
                forbidden_text_fragments,
                f"{path}[{index}]",
            )
        return
    if isinstance(value, str):
        for forbidden_text in forbidden_text_fragments:
            if forbidden_text in value:
                errors.append(f"{path}: forbidden contract text `{forbidden_text}`")
