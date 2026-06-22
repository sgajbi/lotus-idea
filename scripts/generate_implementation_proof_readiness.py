from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.implementation_proof_readiness import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
    build_implementation_proof_readiness_snapshot,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        evaluated_at_utc = _parse_evaluated_at_utc(args.evaluated_at_utc)
        with _temporary_environment(_readiness_environment_overrides(args)):
            repository = get_idea_repository()
            durable_repository_proof_path = _resolve_optional_path(args.durable_repository_proof)
            durable_repository_proof = _read_optional_json_object(durable_repository_proof_path)
            snapshot = build_implementation_proof_readiness_snapshot(
                evaluated_at_utc=evaluated_at_utc,
                repository=repository,
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
                durable_repository_proof=durable_repository_proof,
                durable_repository_proof_ref=_source_safe_artifact_ref(
                    durable_repository_proof_path
                ),
            )
        payload = implementation_proof_readiness_payload(snapshot)
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"{rendered}\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"implementation proof readiness error: {exc}", file=sys.stderr)
        return 2


def implementation_proof_readiness_payload(
    snapshot: ImplementationProofReadinessSnapshot,
) -> dict[str, Any]:
    return {
        "repository": snapshot.repository,
        "evaluatedAtUtc": _format_utc(snapshot.evaluated_at_utc),
        "readinessStatus": snapshot.readiness_status,
        "supportabilityStatus": snapshot.supportability_status,
        "certificationReady": snapshot.certification_ready,
        "capabilityCount": snapshot.capability_count,
        "certificationReadyCapabilityCount": snapshot.certification_ready_capability_count,
        "blockedCapabilityCount": snapshot.blocked_capability_count,
        "supportedFeatureCount": snapshot.supported_feature_count,
        "supportedFeaturesPromoted": snapshot.supported_features_promoted,
        "overallBlockers": list(snapshot.overall_blockers),
        "sourceOfTruth": dict(snapshot.source_of_truth),
        "capabilities": [_capability_payload(capability) for capability in snapshot.capabilities],
        "supportedFeaturePromoted": False,
    }


def _capability_payload(
    capability: ImplementationProofCapabilityReadiness,
) -> dict[str, Any]:
    return {
        "capabilityId": capability.capability_id,
        "name": capability.name,
        "readinessStatus": capability.readiness_status,
        "supportabilityStatus": capability.supportability_status,
        "certificationReady": capability.certification_ready,
        "evidenceRefs": list(capability.evidence_refs),
        "blockers": list(capability.blockers),
        "supportedFeaturePromoted": capability.supported_feature_promoted,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the source-safe lotus-idea RFC-0002 implementation proof readiness snapshot."
    )
    parser.add_argument(
        "--evaluated-at-utc",
        required=True,
        help="Timezone-aware evaluation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. Parent directories are created when needed.",
    )
    parser.add_argument(
        "--source-ingestion-manifest",
        help=(
            f"Optional manifest path to expose to readiness as {MANIFEST_ENV}. "
            "Useful for deterministic CI proof snapshots."
        ),
    )
    parser.add_argument(
        "--core-base-url",
        help=f"Optional Core base URL to expose to readiness as {CORE_BASE_URL_ENV}.",
    )
    parser.add_argument(
        "--source-ingestion-live-proof",
        help=f"Optional live Core proof artifact path to expose as {LIVE_PROOF_ENV}.",
    )
    parser.add_argument(
        "--source-ingestion-scheduled-worker-proof",
        help=(
            "Optional scheduled source-ingestion worker proof artifact path to expose as "
            f"{SCHEDULED_WORKER_PROOF_ENV}."
        ),
    )
    parser.add_argument(
        "--durable-repository-proof",
        default=os.getenv(DURABLE_REPOSITORY_PROOF_ENV),
        help=(
            "Optional durable PostgreSQL repository proof artifact path. "
            f"Defaults to {DURABLE_REPOSITORY_PROOF_ENV} when set."
        ),
    )
    return parser


def _parse_evaluated_at_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evaluated-at-utc must be timezone-aware")
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _readiness_environment_overrides(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        MANIFEST_ENV: args.source_ingestion_manifest,
        CORE_BASE_URL_ENV: args.core_base_url,
        LIVE_PROOF_ENV: args.source_ingestion_live_proof,
        SCHEDULED_WORKER_PROOF_ENV: args.source_ingestion_scheduled_worker_proof,
    }


def _resolve_optional_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return Path(path_value)


def _read_optional_json_object(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("durable repository proof must be a JSON object")
    return payload


def _source_safe_artifact_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return "durable repository proof artifact"


@contextmanager
def _temporary_environment(overrides: dict[str, str | None]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is not None:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    sys.exit(main())
