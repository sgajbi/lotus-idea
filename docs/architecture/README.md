# lotus-idea Architecture

This directory records architecture decisions and service boundaries for
`lotus-idea`.

The initial architecture posture is:

1. separate domain service, not a module inside `lotus-advise`, `lotus-manage`,
   or `lotus-ai`,
2. source-owned upstream facts with provenance, not duplicated calculations,
3. deterministic idea lifecycle first, AI assistance second,
4. human-governed review and conversion, not autonomous execution,
5. implementation only through governed RFC slices.

Architecture decisions live under `docs/architecture/adr/`.

The durable product blueprint lives in `docs/LOTUS_IDEA_BLUEPRINT.md`. Use it
as the repo-authored anchor for product definition, source-authority boundaries,
AI/human-governance posture, and non-claim rules before changing architecture
or RFC implementation scope. It is context truth, not support-promotion
evidence.

Codebase cleanup and modularity evidence lives in:

1. `docs/architecture/CODEBASE-REVIEW-PLAYBOOK.md`
2. `docs/architecture/CODEBASE-REVIEW-LEDGER.md`

Those files distinguish design modularity from runtime modularity. Use them to
record bounded internal-module refactors and keep separate deployable boundary
decisions tied to measured workload, failure-isolation, ownership, security, or
operability evidence.
