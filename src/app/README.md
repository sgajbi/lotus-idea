# Layered Architecture Skeleton

This scaffold is intentionally minimal. Add implementation only when a real service responsibility
exists.

Expected dependency flow:

1. `api` depends on `application`.
2. `application` depends on `domain` and `ports`.
3. `domain` is framework-free and must not import FastAPI, API DTOs, infrastructure, or persistence.
4. `infrastructure` implements `ports`.
5. `security` provides caller-context and authorization policy primitives.
6. `resilience` provides retry, backoff, timeout, and circuit-breaker policy primitives.
7. `observability` provides structured logging, correlation, tracing, and metrics helpers.

Run `make architecture-boundary-report` for the report-only architecture boundary check.
