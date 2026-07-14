from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.application.outbox.broker.source_contract_proof import (  # noqa: E402
    build_outbox_broker_source_contract_proof_payload,
)
from scripts.proof_generator_io import write_json_payload  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the source-safe outbox broker source-contract proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        payload = build_outbox_broker_source_contract_proof_payload(
            generated_at_utc=_aware_datetime(args.generated_at_utc),
            repository_root=ROOT,
        )
    except ValueError as exc:
        print(f"outbox broker source-contract proof error: {exc}", file=sys.stderr)
        return 2

    write_json_payload(payload, output=args.output)
    return 0 if payload["outboxBrokerSourceContractValid"] else 1


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--generated-at-utc must be timezone-aware")
    return parsed


if __name__ == "__main__":
    sys.exit(main())
