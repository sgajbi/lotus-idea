# Layered Architecture Skeleton

This scaffold is intentionally minimal. Add implementation only when a real service responsibility
exists.

Expected dependency flow:

1. `api` depends on `application`.
2. `application` depends on `domain` and `ports`.
3. `domain` is framework-free and must not import FastAPI, API DTOs, infrastructure, or persistence.
4. `infrastructure` implements `ports`.
5. `runtime` owns process-local composition of repositories, source adapters, publishers, and
   downstream clients for API routes, workers, and proof generators.
6. `security` provides caller-context and authorization policy primitives.
7. `resilience` provides retry, backoff, timeout, and circuit-breaker policy primitives.
8. `observability` provides structured logging, correlation, tracing, and metrics helpers.

Run `make architecture-boundary-gate` for the blocking architecture boundary check and
`make architecture-boundary-report` when a report artifact is needed. Run
`make private-import-boundary-gate` to verify cross-module callers use public `app.domain`
exports instead of private domain helpers.
