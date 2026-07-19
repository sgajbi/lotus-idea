# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.runtime_trust_telemetry import (  # noqa: E402
    RuntimeTrustTelemetryPreview,
    build_runtime_trust_telemetry_preview,
)
from app.runtime.repository_state import (  # noqa: E402
    get_idea_repository,
    idea_repository_durable_storage_backed,
)

from scripts.proof_generator_io import parse_generated_at_utc  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
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
        "dataLifecycleStateCounts": dict(snapshot.data_lifecycle_state_counts),
        "retentionExpiredCount": snapshot.retention_expired_count,
        "lifecycleControlMissingCount": snapshot.lifecycle_control_missing_count,
        "reviewDecisionCount": snapshot.review_decision_count,
        "feedbackEventCount": snapshot.feedback_event_count,
        "conversionIntentCount": snapshot.conversion_intent_count,
        "conversionOutcomeCount": snapshot.conversion_outcome_count,
        "reportEvidencePackCount": snapshot.report_evidence_pack_count,
        "downstreamSubmissionCount": snapshot.downstream_submission_count,
        "downstreamReconciliationRequiredCount": (
            snapshot.downstream_reconciliation_required_count
        ),
        "lineageMaterialized": snapshot.lineage_materialized,
        "runtimeTelemetryBacked": snapshot.runtime_telemetry_backed,
        "platformCertified": snapshot.platform_certified,
        "certificationStatus": snapshot.certification_status,
        "certificationReady": snapshot.certification_ready,
        "certificationBlockers": list(snapshot.certification_blockers),
        "blockerIssueRefs": dict(snapshot.blocker_issue_refs),
        "productCoverage": [
            {
                "productId": posture.product_id,
                "productName": posture.product_name,
                "productVersion": posture.product_version,
                "lifecycleStatus": posture.lifecycle_status,
                "freshnessClass": posture.freshness_class,
                "coverageStatus": posture.coverage_status,
                "runtimeBacked": posture.runtime_backed,
                "observedRecordCount": posture.observed_record_count,
                "currentSourceRefCount": posture.current_source_ref_count,
                "staleOrUnavailableSourceRefCount": (posture.stale_or_unavailable_source_ref_count),
                "freshnessState": posture.freshness_state,
                "completenessStatus": posture.completeness_status,
                "reconciliationStatus": posture.reconciliation_status,
                "dataQualityStatus": posture.data_quality_status,
                "lineageMaterialized": posture.lineage_materialized,
                "sourceBatchEvidenceAvailable": posture.source_batch_evidence_available,
                "consumerExposureStatus": posture.consumer_exposure_status,
                "certificationBlockers": list(posture.certification_blockers),
                "blockerIssueRefs": dict(posture.blocker_issue_refs),
            }
            for posture in snapshot.product_postures
        ],
        "supportedFeaturePromoted": snapshot.supported_feature_promoted,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe runtime trust telemetry preview for the proposed "
            "lotus-idea producer product catalog."
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


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
