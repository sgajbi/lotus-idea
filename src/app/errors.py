from __future__ import annotations

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    type: str = Field(
        default="about:blank",
        description="Stable problem type URI or about:blank when no external type is assigned.",
        examples=["about:blank"],
    )

    status: int = Field(..., description="HTTP response status code.", examples=[400])
    code: str = Field(
        ..., description="Stable product-safe error code.", examples=["invalid_request"]
    )
    title: str = Field(
        ..., description="Short product-safe error title.", examples=["Invalid request"]
    )
    detail: str = Field(
        ...,
        description="Product-safe remediation guidance without raw payload or sensitive content.",
        examples=["Correct the request fields and retry."],
    )


def problem_response(status_code: int, code: str, title: str, detail: str) -> JSONResponse:
    problem = ProblemDetails(status=status_code, code=code, title=title, detail=detail)
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )
