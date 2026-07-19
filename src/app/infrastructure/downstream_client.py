from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import random
import time
from typing import Any, Mapping
from urllib.parse import urlparse

import httpx

from app.contracts.operational_limits import (
    DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
    DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_DEPENDENCY_TIMEOUT_SECONDS,
)
from app.observability.service_slo_metrics import DEPENDENCIES, observe_dependency_request
from app.observability.correlation_context import (
    generated_correlation_id,
    generated_trace_id,
    sanitize_or_generate_context_id,
)


class DownstreamClientConfigurationError(ValueError):
    pass


class DownstreamServiceError(Exception):
    def __init__(
        self,
        *,
        code: str,
        status_code: int | None = None,
        attempt_count: int = 1,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.attempt_count = attempt_count
        super().__init__(code)


@dataclass(frozen=True)
class DownstreamClientConfig:
    base_url: str
    dependency: str | None = None
    timeout_seconds: float = DEFAULT_DEPENDENCY_TIMEOUT_SECONDS
    max_connections: int = DEFAULT_DEPENDENCY_MAX_CONNECTIONS
    max_keepalive_connections: int = DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS
    pool_timeout_seconds: float = 2.0
    retry_max_attempts: int = 1
    retry_initial_backoff_seconds: float = 0.05
    retry_max_backoff_seconds: float = 0.5
    retry_backoff_multiplier: float = 2.0
    retry_jitter_ratio: float = 0.2
    retry_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 502, 503, 504})
    )
    retry_post_without_idempotency: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DownstreamClientConfigurationError(
                "Downstream base_url must be an absolute HTTP(S) URL."
            )
        if self.dependency is not None and self.dependency not in DEPENDENCIES:
            raise DownstreamClientConfigurationError(
                "Downstream dependency must use the governed service vocabulary."
            )
        if self.timeout_seconds <= 0:
            raise DownstreamClientConfigurationError("Downstream timeout_seconds must be positive.")
        if self.max_connections <= 0:
            raise DownstreamClientConfigurationError("Downstream max_connections must be positive.")
        if self.max_keepalive_connections <= 0:
            raise DownstreamClientConfigurationError(
                "Downstream max_keepalive_connections must be positive."
            )
        if self.max_keepalive_connections > self.max_connections:
            raise DownstreamClientConfigurationError(
                "Downstream max_keepalive_connections must not exceed max_connections."
            )
        if self.pool_timeout_seconds <= 0:
            raise DownstreamClientConfigurationError(
                "Downstream pool_timeout_seconds must be positive."
            )
        if self.retry_max_attempts <= 0:
            raise DownstreamClientConfigurationError(
                "Downstream retry_max_attempts must be positive."
            )
        if self.retry_initial_backoff_seconds < 0:
            raise DownstreamClientConfigurationError(
                "Downstream retry_initial_backoff_seconds must not be negative."
            )
        if self.retry_max_backoff_seconds < 0:
            raise DownstreamClientConfigurationError(
                "Downstream retry_max_backoff_seconds must not be negative."
            )
        if self.retry_max_backoff_seconds < self.retry_initial_backoff_seconds:
            raise DownstreamClientConfigurationError(
                "Downstream retry_max_backoff_seconds must be greater than or equal to "
                "retry_initial_backoff_seconds."
            )
        if self.retry_backoff_multiplier < 1:
            raise DownstreamClientConfigurationError(
                "Downstream retry_backoff_multiplier must be greater than or equal to 1."
            )
        if self.retry_jitter_ratio < 0 or self.retry_jitter_ratio > 1:
            raise DownstreamClientConfigurationError(
                "Downstream retry_jitter_ratio must be between 0 and 1."
            )
        invalid_statuses = [
            status_code
            for status_code in self.retry_status_codes
            if status_code < 100 or status_code > 599
        ]
        if invalid_statuses:
            raise DownstreamClientConfigurationError(
                "Downstream retry_status_codes must be valid HTTP status codes."
            )

    def limits(self) -> httpx.Limits:
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
        )

    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=self.timeout_seconds,
            pool=self.pool_timeout_seconds,
        )


def build_trace_headers(
    *,
    correlation_id: str | None,
    trace_id: str | None,
    idempotency_key: str | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if correlation_id:
        headers["X-Correlation-Id"] = sanitize_or_generate_context_id(
            correlation_id,
            generated_correlation_id,
        )
    if trace_id:
        headers["X-Trace-Id"] = sanitize_or_generate_context_id(trace_id, generated_trace_id)
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


class DownstreamJsonClient:
    def __init__(
        self,
        config: DownstreamClientConfig,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter_random: Callable[[], float] = random.random,
    ) -> None:
        self._config = config
        self._owns_client = client is None
        self._sleep = sleep
        self._jitter_random = jitter_random
        self._client = client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout(),
            limits=config.limits(),
        )

    @property
    def owns_client(self) -> bool:
        return self._owns_client

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "DownstreamJsonClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def get_json(
        self,
        path: str,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        additional_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            path,
            correlation_id=correlation_id,
            trace_id=trace_id,
            additional_headers=additional_headers,
        )

    def post_json(
        self,
        path: str,
        *,
        json_payload: dict[str, Any],
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
        additional_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            path,
            json_payload=json_payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            additional_headers=additional_headers,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
        additional_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        try:
            payload = self._request_json_with_retries(
                method,
                path,
                json_payload=json_payload,
                correlation_id=correlation_id,
                trace_id=trace_id,
                idempotency_key=idempotency_key,
                additional_headers=additional_headers,
            )
        except DownstreamServiceError as error:
            self._observe_dependency_request(
                method=method,
                outcome=_dependency_outcome(error),
                duration_seconds=time.perf_counter() - started_at,
            )
            raise
        self._observe_dependency_request(
            method=method,
            outcome="accepted",
            duration_seconds=time.perf_counter() - started_at,
        )
        return payload

    def _request_json_with_retries(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
        additional_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        retry_attempt_limit = self._retry_attempt_limit(
            method=method,
            idempotency_key=idempotency_key,
        )
        headers = build_trace_headers(
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        _add_request_headers(headers, additional_headers)
        attempt_count = 0
        while True:
            attempt_count += 1
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json_payload,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                if attempt_count < retry_attempt_limit:
                    self._sleep_before_retry(attempt_count, response=None)
                    continue
                raise DownstreamServiceError(
                    code="upstream_timeout",
                    attempt_count=attempt_count,
                ) from exc
            except httpx.HTTPError as exc:
                if attempt_count < retry_attempt_limit:
                    self._sleep_before_retry(attempt_count, response=None)
                    continue
                raise DownstreamServiceError(
                    code="upstream_unavailable",
                    attempt_count=attempt_count,
                ) from exc

            if (
                response.status_code in self._config.retry_status_codes
                and attempt_count < retry_attempt_limit
            ):
                self._sleep_before_retry(attempt_count, response=response)
                continue
            break

        if 400 <= response.status_code < 500:
            raise DownstreamServiceError(
                code="upstream_rejected_request",
                status_code=response.status_code,
                attempt_count=attempt_count,
            )
        if response.status_code >= 500:
            raise DownstreamServiceError(
                code="upstream_unavailable",
                status_code=response.status_code,
                attempt_count=attempt_count,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise DownstreamServiceError(
                code="upstream_malformed_response",
                status_code=response.status_code,
                attempt_count=attempt_count,
            ) from exc

        if not isinstance(payload, dict):
            raise DownstreamServiceError(
                code="upstream_malformed_response",
                status_code=response.status_code,
                attempt_count=attempt_count,
            )
        return payload

    def _observe_dependency_request(
        self,
        *,
        method: str,
        outcome: str,
        duration_seconds: float,
    ) -> None:
        if self._config.dependency is None:
            return
        observe_dependency_request(
            dependency=self._config.dependency,
            method=method,
            outcome=outcome,
            duration_seconds=duration_seconds,
        )

    def _retry_attempt_limit(self, *, method: str, idempotency_key: str | None) -> int:
        if self._config.retry_max_attempts <= 1:
            return 1
        if method.upper() != "POST":
            return self._config.retry_max_attempts
        if idempotency_key or self._config.retry_post_without_idempotency:
            return self._config.retry_max_attempts
        return 1

    def _sleep_before_retry(self, attempt_count: int, *, response: httpx.Response | None) -> None:
        delay_seconds = self._retry_delay_seconds(attempt_count, response=response)
        if delay_seconds > 0:
            self._sleep(delay_seconds)

    def _retry_delay_seconds(
        self,
        attempt_count: int,
        *,
        response: httpx.Response | None,
    ) -> float:
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return min(retry_after, self._config.retry_max_backoff_seconds)
        backoff = self._config.retry_initial_backoff_seconds * (
            self._config.retry_backoff_multiplier ** max(attempt_count - 1, 0)
        )
        capped_backoff = min(backoff, self._config.retry_max_backoff_seconds)
        return self._apply_jitter(capped_backoff)

    def _apply_jitter(self, delay_seconds: float) -> float:
        if delay_seconds <= 0 or self._config.retry_jitter_ratio == 0:
            return delay_seconds
        random_sample = min(max(self._jitter_random(), 0.0), 1.0)
        jitter_factor = 1 - (self._config.retry_jitter_ratio * random_sample)
        return delay_seconds * jitter_factor


def _dependency_outcome(error: DownstreamServiceError) -> str:
    return {
        "upstream_timeout": "timeout",
        "upstream_rejected_request": "rejected",
        "upstream_malformed_response": "malformed",
    }.get(error.code, "unavailable")


def _add_request_headers(
    headers: dict[str, str], additional_headers: Mapping[str, str] | None
) -> None:
    if additional_headers is None:
        return
    protected_headers = {key.lower() for key in headers}
    for name, value in additional_headers.items():
        normalized_name = name.strip()
        normalized_value = value.strip()
        if not normalized_name or not normalized_value:
            raise DownstreamClientConfigurationError(
                "additional request headers must have non-blank names and values."
            )
        if normalized_name.lower() in protected_headers:
            raise DownstreamClientConfigurationError(
                f"additional request header must not override {normalized_name}."
            )
        headers[normalized_name] = normalized_value


def _retry_after_seconds(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    raw_retry_after = response.headers.get("Retry-After")
    if raw_retry_after is None:
        return None
    try:
        retry_after = float(raw_retry_after)
    except ValueError:
        return None
    if retry_after < 0:
        return None
    return retry_after
