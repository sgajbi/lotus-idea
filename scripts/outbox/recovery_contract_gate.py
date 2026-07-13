from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts.outbox._bootstrap import ROOT
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from _bootstrap import ROOT  # type: ignore[import-not-found,no-redef]

REQUIRED_FRAGMENTS = {
    "src/app/domain/outbox/recovery.py": (
        "MAX_OUTBOX_RECOVERY_ATTEMPTS = 1",
        "class OutboxRecoveryDecision",
        "unsupported_event_family",
        "recovery_attempt_limit_reached",
    ),
    "src/app/application/outbox/recovery.py": (
        "claim_dead_letter_for_recovery",
        "publish_outbox_event_safely",
        "max_retry_count=claim.event.retry_count + 1",
    ),
    "src/app/infrastructure/outbox/postgres_recovery.py": (
        "outbox-dead-letter-by-support-reference",
        "sha256(outbox_event_id::bytea)",
    ),
    "src/app/api/outbox/recovery.py": (
        "idea.outbox-recovery.read",
        "idea.outbox-recovery.redrive",
        "/api/v1/outbox-delivery/dead-letters",
        "{supportReference}/redrive",
    ),
    "migrations/004_outbox_dead_letter_recovery.sql": (
        "idempotency_fingerprint TEXT NOT NULL UNIQUE",
        "original_failure_reason TEXT NOT NULL",
        "original_first_failed_at_utc TIMESTAMPTZ NOT NULL",
        "original_last_failed_at_utc TIMESTAMPTZ NOT NULL",
        "CONSTRAINT uq_idea_outbox_recovery_event UNIQUE (outbox_event_id)",
        "idx_idea_outbox_dead_letter_support_reference",
    ),
}
FORBIDDEN_RESPONSE_FIELDS = (
    "aggregate_id",
    "candidate_id",
    "client_id",
    "idempotency_fingerprint",
    "payload",
    "portfolio_id",
)


def validate_outbox_recovery_contract(repository_root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative_path, fragments in REQUIRED_FRAGMENTS.items():
        path = repository_root / relative_path
        if not path.exists():
            errors.append(f"{relative_path}: required outbox recovery artifact is missing")
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{relative_path}: missing required fragment `{fragment}`")

    response_path = repository_root / "src/app/api/outbox/recovery_models.py"
    if not response_path.exists():
        errors.append("src/app/api/outbox/recovery_models.py: response contract is missing")
    else:
        response_content = response_path.read_text(encoding="utf-8")
        for field_name in FORBIDDEN_RESPONSE_FIELDS:
            if f"    {field_name}:" in response_content:
                errors.append(
                    "src/app/api/outbox/recovery_models.py: "
                    f"source-sensitive response field `{field_name}` is forbidden"
                )

    events_path = repository_root / "src/app/domain/outbox/events.py"
    events_content = events_path.read_text(encoding="utf-8")
    if "failure_reason=event.failure_reason" not in events_content:
        errors.append(
            f"{events_path.relative_to(repository_root)}: "
            "publication must preserve prior failure reason"
        )
    if "first_failed_at_utc=event.first_failed_at_utc" not in events_content:
        errors.append(
            f"{events_path.relative_to(repository_root)}: "
            "publication must preserve first failure time"
        )
    postgres_content = (
        repository_root / "src/app/infrastructure/outbox/postgres_recovery.py"
    ).read_text(encoding="utf-8")
    if "MAX_DEAD_LETTER_RECOVERY_LOOKUP_ROWS" in postgres_content:
        errors.append("PostgreSQL recovery lookup must not impose an arbitrary row limit")
    if "ORDER BY occurred_at_utc" in postgres_content:
        errors.append("PostgreSQL recovery lookup must resolve the exact support reference")
    return sorted(errors)


def main() -> int:
    errors = validate_outbox_recovery_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox recovery contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
