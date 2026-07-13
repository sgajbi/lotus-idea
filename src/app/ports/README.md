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
3. `outbox/publisher.py` defines the outbox event publisher port and bounded
   publish outcome used by the run-once outbox delivery orchestration.
   Infrastructure adapters must return product-safe failure reasons and must
   not expose raw broker responses to domain or application code.
4. `downstream_realization.py` defines source-safe downstream handoff ports for
   Advise proposal intents, Manage action intents, and Report evidence-pack
   request materialization. These ports do not grant downstream authority or
   certify live downstream execution.
