from __future__ import annotations

from typing import Any


def build_named_openapi_examples(
    examples: dict[str, dict[str, Any]],
    summaries: dict[str, str],
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "summary": summaries[name],
            "value": value,
        }
        for name, value in examples.items()
    }


def apply_named_response_examples(
    openapi_schema: dict[str, Any],
    *,
    operation_path: str,
    examples: dict[str, dict[str, Any]],
) -> None:
    operation = openapi_schema["paths"][operation_path]["post"]
    media = operation["responses"]["200"]["content"]["application/json"]
    media.pop("example", None)
    media["examples"] = examples


__all__ = [
    "apply_named_response_examples",
    "build_named_openapi_examples",
]
