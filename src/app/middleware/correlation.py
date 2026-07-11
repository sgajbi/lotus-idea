from __future__ import annotations

from collections.abc import Awaitable, Callable
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.observability.correlation_context import (
    generated_correlation_id,
    generated_trace_id,
    sanitize_or_generate_context_id,
)
from app.observability.service_slo_metrics import observe_http_request


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, service_name: str) -> None:
        super().__init__(app)
        self._service_name = service_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = sanitize_or_generate_context_id(
            request.headers.get("X-Correlation-Id"),
            generated_correlation_id,
        )
        trace_id = sanitize_or_generate_context_id(
            request.headers.get("X-Trace-Id"),
            generated_trace_id,
        )
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            observe_http_request(
                method=request.method,
                route=_route_template(request),
                status_code=500,
                duration_seconds=time.perf_counter() - start,
            )
            raise
        duration_seconds = time.perf_counter() - start
        observe_http_request(
            method=request.method,
            route=_route_template(request),
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        duration_ms = duration_seconds * 1000.0
        response.headers["X-Correlation-Id"] = correlation_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Service-Name"] = self._service_name
        response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.3f}"
        return response


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path.startswith("/") else "/unknown"
