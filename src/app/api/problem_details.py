from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.errors import ProblemDetails as ProblemDetails
from app.errors import problem_response as _problem_response


class ProblemDetailsHTTPException(HTTPException):
    """Product-safe boundary error whose stable code survives global handling."""

    def __init__(self, *, status_code: int, code: str, title: str, detail: str) -> None:
        self.code = code
        self.title = title
        super().__init__(status_code=status_code, detail=detail)


def _problem_details_example(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "type": "about:blank",
        "status": status_code,
        "code": code,
        "title": title,
        "detail": detail,
    }


def _problem_details_content(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    content = dict(payload)
    content["schema"] = {"$ref": "#/components/schemas/ProblemDetails"}
    return {
        "application/json": dict(content),
        "application/problem+json": dict(content),
    }


def problem_response_metadata(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    description: str,
) -> dict[int | str, dict[str, Any]]:
    return {
        status_code: {
            "model": ProblemDetails,
            "description": description,
            "content": _problem_details_content(
                {
                    "example": _problem_details_example(
                        status_code=status_code,
                        code=code,
                        title=title,
                        detail=detail,
                    )
                }
            ),
        }
    }


def merged_problem_response_metadata(
    *,
    status_code: int,
    description: str,
    responses: tuple[dict[int | str, dict[str, Any]], ...],
) -> dict[int | str, dict[str, Any]]:
    examples: dict[str, dict[str, Any]] = {}
    for metadata in responses:
        response = metadata[status_code]
        media = response["content"]["application/json"]
        if "example" in media:
            example = media["example"]
            examples[str(example["code"])] = {
                "summary": str(example["title"]),
                "value": example,
            }
            continue
        for key, example_metadata in media.get("examples", {}).items():
            value = example_metadata["value"]
            examples[str(key)] = {
                "summary": str(example_metadata.get("summary", value["title"])),
                "value": value,
            }
    return {
        status_code: {
            "model": ProblemDetails,
            "description": description,
            "content": _problem_details_content({"examples": examples}),
        }
    }


def invalid_request_metadata(
    *,
    detail: str = "Correct the request fields and retry.",
    description: str = "Request validation failed.",
) -> dict[int | str, dict[str, Any]]:
    return problem_response_metadata(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail=detail,
        description=description,
    )


def permission_denied_metadata(
    *,
    detail: str,
    description: str,
) -> dict[int | str, dict[str, Any]]:
    return problem_response_metadata(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail=detail,
        description=description,
    )


def not_found_metadata(
    *,
    code: str,
    title: str,
    detail: str,
    description: str,
) -> dict[int | str, dict[str, Any]]:
    return problem_response_metadata(
        status_code=status.HTTP_404_NOT_FOUND,
        code=code,
        title=title,
        detail=detail,
        description=description,
    )


def conflict_metadata(
    *,
    code: str,
    title: str,
    detail: str,
    description: str,
) -> dict[int | str, dict[str, Any]]:
    return problem_response_metadata(
        status_code=status.HTTP_409_CONFLICT,
        code=code,
        title=title,
        detail=detail,
        description=description,
    )


def service_unavailable_metadata(
    *,
    code: str,
    title: str,
    detail: str,
    description: str,
) -> dict[int | str, dict[str, Any]]:
    return problem_response_metadata(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=code,
        title=title,
        detail=detail,
        description=description,
    )


def problem_details_response(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
) -> JSONResponse:
    return _problem_response(
        status_code=status_code,
        code=code,
        title=title,
        detail=detail,
    )


def permission_denied_problem(detail: str) -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail=detail,
    )


def invalid_request_problem(detail: str) -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail=detail,
    )
