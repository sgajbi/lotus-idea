# Conversion Outcome Identity And Lifecycle

## Current Scope

Lotus Idea records source-owned facts about what happened after an approved idea conversion intent.
It owns the intent-to-outcome evidence history and current readiness posture. It does not become the
authority for proposals, mandate actions, reports, execution, suitability, compliance, portfolio
accounting, performance, or risk.

| Concern | Current contract |
| --- | --- |
| Source authority | The target service owns the reported outcome fact. |
| Lotus Idea authority | Validate, persist, audit, replay, and expose conversion history and posture. |
| History | Append-only; corrections add a linked source event. |
| Current posture | Derived only from a policy-valid history. |
| Downstream action | Never authorized by an outcome record. |
| Support claim | Internal RFC-0002 foundation; supported-feature promotion remains gated. |

## Identity Contract

`conversionOutcomeId` is the durable source-event resource identity. `Idempotency-Key` is only the
transport retry identity. A caller may replay an identical source event with a new transport key;
Lotus Idea returns `replayed` without adding outcome, audit, or outbox records.

The immutable identity includes:

| Field | Purpose |
| --- | --- |
| `conversionOutcomeId` | Stable source-event resource identity. |
| `conversionIntentId` | Binds the event to one governed conversion intent. |
| `target` and `sourceSystem` | Preserve target ownership and source authority. |
| `sourceEventVersion` | Orders facts within one intent stream. |
| `status` and `downstreamReference` | Capture the reported outcome fact. |
| `recordedAtUtc` and `actorSubject` | Establish source time and accountable actor. |
| correction fields | Link and explain an append-only correction. |

The API separates `idempotency_conflict` from `conversion_outcome_conflict`. This prevents a
transport-key collision from being mistaken for a contradictory source fact.

## Lifecycle And Correction Policy

Policy `idea-conversion-outcome-v1` accepts these uncorrected progressions:

```text
requested -> accepted -> completed
          -> rejected
          -> failed

accepted  -> completed
```

`accepted`, `rejected`, `failed`, and `requested` may be initial source facts; `completed` may not.
Accepted and completed events require a downstream reference. Terminal events cannot transition
again unless the source emits the next contiguous version with both:

1. `supersedesConversionOutcomeId` pointing to the current event;
2. a non-empty `correctionReason`.

Corrections do not rewrite or delete prior evidence. Version gaps, duplicate versions, time
regression, changed stream ownership, unlinked corrections, and contradictory terminal transitions
fail closed.

## Application And Adapter Flow

```text
API route
  -> request DTO mapper
  -> conversion outcome use case
  -> lifecycle policy and conversion domain
  -> conversion workflow repository port
  -> in-memory or PostgreSQL adapter
  -> outcome, idempotency, audit, and outbox persistence
```

The use case resolves the intent before deriving source identity, performs a bounded identity
precheck, loads only that intent's history, applies domain policy, and then invokes the repository
mutation. Both repository providers repeat identity and progression checks at the persistence
boundary.

## PostgreSQL Atomicity And Legacy Quarantine

PostgreSQL enforces one row for each `conversionOutcomeId` and one source version for each
`conversionIntentId`. Outcome insertion uses an atomic conflict claim. A collision triggers one
fresh-snapshot retry so the winner is classified as an equivalent replay or a typed outcome
conflict before side effects are committed.

Migration 006 ranks historical events, adds lifecycle metadata, and snapshots every event from a
contradictory legacy stream into `idea_conversion_outcome_quarantine`. It deliberately leaves the
active source rows intact. Quarantined streams:

1. remain available for reconciliation and audit;
2. have no authoritative current posture;
3. are excluded from downstream readiness counts;
4. reject new progression until their history is reconciled.

## Operability And API Truth

Candidate detail exposes both `conversionOutcomes` (full history) and `currentConversionOutcomes`
(one policy-valid posture per intent). Audit and outbox records carry source version and correction
posture. OpenAPI publishes distinct 409 examples for transport idempotency and source-history
conflicts.

Validation entry points:

```powershell
make conversion-outcome-contract-gate
make migration-contract-gate
make openapi-gate
make endpoint-certification-gate
make postgres-integration-gate
```

The PostgreSQL integration gate includes two-connection races for equivalent identities and
competing versions, plus a migration scenario that proves invalid legacy history is preserved,
quarantined, and excluded from readiness.

## Runtime Modularity Decision

The implementation uses separate domain-policy, application-use-case, port, and PostgreSQL adapter
modules. It remains part of the existing Lotus Idea process. There is no evidence of independent
scaling, failure isolation, deployment cadence, ownership, or security needs that justify another
runtime service. A future process split requires measured workload or operability evidence and a
separate RFC.
