# Runtime Composition Layer

This package owns process-local dependency composition for the Lotus Idea
service.

Keep concrete environment wiring here when it builds repositories, source
adapters, publishers, downstream clients, or configured proof-artifact readers
for API routes, workers, and proof generators.

`settings.py` owns runtime profile and durable repository posture. Keep
environment reads there or in focused runtime composition modules; API routes
must consume typed settings/posture helpers instead of reading environment
variables directly.

Runtime profile semantics:

1. `local` and `test` allow explicit process-local repository fallback.
2. `demo`, `staging`, and `production` require durable write repository
   configuration through `LOTUS_IDEA_DATABASE_URL`.
3. write-capable API routes must fail closed before mutating process-local
   repository state when durable writes are required.

Do not put domain policy, use-case orchestration, HTTP DTOs, or concrete adapter
implementations here:

1. domain policy belongs in `app.domain`,
2. use-case orchestration belongs in `app.application`,
3. HTTP routes and DTOs belong in `app.api`,
4. concrete adapters belong in `app.infrastructure`,
5. dependency protocols belong in `app.ports`.
