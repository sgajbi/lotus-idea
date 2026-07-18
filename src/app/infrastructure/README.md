# Infrastructure Layer

Concrete adapters belong here and should implement interfaces from `app.ports`. Infrastructure code
may depend on HTTP clients, databases, queues, or files, but domain and application code must not.

Current adapters include:

1. `lotus_core_sources.py` for source-owned Core evidence retrieval.
2. `outbox/publisher.py` for the source-safe HTTP broker-publisher adapter
   foundation. It is not certified live broker runtime until downstream
   consumers, platform-mesh event runtime publication evidence, Gateway/Workbench proof, and
   supported-feature evidence exist.
3. `downstream_realization.py` for source-safe HTTP Advise, Manage, and Report
   handoff adapter foundations. They are not live downstream realization proof
   until owning repositories certify routes, acceptance behavior, and product
   evidence.
4. `postgres_repository.py` for the opt-in durable repository path, with
   snapshot replacement/detail-write SQL owned by `postgres_snapshot_writes.py`.
