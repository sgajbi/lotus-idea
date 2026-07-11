# PostgreSQL Disaster Recovery

## Current Posture

`lotus-idea` has implementation-backed logical backup/restore validation,
provider-restored database validation, replay/fencing proof, recovery-aware
readiness, and a weekly attested CI drill. Production PITR remains
`not_certified` until approved managed-provider topology and a successful
physical base-backup/WAL exercise are evidenced.

## Operator Decision Table

| Posture | Readiness | Writes | Operator action |
| --- | --- | --- | --- |
| `normal` | follows durable repository posture | allowed only when durable storage is ready | normal operations |
| `draining` | `503 draining` | blocked with `service_draining` | quiesce traffic and workers before restore/cutover |
| `restoring` | `503 restoring` | blocked with `service_restoring` | restore and validate a clean target |
| `degraded` or invalid | `503 degraded` | blocked with `service_recovery_degraded` | investigate; do not cut over |

Configure posture with `LOTUS_IDEA_RECOVERY_POSTURE`. Invalid values fail
closed and are never echoed in responses.

## Recovery Gate

An authorized cutover requires all of the following:

1. approved backup identity, jurisdiction, operator, incident, and recovery
   point;
2. restore validation with all 17 owned tables, source-safe hashes, valid
   constraints/indexes, and zero relationship/state violations;
3. RPO no greater than 15 minutes and RTO no greater than 60 minutes;
4. candidate and outbox recovery replay, downstream reconciliation fencing,
   stale-lease rejection, and unchanged table hashes;
5. incident commander and database-operations authorization;
6. healthy `/health/live` and `/health/ready` after posture returns to
   `normal`.

## Commands

```powershell
make postgres-disaster-recovery-seed
make postgres-disaster-recovery-drill
make postgres-disaster-recovery-resume
make disaster-recovery-proof-gate
```

The first two commands require separate disposable source and target database
URLs. Never use the fixture seed against a database containing user tables.

## Evidence Boundary

The scheduled workflow stores source-safe restore/resume JSON for 90 days and
attests its provenance. Logical `pg_dump` evidence always carries
`pitrProof=false`; it is useful validation but is not physical/WAL recovery
certification. Migration rollback, internal repository replay, and application
re-drive are separate controls and must not be cited as database DR.

The complete operating procedure, escalation, failover, rollback, encryption,
residency, and evidence requirements are maintained in
[`docs/runbooks/postgres-disaster-recovery.md`](https://github.com/sgajbi/lotus-idea/blob/main/docs/runbooks/postgres-disaster-recovery.md).
