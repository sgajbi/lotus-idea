from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import os

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message

from app.api.problem_details import problem_details_response
from app.contracts.operational_limits import DEFAULT_HTTP_REQUEST_BODY_MAX_BYTES

TRUSTED_HOSTS_ENV = "LOTUS_IDEA_TRUSTED_HOSTS"
CORS_ALLOWED_ORIGINS_ENV = "LOTUS_IDEA_CORS_ALLOWED_ORIGINS"
MAX_REQUEST_BODY_BYTES_ENV = "LOTUS_IDEA_MAX_REQUEST_BODY_BYTES"
DEFAULT_MAX_REQUEST_BODY_BYTES = DEFAULT_HTTP_REQUEST_BODY_MAX_BYTES

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
JSON_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})
JSON_MEDIA_TYPES = frozenset({"application/json", "application/problem+json"})


class HttpBoundaryConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class HttpBoundaryConfig:
    trusted_hosts: tuple[str, ...] = ("*",)
    cors_allowed_origins: tuple[str, ...] = ()
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES

    def __post_init__(self) -> None:
        if not self.trusted_hosts:
            raise HttpBoundaryConfigurationError("trusted_hosts must not be empty")
        if any(not host.strip() for host in self.trusted_hosts):
            raise HttpBoundaryConfigurationError("trusted_hosts must not contain blanks")
        if any(not origin.strip() for origin in self.cors_allowed_origins):
            raise HttpBoundaryConfigurationError("cors_allowed_origins must not contain blanks")
        if self.max_request_body_bytes <= 0:
            raise HttpBoundaryConfigurationError("max_request_body_bytes must be positive")

    @property
    def enforce_trusted_hosts(self) -> bool:
        return "*" not in self.trusted_hosts


class HttpBoundaryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, config: HttpBoundaryConfig) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rejection = self._boundary_rejection(request)
        if rejection is not None:
            _apply_security_headers(rejection)
            return rejection
        body_rejection = await self._body_size_rejection(request)
        if body_rejection is not None:
            _apply_security_headers(body_rejection)
            return body_rejection
        response = await call_next(request)
        _apply_security_headers(response)
        return response

    def _boundary_rejection(self, request: Request) -> Response | None:
        if self._config.enforce_trusted_hosts and not _host_is_trusted(
            request.headers.get("host", ""),
            self._config.trusted_hosts,
        ):
            return _boundary_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_host",
                title="Invalid host",
                detail="The request host is not accepted by this service.",
            )
        content_length = _content_length(request)
        if content_length is not None and content_length > self._config.max_request_body_bytes:
            return _request_too_large_problem()
        if (
            request.method.upper() in JSON_WRITE_METHODS
            and content_length is not None
            and content_length > 0
            and not _content_type_is_json(request.headers.get("content-type", ""))
        ):
            return _boundary_problem(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="unsupported_media_type",
                title="Unsupported media type",
                detail="JSON write requests must use an application/json content type.",
            )
        return None

    async def _body_size_rejection(self, request: Request) -> Response | None:
        if request.method.upper() not in JSON_WRITE_METHODS:
            return None

        body_parts: list[bytes] = []
        observed_body_bytes = 0
        async for chunk in request.stream():
            observed_body_bytes += len(chunk)
            if observed_body_bytes > self._config.max_request_body_bytes:
                return _request_too_large_problem()
            body_parts.append(chunk)

        body = b"".join(body_parts)
        body_sent = False

        async def replay_body() -> Message:
            nonlocal body_sent
            if body_sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        request._body = body
        request._receive = replay_body
        return None


def configure_http_boundary(app: object, *, config: HttpBoundaryConfig | None = None) -> None:
    boundary_config = config or http_boundary_config_from_environment()
    add_middleware = getattr(app, "add_middleware")
    if boundary_config.cors_allowed_origins:
        add_middleware(
            CORSMiddleware,
            allow_origins=list(boundary_config.cors_allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Idempotency-Key",
                "X-Caller-Capabilities",
                "X-Caller-Roles",
                "X-Caller-Subject",
                "X-Correlation-Id",
                "X-Trace-Id",
            ],
        )
    add_middleware(HttpBoundaryMiddleware, config=boundary_config)


def http_boundary_config_from_environment() -> HttpBoundaryConfig:
    return HttpBoundaryConfig(
        trusted_hosts=_csv_env(TRUSTED_HOSTS_ENV, default=("*",)),
        cors_allowed_origins=_csv_env(CORS_ALLOWED_ORIGINS_ENV, default=()),
        max_request_body_bytes=_positive_int_env(
            MAX_REQUEST_BODY_BYTES_ENV,
            default=DEFAULT_MAX_REQUEST_BODY_BYTES,
        ),
    )


def _csv_env(name: str, *, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    return tuple(item.strip() for item in raw_value.split(","))


def _positive_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise HttpBoundaryConfigurationError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise HttpBoundaryConfigurationError(f"{name} must be positive")
    return parsed


def _host_is_trusted(host_header: str, trusted_hosts: tuple[str, ...]) -> bool:
    host = host_header.split(":", maxsplit=1)[0].strip().lower()
    return bool(host) and host in {trusted_host.lower() for trusted_host in trusted_hosts}


def _content_length(request: Request) -> int | None:
    raw_value = request.headers.get("content-length")
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _content_type_is_json(content_type: str) -> bool:
    media_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    return media_type in JSON_MEDIA_TYPES or media_type.endswith("+json")


def _boundary_problem(*, status_code: int, code: str, title: str, detail: str) -> Response:
    return problem_details_response(
        status_code=status_code,
        code=code,
        title=title,
        detail=detail,
    )


def _request_too_large_problem() -> Response:
    return _boundary_problem(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        code="request_too_large",
        title="Request too large",
        detail="The request body exceeds the configured service limit.",
    )


def _apply_security_headers(response: Response) -> None:
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
