# Ports Layer

Define repository, downstream client, clock, audit, idempotency, and event-publisher protocols here
before adding concrete infrastructure adapters.

Current implemented port:

1. `core_sources.py` defines the Core high-cash evidence port used by RFC-0002
   Slice 05 application orchestration. It accepts Core source refs and a
   source-reported cash-weight value only; `lotus-idea` must not infer that
   weight from Core cash totals or market values.
