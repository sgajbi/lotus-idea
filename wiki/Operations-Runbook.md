# Operations Runbook

Current posture: scaffold operations only.

Initial commands:

```powershell
make install
make check
make ci
uvicorn app.main:app --reload --port 8330
```

RFC-0002 will add support runbooks for:

1. upstream source unavailable,
2. stale evidence,
3. duplicate idea burst,
4. scoring policy disabled,
5. review queue backlog,
6. entitlement denial,
7. idempotency conflict,
8. AI unavailable,
9. unsupported AI output,
10. downstream conversion failure,
11. report/archive handoff failure,
12. replay hash mismatch.
