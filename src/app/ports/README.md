# Ports Layer

Define repository, downstream client, clock, audit, idempotency, and event-publisher protocols here
before adding concrete infrastructure adapters.

Current implemented port:

1. `idea_repository.py` defines the central repository workflow protocols for
   candidate snapshots, candidate persistence, evidence replay, lifecycle
   mutation, review and feedback mutation, conversion mutation, report
   evidence-pack requests, and AI explanation reads. Application use cases must
   depend on these protocols instead of declaring local repository protocols,
   so the future durable repository adapter has one governed contract surface.
2. `core_sources.py` defines the Core high-cash evidence port used by RFC-0002
   Slice 05 application orchestration. It accepts Core source refs and a
   source-reported cash-weight value only; `lotus-idea` must not infer that
   weight from Core cash totals or market values.
