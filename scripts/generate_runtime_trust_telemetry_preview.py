from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from pathlib import Path
from typing import Any

from app.application.runtime_trust_telemetry import (
    RuntimeTrustTelemetryPreview,
    build_runtime_trust_telemetry_preview,
)
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = _parse_generated_at_utc(args.generated_at_utc)
        repository = get_idea_repository()
        snapshot = build_runtime_trust_telemetry_preview(
            repository=repository,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
            generated_at_utc=generated_at_utc,
        )
        rendered = json.dumps(runtime_trust_telemetry_preview_payload(snapshot), indent=2)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"{rendered}\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"runtime trust telemetry preview error: {exc}", file=sys.stderr)
        return 2


def runtime_trust_telemetry_preview_payload(
    snapshot: RuntimeTrustTelemetryPreview,
) -> dict[str, Any]:
    return {
        "repository": snapshot.repository,
        "productId": snapshot.product_id,
        "generatedAtUtc": _format_utc(snapshot.generated_at_utc),
        "candidateSnapshotCount": snapshot.candidate_snapshot_count,
        "currentSourceRefCount": snapshot.current_source_ref_count,
        "staleOrUnavailableSourceRefCount": snapshot.stale_or_unavailable_source_ref_count,
        "sourceAuthorityCounts": dict(snapshot.source_authority_counts),
        "freshnessCounts": dict(snapshot.freshness_counts),
        "supportabilityCounts": dict(snapshot.supportability_counts),
        "lifecycleCounts": dict(snapshot.lifecycle_counts),
        "reviewDecisionCount": snapshot.review_decision_count,
        "feedbackEventCount": snapshot.feedback_event_count,
        "conversionIntentCount": snapshot.conversion_intent_count,
        "conversionOutcomeCount": snapshot.conversion_outcome_count,
        "reportEvidencePackCount": snapshot.report_evidence_pack_count,
        "lineageMaterialized": snapshot.lineage_materialized,
        "runtimeTelemetryBacked": snapshot.runtime_telemetry_backed,
        "platformCertified": snapshot.platform_certified,
        "certificationStatus": snapshot.certification_status,
        "certificationReady": snapshot.certification_ready,
        "certificationBlockers": list(snapshot.certification_blockers),
        "supportedFeaturePromoted": snapshot.supported_feature_promoted,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe runtime trust telemetry preview for the proposed "
            "lotus-idea IdeaCandidate data product."
        )
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help="Timezone-aware generation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. Parent directories are created when needed.",
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


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
