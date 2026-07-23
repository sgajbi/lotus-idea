# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.broker.runtime_execution import (  # noqa: E402
    build_outbox_broker_runtime_execution_payload,
    outbox_broker_runtime_execution_is_valid,
)
from app.application.outbox.readiness import OUTBOX_BROKER_URL_ENV  # noqa: E402
from app.domain import EventLineageContext, EventLineageOrigin, build_candidate_outbox_event  # noqa: E402
from app.runtime.outbox.publisher_state import (  # noqa: E402
    build_outbox_publisher_from_environment,
)
from scripts.proof_generator_io import write_json_payload  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a runtime outbox broker publication proof from configured broker."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    generated_at_utc = _aware_datetime(args.generated_at_utc)
    publisher = build_outbox_publisher_from_environment()
    if isinstance(publisher, str):
        print(f"outbox broker runtime execution proof error: {publisher}", file=sys.stderr)
        return 2
    try:
        event = build_candidate_outbox_event(
            event_type="idea.candidate.persisted.v1",
            aggregate_id="outbox-certification-canary",
            occurred_at_utc=generated_at_utc,
            payload={"candidate_family": "certification_canary"},
            idempotency_key="outbox-certification-canary",
            lineage=EventLineageContext(
                correlation_id="outbox-certification-correlation",
                trace_id="outbox-certification-trace",
                causation_id=None,
                origin=EventLineageOrigin.SYSTEM_GENERATED,
            ),
        )
        outcome = publisher.publish(event)
    finally:
        close = getattr(publisher, "close", None)
        if callable(close):
            close()

    payload = build_outbox_broker_runtime_execution_payload(
        generated_at_utc=generated_at_utc,
        broker_configured=True,
        publication_receipt={
            "outcomeAccepted": outcome.accepted,
            "failureReasonCode": outcome.failure_reason,
            "sourceSafeEnvelopePublished": True,
            "supportabilityStatusPublished": "not_certified",
        },
    )
    write_json_payload(payload, output=args.output)
    if not outbox_broker_runtime_execution_is_valid(payload):
        print(
            f"outbox broker runtime execution proof invalid for {OUTBOX_BROKER_URL_ENV}",
            file=sys.stderr,
        )
        return 1
    return 0


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
