# Architecture Rules

Use the Lotus layered backend default:

1. `src/app/api` routers/controllers stay thin and depend on `application`,
2. `src/app/application` services orchestrate use cases and depend on `domain` and `ports`,
3. `src/app/domain` logic stays framework-free and must not import FastAPI, API DTOs, infrastructure, persistence, or HTTP clients,
4. `src/app/infrastructure` sits behind `ports` adapters,
5. `src/app/runtime` owns process-local composition of repositories, source adapters, publishers,
   and downstream clients; it may wire concrete adapters but must not import API routes, DTOs, or
   framework modules,
6. `src/app/security` owns caller-context and product-safe authorization policy primitives,
7. `src/app/resilience` owns retry, backoff, timeout, and circuit-breaker policy primitives; concrete downstream clients still belong behind `ports` in `infrastructure`,
8. `src/app/observability` owns structured logging, correlation, tracing, and metrics helpers,
9. generated or scaffold placeholders must be replaced with implementation truth before promotion.

Run `make architecture-boundary-gate` for blocking CI enforcement. Run
`make architecture-boundary-report` when a report artifact is needed for scorecard or review
evidence.
