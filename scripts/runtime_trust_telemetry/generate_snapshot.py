# ruff: noqa: E402
from __future__ import annotations

import argparse
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
    RUNTIME_TELEMETRY_OUTPUT_PATH,
    build_runtime_trust_telemetry_snapshot,
    build_source_safe_runtime_trust_telemetry_repository,
    required_runtime_trust_telemetry_blocker_issue_refs,
)
from app.runtime.repository_state import (  # noqa: E402
    get_idea_repository,
    idea_repository_durable_storage_backed,
)

from scripts.proof_generator_io import parse_generated_at_utc  # noqa: E402


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
    "data_lifecycle",
    "downstream_submission_posture",
    "blocking",
    "product_coverage",
    "observed_trust_metadata",
    "evidence",
}
REQUIRED_PRODUCT_COVERAGE_FIELDS = {
    "product_id",
    "product_name",
    "product_version",
    "lifecycle_status",
    "freshness_class",
    "coverage_status",
    "runtime_backed",
    "observed_record_count",
    "current_source_ref_count",
    "stale_or_unavailable_source_ref_count",
    "freshness_state",
    "completeness_status",
    "reconciliation_status",
    "data_quality_status",
    "lineage_materialized",
    "source_batch_evidence_available",
    "consumer_exposure_status",
    "certification_blockers",
    "blocker_issue_refs",
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
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
        output_path = Path(args.output)
        repository = (
            build_source_safe_runtime_trust_telemetry_repository(generated_at_utc=generated_at_utc)
            if args.source_safe_local_exercise
            else get_idea_repository()
        )
        durable_storage_backed = (
            False
            if args.source_safe_local_exercise
            else idea_repository_durable_storage_backed(repository)
        )
        snapshot = build_runtime_trust_telemetry_snapshot(
            repository=repository,
            durable_storage_backed=durable_storage_backed,
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
    _validate_product_coverage(payload, errors)
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
    elif "blocker_issue_refs" not in blocking:
        errors.append("runtime snapshot blocking.blocker_issue_refs must be present")
    else:
        _validate_blocker_issue_refs(
            blockers=_blocking_certification_blockers(blocking),
            issue_refs=blocking.get("blocker_issue_refs"),
            context="runtime snapshot blocking.blocker_issue_refs",
            errors=errors,
        )

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
    _validate_downstream_submission_posture(payload, errors)


def _validate_downstream_submission_posture(
    payload: dict[str, Any],
    errors: list[str],
) -> None:
    posture = payload.get("downstream_submission_posture")
    if not isinstance(posture, dict):
        errors.append("runtime snapshot downstream_submission_posture must be an object")
        return
    expected_fields = {
        "submission_count",
        "reconciliation_required_count",
        "posture_scope",
        "certification_status",
        "supported_feature_promoted",
    }
    unknown_or_missing = sorted(set(posture) ^ expected_fields)
    if unknown_or_missing:
        errors.append("runtime snapshot downstream_submission_posture fields are invalid")
    for count_field in ("submission_count", "reconciliation_required_count"):
        if not isinstance(posture.get(count_field), int) or posture[count_field] < 0:
            errors.append(f"runtime snapshot downstream_submission_posture {count_field} invalid")
    if posture.get("posture_scope") != "local_idea_submission_state":
        errors.append("runtime snapshot downstream submission posture scope is invalid")
    if posture.get("certification_status") != "not_certified":
        errors.append("runtime snapshot downstream submission posture must remain not_certified")
    if posture.get("supported_feature_promoted") is not False:
        errors.append("runtime snapshot downstream submission posture must not promote support")


def _validate_product_coverage(payload: dict[str, Any], errors: list[str]) -> None:
    coverage = payload.get("product_coverage")
    if not isinstance(coverage, list) or not coverage:
        errors.append("runtime snapshot product_coverage must be a non-empty list")
        return
    product_ids: set[str] = set()
    for index, item in enumerate(coverage):
        if not isinstance(item, dict):
            errors.append(f"runtime snapshot product_coverage[{index}] must be an object")
            continue
        missing = sorted(REQUIRED_PRODUCT_COVERAGE_FIELDS - set(item))
        if missing:
            errors.append(
                f"runtime snapshot product_coverage[{index}] missing fields: " + ", ".join(missing)
            )
        product_id = item.get("product_id")
        if not isinstance(product_id, str) or not product_id.startswith("lotus-idea:"):
            errors.append(f"runtime snapshot product_coverage[{index}] product_id is invalid")
        else:
            product_ids.add(product_id)
        if item.get("coverage_status") not in {
            "runtime_backed",
            "runtime_backed_no_records",
            "blocked_not_runtime_backed",
        }:
            errors.append(f"runtime snapshot product_coverage[{index}] coverage_status is invalid")
        if not isinstance(item.get("certification_blockers"), list):
            errors.append(
                f"runtime snapshot product_coverage[{index}] certification_blockers must be a list"
            )
            blockers: list[str] = []
        else:
            blockers = item["certification_blockers"]
        _validate_blocker_issue_refs(
            blockers=blockers,
            issue_refs=item.get("blocker_issue_refs"),
            context=f"runtime snapshot product_coverage[{index}].blocker_issue_refs",
            errors=errors,
        )
    if "lotus-idea:IdeaTrustTelemetry:v1" not in product_ids:
        errors.append("runtime snapshot product_coverage must include IdeaTrustTelemetry:v1")


def _blocking_certification_blockers(blocking: dict[str, Any]) -> list[str]:
    blocked_reason = blocking.get("blocked_reason")
    if not isinstance(blocked_reason, str) or "blockers: " not in blocked_reason:
        return []
    serialized = blocked_reason.split("blockers: ", maxsplit=1)[1].rstrip(".")
    return [blocker.strip() for blocker in serialized.split(",") if blocker.strip()]


def _validate_blocker_issue_refs(
    *,
    blockers: list[str],
    issue_refs: Any,
    context: str,
    errors: list[str],
) -> None:
    if not isinstance(issue_refs, dict):
        errors.append(f"{context} must be an object")
        return
    blocker_set = set(blockers)
    missing_mappings = sorted(blocker_set - set(issue_refs))
    if missing_mappings:
        errors.append(f"{context} missing blockers: {', '.join(missing_mappings)}")
    stale_mappings = sorted(set(issue_refs) - blocker_set)
    if stale_mappings:
        errors.append(f"{context} contains non-blockers: {', '.join(stale_mappings)}")

    required_refs = required_runtime_trust_telemetry_blocker_issue_refs()
    for blocker in sorted(blocker_set):
        if blocker not in required_refs:
            errors.append(f"{context}.{blocker} is not in the canonical blocker issue-ref map")
        refs = issue_refs.get(blocker)
        if not isinstance(refs, list | tuple) or not refs:
            errors.append(f"{context}.{blocker} must be a non-empty issue-ref list")
            continue
        expected_refs = set(required_refs.get(blocker, ()))
        missing_required_refs = sorted(expected_refs - set(refs))
        if missing_required_refs:
            errors.append(
                f"{context}.{blocker} missing required issue refs: "
                + ", ".join(missing_required_refs)
            )
        invalid_refs = sorted(ref for ref in refs if not _is_issue_ref(ref))
        if invalid_refs:
            errors.append(
                f"{context}.{blocker} must use sgajbi/<repo>#<number> refs: "
                + ", ".join(invalid_refs)
            )


def _is_issue_ref(ref: Any) -> bool:
    if not isinstance(ref, str) or not ref.startswith("sgajbi/"):
        return False
    if "#" not in ref:
        return False
    _, number = ref.rsplit("#", maxsplit=1)
    return number.isdecimal()


def _validate_source_safety(payload: dict[str, Any], errors: list[str]) -> None:
    rendered = json.dumps(payload, sort_keys=True)
    for fragment in sorted(PROHIBITED_SOURCE_SAFE_FRAGMENTS):
        if fragment in rendered:
            errors.append(f"runtime snapshot contains source-unsafe fragment: {fragment}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a source-safe, contract-shaped runtime trust telemetry snapshot for "
            "the proposed lotus-idea producer product catalog."
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
    parser.add_argument(
        "--source-safe-local-exercise",
        action="store_true",
        help=(
            "Generate the snapshot from a deterministic local/test source-safe candidate exercise. "
            "This proves the Idea-owned telemetry path but remains non-durable and not certified."
        ),
    )
    return parser


if __name__ == "__main__":
    sys.exit(main())
