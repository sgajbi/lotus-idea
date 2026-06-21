# Architecture Rules

Use the Lotus layered backend default:

1. `src/app/api` routers/controllers stay thin and depend on `application`,
2. `src/app/application` services orchestrate use cases and depend on `domain` and `ports`,
3. `src/app/domain` logic stays framework-free and must not import FastAPI, API DTOs, infrastructure, persistence, or HTTP clients,
4. `src/app/infrastructure` sits behind `ports` adapters,
5. `src/app/security` owns caller-context and product-safe authorization policy primitives,
6. `src/app/resilience` owns retry, backoff, timeout, and circuit-breaker policy primitives; concrete downstream clients still belong behind `ports` in `infrastructure`,
7. `src/app/observability` owns structured logging, correlation, tracing, and metrics helpers,
8. generated or scaffold placeholders must be replaced with implementation truth before promotion.

Run `make architecture-boundary-report` for report-only evidence. Promote it to blocking only after
the signal is stable, deterministic, low-noise, and exception policy is clear.
