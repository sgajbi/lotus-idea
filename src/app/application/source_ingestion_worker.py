from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.application.source_ingestion import (
    DEFAULT_SOURCE_INGESTION_BATCH_LIMIT,
    HighCashSourceIngestionDecision,
    HighCashSourceIngestionBatchResult,
    HighCashSourceIngestionResult,
    HighCashSourceIngestionWorkItem,
    RunHighCashSourceIngestionBatchCommand,
    SOURCE_INGESTION_ACTOR,
    SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING,
    SourceIngestionBatchLimitExceeded,
)


MANIFEST_SCHEMA_VERSION = "lotus-idea.source-ingestion.high-cash.run-once.v1"

_MANIFEST_KEYS = {
    "schemaVersion",
    "evaluatedAtUtc",
    "actorSubject",
    "maxItems",
    "correlationId",
    "traceId",
    "workItems",
}
_WORK_ITEM_KEYS = {
    "portfolioId",
    "asOfDate",
    "idempotencyKey",
    "duplicateOfCandidateId",
}


@dataclass(frozen=True)
class SourceIngestionWorkerPlan:
    command: RunHighCashSourceIngestionBatchCommand
    schema_version: str = MANIFEST_SCHEMA_VERSION

    def check_summary(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "mode": "check_only",
            "sourceAuthority": "lotus-core",
            "evaluatedAtUtc": self.command.evaluated_at_utc.isoformat(),
            "actorSubject": self.command.actor_subject,
            "maxItems": self.command.max_items,
            "workItemCount": len(self.command.work_items),
            "workItems": [
                {
                    "itemIndex": index,
                    "asOfDate": item.as_of_date.isoformat(),
                    "hasExplicitIdempotencyKey": item.idempotency_key is not None,
                    "hasDuplicateOfCandidateId": item.duplicate_of_candidate_id is not None,
                }
                for index, item in enumerate(self.command.work_items)
            ],
        }


def source_ingestion_worker_plan_from_manifest(
    manifest: Mapping[str, Any],
) -> SourceIngestionWorkerPlan:
    _reject_unknown_keys(manifest, allowed_keys=_MANIFEST_KEYS, context="manifest")
    schema_version = _require_text(manifest.get("schemaVersion"), "schemaVersion")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {MANIFEST_SCHEMA_VERSION}")

    work_items = _work_items_from_manifest(manifest.get("workItems"))
    command = RunHighCashSourceIngestionBatchCommand(
        work_items=work_items,
        evaluated_at_utc=_aware_datetime(manifest.get("evaluatedAtUtc"), "evaluatedAtUtc"),
        actor_subject=_optional_text(manifest.get("actorSubject")) or SOURCE_INGESTION_ACTOR,
        max_items=_positive_int(
            manifest.get("maxItems"),
            "maxItems",
            default=DEFAULT_SOURCE_INGESTION_BATCH_LIMIT,
        ),
        correlation_id=_optional_text(manifest.get("correlationId")),
        trace_id=_optional_text(manifest.get("traceId")),
    )
    return SourceIngestionWorkerPlan(command=command, schema_version=schema_version)


def summarize_source_ingestion_worker_run(
    *,
    plan: SourceIngestionWorkerPlan,
    result: HighCashSourceIngestionBatchResult,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    return {
        "schemaVersion": plan.schema_version,
        "mode": "run_once",
        "sourceAuthority": result.source_authority,
        "evaluatedAtUtc": plan.command.evaluated_at_utc.isoformat(),
        "actorSubject": plan.command.actor_subject,
        "durableStorageBacked": durable_storage_backed,
        "supportedFeaturePromoted": False,
        "totalCount": result.total_count,
        "decisionCounts": result.decision_counts(),
        "blockReasonCounts": _block_reason_counts(result),
        "items": [
            {
                "decision": item_result.decision.value,
                "hasIdempotencyKey": bool(item_result.idempotency_key),
                "candidateId": _candidate_id(item_result),
            }
            for item_result in result.item_results
        ],
    }


def summarize_source_ingestion_worker_failure(
    *,
    plan: SourceIngestionWorkerPlan,
    error_code: str,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    return {
        "schemaVersion": plan.schema_version,
        "mode": "run_once",
        "status": "blocked",
        "sourceAuthority": "lotus-core",
        "evaluatedAtUtc": plan.command.evaluated_at_utc.isoformat(),
        "actorSubject": plan.command.actor_subject,
        "durableStorageBacked": durable_storage_backed,
        "supportedFeaturePromoted": False,
        "workItemCount": len(plan.command.work_items),
        "decisionCounts": _empty_decision_counts(),
        "blockReasonCounts": {_safe_error_code(error_code): len(plan.command.work_items)},
        "errorCode": _safe_error_code(error_code),
    }


def _work_items_from_manifest(
    raw_work_items: object,
) -> tuple[HighCashSourceIngestionWorkItem, ...]:
    if not isinstance(raw_work_items, Sequence) or isinstance(raw_work_items, (str, bytes)):
        raise ValueError("workItems must be a non-empty list")
    if len(raw_work_items) > SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING:
        raise SourceIngestionBatchLimitExceeded(
            "workItems exceeds source_ingestion_run_once_batch_ceiling"
        )
    parsed_items: list[HighCashSourceIngestionWorkItem] = []
    for index, raw_item in enumerate(raw_work_items):
        if not isinstance(raw_item, Mapping):
            raise ValueError(f"workItems[{index}] must be an object")
        _reject_unknown_keys(raw_item, allowed_keys=_WORK_ITEM_KEYS, context=f"workItems[{index}]")
        parsed_items.append(
            HighCashSourceIngestionWorkItem(
                portfolio_id=_require_text(
                    raw_item.get("portfolioId"), f"workItems[{index}].portfolioId"
                ),
                as_of_date=_date(raw_item.get("asOfDate"), f"workItems[{index}].asOfDate"),
                idempotency_key=_optional_text(raw_item.get("idempotencyKey")),
                duplicate_of_candidate_id=_optional_text(raw_item.get("duplicateOfCandidateId")),
            )
        )
    return tuple(parsed_items)


def _empty_decision_counts() -> dict[str, int]:
    return {decision.value: 0 for decision in HighCashSourceIngestionDecision}


def _block_reason_counts(result: HighCashSourceIngestionBatchResult) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item_result in result.item_results:
        if item_result.decision is not HighCashSourceIngestionDecision.BLOCKED:
            continue
        reason_codes = tuple(item_result.signal_result.source_diagnostic_codes) or tuple(
            reason.value for reason in item_result.signal_result.evaluation.unsupported_reasons
        )
        if not reason_codes:
            reason_codes = ("source_evidence_blocked",)
        counts.update(reason_codes)
    return {reason: counts[reason] for reason in sorted(counts)}


def _safe_error_code(error_code: str) -> str:
    stripped = error_code.strip()
    if not stripped:
        return "core_source_unavailable"
    return stripped


def _candidate_id(item_result: HighCashSourceIngestionResult) -> str | None:
    persistence = item_result.signal_result.persistence
    if persistence is None or persistence.record is None:
        return None
    return persistence.record.candidate.candidate_id


def _reject_unknown_keys(
    values: Mapping[str, Any],
    *,
    allowed_keys: set[str],
    context: str,
) -> None:
    unknown_keys = sorted(set(values) - allowed_keys)
    if unknown_keys:
        joined = ", ".join(unknown_keys)
        raise ValueError(f"{context} contains unsupported keys: {joined}")


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("optional text fields must be non-empty strings when supplied")
    return value.strip()


def _aware_datetime(value: object, field_name: str) -> datetime:
    text = _require_text(value, field_name)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _date(value: object, field_name: str) -> date:
    return date.fromisoformat(_require_text(value, field_name))


def _positive_int(value: object, field_name: str, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value
