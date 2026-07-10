# Review And Feedback Identity

## Purpose

Review decisions and feedback events are durable business resources. Their
identifiers must remain stable across HTTP retries, client reconnects, and
concurrent submissions. An `Idempotency-Key` protects one transport request;
it does not replace `reviewId` or `feedbackId` as the resource identity.

This contract prevents a retry with a new transport key from applying a second
candidate mutation, audit event, or outbox event. It remains inside Lotus
Idea's review-workflow boundary and grants no suitability, compliance,
execution, accounting, performance, risk, or reporting authority.

## Identity Contract

The immutable identity binds the following fields:

| Resource | Identity fields |
| --- | --- |
| Review decision | resource type, `reviewId`, candidate, evidence packet and content hash, actor subject and role, action, resulting posture, reason codes, decision time, suppression reason, snooze time |
| Feedback event | resource type, `feedbackId`, candidate, evidence packet and content hash, source signals, actor subject and role, outcome, reason codes, recorded time |

Equivalent values represent the same resource even when the caller supplies a
different `Idempotency-Key`. Any changed identity field is a conflict; Lotus
Idea does not overwrite or reinterpret the original resource.

## Decision Matrix

| Existing transport key | Existing resource ID | Content | Result |
| --- | --- | --- | --- |
| no | no | new | `accepted` |
| yes | any | same transport payload | `replayed` |
| yes | any | changed transport payload | `idempotency_conflict` |
| no | yes | equivalent resource identity | `replayed`; reserve the new transport key |
| no | yes | changed resource identity | `review_identity_conflict` |

The transport-key check runs first. This preserves deterministic diagnostics
when both a transport key and resource ID have previously been used.

## Layered Flow

1. The API maps the request DTO and authenticated caller context.
2. The application use case loads the entitled candidate projection.
3. It derives resource identity before applying a lifecycle or posture change.
4. The repository port prechecks transport and resource identity.
5. The domain service runs only for a genuinely new resource.
6. The infrastructure adapter repeats the identity decision atomically before
   candidate, audit, and outbox persistence.

This ordering allows an equivalent retry of a terminal review to replay before
terminal-state validation. Entitlement checks and candidate lookup still run
before identity disclosure.

## PostgreSQL Atomicity

PostgreSQL primary keys remain the final concurrency authority. Delta writes
claim `review_decision_id` or `feedback_event_id` with
`ON CONFLICT DO NOTHING ... RETURNING` before updating candidate state or
inserting audit and outbox rows.

On a collision, the transaction rolls back and reloads a fresh snapshot once:

- equivalent identity returns `replayed` and persists the new transport key;
- changed identity returns `review_identity_conflict`;
- neither outcome duplicates candidate, review, feedback, audit, or outbox
  state;
- database uniqueness errors do not cross the adapter boundary.

No schema migration is required because the review and feedback tables already
use their resource identifiers as primary keys.

## API Contract

Both mutation routes return product-safe RFC 9457-style ProblemDetails:

- `idempotency_conflict` for a reused transport key with changed payload;
- `review_identity_conflict` for a reused review or feedback resource ID with
  changed business content;
- existing candidate-state, action, entitlement, and not-found responses remain
  unchanged.

OpenAPI publishes named 409 examples for both conflict classes. Responses do
not expose the prior actor, evidence, candidate state, or request payload.

## Edge Cases

- A terminal review replay with a new key returns before domain transition
  validation.
- Reusing an ID for another candidate or evidence version conflicts.
- Actor, role, reason, action/outcome, and event-time changes conflict.
- Feedback source-signal lineage is part of identity, preventing evidence drift
  from being treated as the same event.
- An identity conflict does not reserve the losing transport key.
- An equivalent replay does reserve its transport key so later changed reuse of
  that key remains an idempotency conflict.

## Operability

Operation telemetry uses bounded outcomes and the safe error code
`review_identity_conflict`. It must not include request bodies, entitlement
sets, client identifiers, portfolio identifiers, or prior resource content.

Operators should investigate repeated conflicts as producer identity defects,
not repair them by deleting the original review or feedback row. The original
resource and its audit/outbox lineage are authoritative Lotus Idea evidence.

## Runtime Modularity Decision

Resource identity is an internal domain contract with application and
PostgreSQL adapters. A separate identity service would add network consistency,
deployment, and incident-response complexity without workload,
failure-isolation, ownership, or scaling evidence. Runtime separation is not
justified.

## Validation

Run:

```powershell
make review-identity-contract-gate
make openapi-gate
make typecheck
make test-unit
make test-integration
```

Supported-feature promotion remains blocked until merge, remote CI, canonical
runtime proof, documentation and wiki publication, and mainline validation are
complete.
