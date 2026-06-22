# Runtime Composition Layer

This package owns process-local dependency composition for the Lotus Idea
service.

Keep concrete environment wiring here when it builds repositories, source
adapters, publishers, or downstream clients for API routes, workers, and proof
generators.

Do not put domain policy, use-case orchestration, HTTP DTOs, or concrete adapter
implementations here:

1. domain policy belongs in `app.domain`,
2. use-case orchestration belongs in `app.application`,
3. HTTP routes and DTOs belong in `app.api`,
4. concrete adapters belong in `app.infrastructure`,
5. dependency protocols belong in `app.ports`.
