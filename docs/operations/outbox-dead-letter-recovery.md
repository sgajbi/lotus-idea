# Outbox Dead-Letter Recovery

## Purpose

This runbook governs inspection and one-time re-drive of Lotus Idea's local
outbox dead letters. It does not certify an external broker, downstream
consumer, platform mesh publication, Gateway/Workbench behavior, or a
supported product feature.

## Control Surface

| Action | Endpoint | Required capability | Mutation |
| --- | --- | --- | --- |
| Inspect quarantine | `GET /api/v1/outbox-delivery/dead-letters?limit=100` | `idea.outbox-recovery.read` | No |
| Re-drive one event | `POST /api/v1/outbox-delivery/dead-letters/{supportReference}/redrive` | `idea.outbox-recovery.redrive` | Yes |

Both routes require the `operator` role. Production-like profiles also require
trusted ingress provenance through `X-Lotus-Trusted-Caller-Context`. Re-drive
requires `Idempotency-Key`, a bounded snake-case `reason`, and a governed
`changeReference`.

## Decision Procedure

1. Confirm `/health/ready` and `/api/v1/outbox-delivery/readiness` do not report
   repository or publisher configuration failures.
2. List dead letters and record the opaque `supportReference`, event family,
   schema version, retry count, failure reason, and failure timestamps in the
   operational case. Do not request database payloads or aggregate ids.
3. Confirm the event family and `v1` schema remain allowlisted. When
   `recoveryEligible` is false, leave the event quarantined and escalate to
   `lotus-idea-operations`.
4. Correct the external cause under an approved change, then submit one
   re-drive with a new `Idempotency-Key`, bounded reason, and change reference.
5. Treat `published` as a local publication result only. Verify downstream
   delivery through the owning consumer's evidence.

## Outcome Handling

| Outcome | Operator response |
| --- | --- |
| `published` | Record `recoveryReference`; continue downstream verification. |
| `replayed` | No new publication occurred; use the original recovery record. |
| `idempotency_conflict` | Stop and reconcile the reused key with the original request. |
| `dead_lettered` | Publication failed; the event remains quarantined with no automatic retry. |
| `recovery_attempt_limit_reached` | Escalate to the owning service; direct database mutation is prohibited. |
| `recovery_lease_conflict` | Another attempt owns or changed the event; re-inspect before action. |

## Preserved Evidence

Migration `004_outbox_dead_letter_recovery` stores an append-only recovery
record with the actor, reason, change reference, hashed idempotency identity,
new lease attempt, and original retry/failure history. Successful publication
also retains prior retry count, failure reason, and first/last failure times on
the outbox event. API responses and operation telemetry omit event payloads,
aggregate ids, portfolio/client identifiers, and raw idempotency keys.

PostgreSQL resolves `supportReference` with the same SHA-256 derivation as the
domain through an immutable expression index. The selector locks only the exact
event and remains state-aware so a competing request sees `lease_conflict`
rather than `not_found`. It must never fall back to a fixed-size recent-row
scan, because that makes older dead letters unreachable and locks unrelated
outbox work.

## Validation

```powershell
make outbox-recovery-contract-gate
.\.venv\Scripts\python.exe -m pytest tests/unit/test_outbox_recovery.py tests/unit/test_outbox_recovery_application.py tests/unit/test_postgres_outbox_delivery_adapter.py tests/integration/test_outbox_recovery_api.py -q
make postgres-integration-gate
```

The PostgreSQL gate must run with
`LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1` against a disposable database. It
proves migration execution, delivery claim, dead-letter transition, connection
reload, exact support-reference recovery, durable audit replay, and schema
rollback/reapply.

Promotion remains blocked until the full repository gates, external broker and
consumer proof, merged-main validation, and supported-feature governance pass.
