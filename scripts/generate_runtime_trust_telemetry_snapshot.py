from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from pathlib import Path
from typing import Any

from app.application.runtime_trust_telemetry import (
    RUNTIME_TELEMETRY_OUTPUT_PATH,
    build_runtime_trust_telemetry_snapshot,
)
from app.repository_state import get_idea_repository, idea_repository_durable_storage_backed


REQUIRED_CONTRACT_FIELDS = {
    "contract_id",
    "contract_version",
    "governed_by_rfcs",
    "emitted_at_utc",
    "product_id",
    "producer_repository",
    "product_name",
    "product_version",
    "source_repository",
    "freshness",
    "completeness_status",
    "reconciliation_status",
    "data_quality_status",
    "lineage",
    "blocking",
    "observed_trust_metadata",
    "evidence",
}
ALLOWED_COMPLETENESS_STATUSES = {
    "complete",
    "partial",
    "stale",
    "unreconciled",
    "break_open",
    "blocked",
    "unknown",
}
ALLOWED_RECONCILIATION_STATUSES = {
    "reconciled",
    "partial",
    "stale",
    "unreconciled",
    "break_open",
    "blocked",
    "not_applicable",
    "unknown",
}
ALLOWED_DATA_QUALITY_STATUSES = {
    "quality_passed",
    "quality_warning",
    "quality_failed",
    "quality_blocked",
    "quality_unknown",
}
ALLOWED_OBSERVED_METADATA = {
    "product_name",
    "product_version",
    "generated_at",
    "as_of_date",
    "reconciliation_status",
    "data_quality_status",
    "lineage_bundle_id",
    "source_batch_fingerprint",
    "correlation_id",
}
PROHIBITED_SOURCE_SAFE_FRAGMENTS = {
    "candidate_id",
    "candidateId",
    "portfolio_id",
    "portfolioId",
    "client_id",
    "clientId",
    "content_hash",
    "contentHash",
    "/source-owned/",
}


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_generated_at_utc(args.generated_at_utc)
        output_path = Path(args.output)
        repository = get_idea_repository()
        snapshot = build_runtime_trust_telemetry_snapshot(
            repository=repository,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
            generated_at_utc=generated_at_utc,
            source_artifact_uri=f"lotus-idea://{output_path.as_posix()}",
        ).to_dict()
        validation_errors = validate_runtime_trust_telemetry_snapshot_payload(snapshot)
        if validation_errors:
            print("\n".join(validation_errors), file=sys.stderr)
            return 1
        rendered = json.dumps(snapshot, indent=2)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
        print(f"Wrote runtime trust telemetry snapshot: {output_path.as_posix()}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"runtime trust telemetry snapshot error: {exc}", file=sys.stderr)
        return 2


def validate_runtime_trust_telemetry_snapshot_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_CONTRACT_FIELDS - set(payload))
    if missing:
        errors.append(f"runtime snapshot missing required fields: {', '.join(missing)}")
    if payload.get("contract_id") != "lotus-domain-product-trust-telemetry-snapshot":
        errors.append("runtime snapshot contract_id is invalid")
    if payload.get("product_id") != "lotus-idea:IdeaCandidate:v1":
        errors.append("runtime snapshot product_id must be lotus-idea:IdeaCandidate:v1")
    if payload.get("producer_repository") != "lotus-idea":
        errors.append("runtime snapshot producer_repository must be lotus-idea")
    if payload.get("source_repository") != "lotus-idea":
        errors.append("runtime snapshot source_repository must be lotus-idea")
    _validate_status_vocabulary(payload, errors)
    _validate_nested_contracts(payload, errors)
    _validate_source_safety(payload, errors)
    return errors


def _validate_status_vocabulary(payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("completeness_status") not in ALLOWED_COMPLETENESS_STATUSES:
        errors.append("runtime snapshot completeness_status is not in the mesh vocabulary")
    if payload.get("reconciliation_status") not in ALLOWED_RECONCILIATION_STATUSES:
        errors.append("runtime snapshot reconciliation_status is not in the mesh vocabulary")
    if payload.get("data_quality_status") not in ALLOWED_DATA_QUALITY_STATUSES:
        errors.append("runtime snapshot data_quality_status is not in the mesh vocabulary")


def _validate_nested_contracts(payload: dict[str, Any], errors: list[str]) -> None:
    freshness = payload.get("freshness")
    if not isinstance(freshness, dict):
        errors.append("runtime snapshot freshness must be an object")
    elif freshness.get("freshness_state") not in {"current", "stale", "unknown"}:
        errors.append("runtime snapshot freshness_state is invalid")

    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        errors.append("runtime snapshot lineage must be an object")
    elif not isinstance(lineage.get("lineage_materialized"), bool):
        errors.append("runtime snapshot lineage_materialized must be boolean")

    blocking = payload.get("blocking")
    if not isinstance(blocking, dict):
        errors.append("runtime snapshot blocking must be an object")
    elif blocking.get("blocked") is not True:
        errors.append("runtime snapshot must remain blocked before platform certification")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("runtime snapshot evidence must be an object")
    elif not evidence.get("validation_lanes"):
        errors.append("runtime snapshot evidence.validation_lanes must be non-empty")

    observed = payload.get("observed_trust_metadata")
    if not isinstance(observed, dict):
        errors.append("runtime snapshot observed_trust_metadata must be an object")
        return
    unknown_metadata = sorted(set(observed) - ALLOWED_OBSERVED_METADATA)
    if unknown_metadata:
        errors.append(
            "runtime snapshot observed_trust_metadata contains undeclared fields: "
            + ", ".join(unknown_metadata)
        )


def _validate_source_safety(payload: dict[str, Any], errors: list[str]) -> None:
    rendered = json.dumps(payload, sort_keys=True)
    for fragment in sorted(PROHIBITED_SOURCE_SAFE_FRAGMENTS):
        if fragment in rendered:
            errors.append(f"runtime snapshot contains source-unsafe fragment: {fragment}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe, contract-shaped runtime trust telemetry snapshot for "
            "the proposed lotus-idea IdeaCandidate data product."
        )
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--output",
        default=RUNTIME_TELEMETRY_OUTPUT_PATH,
        help="JSON output path. Parent directories are created when needed.",
    )
    return parser


def _parse_generated_at_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated-at-utc must be timezone-aware")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    sys.exit(main())
