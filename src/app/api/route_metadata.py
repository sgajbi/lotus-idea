from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict

from pydantic import BaseModel


class RouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]
