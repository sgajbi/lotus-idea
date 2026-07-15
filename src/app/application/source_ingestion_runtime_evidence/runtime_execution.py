from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from app.application.proof_provenance import (
    AGGREGATE_PROOF_PROVENANCE_KEY,
    aggregate_proof_artifact_is_current,
)
from app.application.source_ingestion import (
    HighCashSourceIngestionBatchResult,
    HighCashSourceIngestionDecision,
    HighCashSourceIngestionResult,
    SOURCE_INGESTION_ACTOR,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    SourceIngestionWorkerPlan,
)
from app.domain import CandidatePersistenceDecision, EvidenceFreshness, SourceRef, SourceSystem
from app.domain.evidence_hashing import evidence_hash_for_source_refs
from app.domain.proof_evidence import EvidenceClass, evidence_class_can_clear
from app.ports.core_sources import CORE_HIGH_CASH_SOURCE_PRODUCT_IDS


SOURCE_INGESTION_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_SOURCE_INGESTION_RUNTIME_EXECUTION"
SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.source-ingestion.runtime-execution.v2"
)
SOURCE_INGESTION_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_core_source_proof_missing",
)
SOURCE_INGESTION_REMAINING_BLOCKERS = (
    "scheduled_worker_deploy_proof_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "gateway_workbench_proof_missing",
    "production_certification_missing",
    "supported_feature_promotion_missing",
)
SOURCE_INGESTION_RUNTIME_EVIDENCE_REFS = (
    "scripts/source_ingestion/generate_runtime_execution.py",
    "scripts/source_ingestion/run_worker.py",
    "src/app/application/source_ingestion.py",
    "src/app/application/source_ingestion_runtime_evidence/runtime_execution.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "docs/operations/source-ingestion-run-once.md",
)

_DECISIONS = tuple(decision.value for decision in HighCashSourceIngestionDecision)
_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "evidenceClass",
        "proofFamily",
        "proofType",
        "sourceAuthority",
        "generatedAtUtc",
        "worker",
        "execution",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "evidenceRefs",
        "nonProofClaims",
    }
)
_WORKER_KEYS = frozenset({"schemaVersion", "mode", "evaluatedAtUtc", "actorRole", "workItemCount"})
_EXECUTION_KEYS = frozenset(
    {
        "status",
        "durableStorageBacked",
        "totalCount",
        "decisionCounts",
        "blockReasonCounts",
        "receiptCount",
        "receipts",
        "qualificationBlockers",
    }
)
_RECEIPT_KEYS = frozenset(
    {
        "itemIndex",
        "decision",
        "asOfDate",
        "scopeFingerprint",
        "sourceRefs",
        "sourceEvidenceHash",
        "persistedAtUtc",
        "persistenceReceiptSha256",
    }
)
_SOURCE_REF_KEYS = frozenset(
    {
        "productId",
        "sourceSystem",
        "productVersion",
        "asOfDate",
        "generatedAtUtc",
        "contentHash",
        "dataQualityStatus",
        "freshness",
    }
)
_NON_PROOF_CLAIM_KEYS = frozenset(
    {
        "scheduledWorkerDeployed",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "productionCertified",
        "supportedFeaturePromoted",
    }
)


def build_source_ingestion_runtime_execution(
    *,
    generated_at_utc: datetime,
    plan: SourceIngestionWorkerPlan,
    result: HighCashSourceIngestionBatchResult,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    receipts = tuple(
        receipt
        for index, item_result in enumerate(result.item_results)
        if (
            receipt := _runtime_receipt(
                index=index,
                plan=plan,
                item_result=item_result,
            )
        )
        is not None
    )
    decision_counts = result.decision_counts()
    qualification_blockers = _qualification_blockers(
        durable_storage_backed=durable_storage_backed,
        total_count=result.total_count,
        decision_counts=decision_counts,
        receipt_count=len(receipts),
    )
    return _payload(
        generated_at_utc=generated_at_utc,
        plan=plan,
        durable_storage_backed=durable_storage_backed,
        status="completed",
        total_count=result.total_count,
        decision_counts=decision_counts,
        block_reason_counts=result.source_failure_counts(),
        receipts=receipts,
        qualification_blockers=qualification_blockers,
    )


def build_blocked_source_ingestion_runtime_execution(
    *,
    generated_at_utc: datetime,
    plan: SourceIngestionWorkerPlan,
    error_code: str,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    safe_error_code = error_code.strip() or "core_source_unavailable"
    decision_counts = {decision: 0 for decision in _DECISIONS}
    decision_counts[HighCashSourceIngestionDecision.BLOCKED.value] = len(plan.command.work_items)
    blockers = [f"source_error_{safe_error_code}", "runtime_receipt_missing"]
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    return _payload(
        generated_at_utc=generated_at_utc,
        plan=plan,
        durable_storage_backed=durable_storage_backed,
        status="blocked",
        total_count=len(plan.command.work_items),
        decision_counts=decision_counts,
        block_reason_counts={safe_error_code: len(plan.command.work_items)},
        receipts=(),
        qualification_blockers=tuple(blockers),
    )


def source_ingestion_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    payload_keys = set(payload)
    if payload_keys not in (
        _TOP_LEVEL_KEYS,
        _TOP_LEVEL_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY},
    ):
        return False
    if AGGREGATE_PROOF_PROVENANCE_KEY in payload and not isinstance(
        payload[AGGREGATE_PROOF_PROVENANCE_KEY], Mapping
    ):
        return False
    if payload.get("schemaVersion") != SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        return False
    if payload.get("proofFamily") != "source_ingestion":
        return False
    if payload.get("proofType") != "lotus_core_high_cash_ingestion":
        return False
    if payload.get("sourceAuthority") != SourceSystem.LOTUS_CORE.value:
        return False
    generated_at_utc = _aware_datetime(payload.get("generatedAtUtc"))
    if generated_at_utc is None:
        return False
    worker = payload.get("worker")
    execution = payload.get("execution")
    non_proof_claims = payload.get("nonProofClaims")
    if not isinstance(worker, Mapping) or set(worker) != _WORKER_KEYS:
        return False
    if not isinstance(execution, Mapping) or set(execution) != _EXECUTION_KEYS:
        return False
    if not isinstance(non_proof_claims, Mapping) or set(non_proof_claims) != _NON_PROOF_CLAIM_KEYS:
        return False
    if any(value is not False for value in non_proof_claims.values()):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        SOURCE_INGESTION_REMAINING_BLOCKERS
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != SOURCE_INGESTION_RUNTIME_EVIDENCE_REFS:
        return False
    if not _worker_is_valid(worker, generated_at_utc=generated_at_utc):
        return False
    if not _execution_is_valid(execution, worker=worker, generated_at_utc=generated_at_utc):
        return False
    if tuple(payload.get("aggregateBlockersSatisfied") or ()) != (
        SOURCE_INGESTION_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    return evidence_class_can_clear(
        actual=EvidenceClass.RUNTIME_EXECUTION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )


def source_ingestion_runtime_execution_can_clear_aggregate_blockers(
    payload: Mapping[str, object] | None,
    *,
    evaluated_at_utc: datetime,
    proof_ref: str | None,
    repository_root: Path | None = None,
) -> bool:
    return bool(
        payload
        and source_ingestion_runtime_execution_is_valid(payload)
        and aggregate_proof_artifact_is_current(
            payload,
            evaluated_at_utc=evaluated_at_utc,
            proof_ref=proof_ref,
            repository_root=repository_root,
        )
    )


def _payload(
    *,
    generated_at_utc: datetime,
    plan: SourceIngestionWorkerPlan,
    durable_storage_backed: bool,
    status: str,
    total_count: int,
    decision_counts: Mapping[str, int],
    block_reason_counts: Mapping[str, int],
    receipts: Sequence[Mapping[str, Any]],
    qualification_blockers: Sequence[str],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    return {
        "schemaVersion": SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "source_ingestion",
        "proofType": "lotus_core_high_cash_ingestion",
        "sourceAuthority": SourceSystem.LOTUS_CORE.value,
        "generatedAtUtc": _format_utc(generated_at_utc),
        "worker": {
            "schemaVersion": plan.schema_version,
            "mode": "run_once",
            "evaluatedAtUtc": _format_utc(plan.command.evaluated_at_utc),
            "actorRole": plan.command.actor_subject,
            "workItemCount": len(plan.command.work_items),
        },
        "execution": {
            "status": status,
            "durableStorageBacked": durable_storage_backed,
            "totalCount": total_count,
            "decisionCounts": {
                decision: int(decision_counts.get(decision, 0)) for decision in _DECISIONS
            },
            "blockReasonCounts": {
                reason: count for reason, count in sorted(block_reason_counts.items()) if count > 0
            },
            "receiptCount": len(receipts),
            "receipts": list(receipts),
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(SOURCE_INGESTION_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(SOURCE_INGESTION_REMAINING_BLOCKERS),
        "evidenceRefs": list(SOURCE_INGESTION_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "scheduledWorkerDeployed": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
        },
    }


def _runtime_receipt(
    *,
    index: int,
    plan: SourceIngestionWorkerPlan,
    item_result: HighCashSourceIngestionResult,
) -> dict[str, Any] | None:
    if item_result.decision not in {
        HighCashSourceIngestionDecision.ACCEPTED,
        HighCashSourceIngestionDecision.REPLAYED,
    }:
        return None
    persistence = item_result.signal_result.persistence
    if persistence is None or persistence.record is None:
        return None
    expected_persistence_decision = CandidatePersistenceDecision(item_result.decision.value)
    if persistence.decision is not expected_persistence_decision:
        return None
    record = persistence.record
    candidate = record.candidate
    scope = candidate.access_scope
    work_item = plan.command.work_items[index]
    source_refs = tuple(candidate.evidence_packet.source_refs)
    if scope is None:
        return None
    if scope.tenant_id != plan.command.tenant_id or scope.portfolio_id != work_item.portfolio_id:
        return None
    if candidate.family.value != "high_cash":
        return None
    if evidence_hash_for_source_refs(source_refs) != record.evidence_hash:
        return None
    if not _source_refs_match_contract(source_refs, as_of_date=work_item.as_of_date):
        return None
    receipt = {
        "itemIndex": index,
        "decision": item_result.decision.value,
        "asOfDate": work_item.as_of_date.isoformat(),
        "scopeFingerprint": _scope_fingerprint(
            tenant_id=scope.tenant_id,
            book_id=scope.book_id,
            portfolio_id=scope.portfolio_id,
            client_id=scope.client_id,
            evaluated_at_utc=plan.command.evaluated_at_utc,
        ),
        "sourceRefs": [
            _source_ref_receipt(ref) for ref in sorted(source_refs, key=lambda ref: ref.product_id)
        ],
        "sourceEvidenceHash": record.evidence_hash,
        "persistedAtUtc": _format_utc(record.persisted_at_utc),
    }
    receipt["persistenceReceiptSha256"] = _sha256_json(receipt)
    return receipt


def _qualification_blockers(
    *,
    durable_storage_backed: bool,
    total_count: int,
    decision_counts: Mapping[str, int],
    receipt_count: int,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    if total_count < 1:
        blockers.append("no_ingestion_results")
    persisted_count = int(decision_counts.get("accepted", 0)) + int(
        decision_counts.get("replayed", 0)
    )
    if persisted_count != total_count:
        blockers.append("non_persisted_decisions_present")
    if receipt_count != persisted_count:
        blockers.append("runtime_receipt_missing")
    return tuple(blockers)


def _worker_is_valid(worker: Mapping[str, Any], *, generated_at_utc: datetime) -> bool:
    evaluated_at_utc = _aware_datetime(worker.get("evaluatedAtUtc"))
    return bool(
        worker.get("schemaVersion") == MANIFEST_SCHEMA_VERSION
        and worker.get("mode") == "run_once"
        and worker.get("actorRole") == SOURCE_INGESTION_ACTOR
        and _positive_int(worker.get("workItemCount"))
        and evaluated_at_utc is not None
        and evaluated_at_utc <= generated_at_utc
    )


def _execution_is_valid(
    execution: Mapping[str, Any],
    *,
    worker: Mapping[str, Any],
    generated_at_utc: datetime,
) -> bool:
    if execution.get("status") != "completed":
        return False
    if execution.get("durableStorageBacked") is not True:
        return False
    if tuple(execution.get("qualificationBlockers") or ()):
        return False
    decision_counts = execution.get("decisionCounts")
    receipts = execution.get("receipts")
    if not isinstance(decision_counts, Mapping) or set(decision_counts) != set(_DECISIONS):
        return False
    if any(_non_negative_int(decision_counts.get(decision)) is None for decision in _DECISIONS):
        return False
    total_count = _non_negative_int(execution.get("totalCount"))
    receipt_count = _non_negative_int(execution.get("receiptCount"))
    work_item_count = _positive_int(worker.get("workItemCount"))
    if total_count is None or receipt_count is None or work_item_count is None:
        return False
    if (
        total_count != work_item_count
        or sum(int(value) for value in decision_counts.values()) != total_count
    ):
        return False
    if any(
        int(decision_counts[decision])
        for decision in _DECISIONS
        if decision not in {"accepted", "replayed"}
    ):
        return False
    if (
        receipt_count != total_count
        or not isinstance(receipts, list)
        or len(receipts) != total_count
    ):
        return False
    if execution.get("blockReasonCounts") != {}:
        return False
    evaluated_at_utc = _aware_datetime(worker.get("evaluatedAtUtc"))
    if evaluated_at_utc is None:
        return False
    indexes: set[int] = set()
    for receipt in receipts:
        if not _receipt_is_valid(
            receipt,
            evaluated_at_utc=evaluated_at_utc,
            generated_at_utc=generated_at_utc,
        ):
            return False
        item_index = receipt["itemIndex"]
        if item_index in indexes or item_index >= total_count:
            return False
        indexes.add(item_index)
    return indexes == set(range(total_count))


def _receipt_is_valid(
    value: object,
    *,
    evaluated_at_utc: datetime,
    generated_at_utc: datetime,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
        return False
    if _non_negative_int(value.get("itemIndex")) is None:
        return False
    if value.get("decision") not in {"accepted", "replayed"}:
        return False
    try:
        as_of_date = date.fromisoformat(str(value.get("asOfDate")))
    except ValueError:
        return False
    if not _is_sha256(value.get("scopeFingerprint")):
        return False
    refs = value.get("sourceRefs")
    if not isinstance(refs, list) or len(refs) != len(CORE_HIGH_CASH_SOURCE_PRODUCT_IDS):
        return False
    if not _source_ref_receipts_are_valid(
        refs, as_of_date=as_of_date, evaluated_at_utc=evaluated_at_utc
    ):
        return False
    source_evidence_hash = value.get("sourceEvidenceHash")
    if source_evidence_hash != _source_ref_receipt_hash(refs):
        return False
    persisted_at_utc = _aware_datetime(value.get("persistedAtUtc"))
    if persisted_at_utc is None or persisted_at_utc > generated_at_utc:
        return False
    unsigned_receipt = {
        key: item for key, item in value.items() if key != "persistenceReceiptSha256"
    }
    return value.get("persistenceReceiptSha256") == _sha256_json(unsigned_receipt)


def _source_refs_match_contract(source_refs: tuple[SourceRef, ...], *, as_of_date: date) -> bool:
    return (
        tuple(sorted(ref.product_id for ref in source_refs))
        == tuple(sorted(CORE_HIGH_CASH_SOURCE_PRODUCT_IDS))
        and all(ref.source_system is SourceSystem.LOTUS_CORE for ref in source_refs)
        and all(ref.as_of_date == as_of_date for ref in source_refs)
        and all(ref.freshness is EvidenceFreshness.CURRENT for ref in source_refs)
    )


def _source_ref_receipt(source_ref: SourceRef) -> dict[str, Any]:
    return {
        "productId": source_ref.product_id,
        "sourceSystem": source_ref.source_system.value,
        "productVersion": source_ref.product_version,
        "asOfDate": source_ref.as_of_date.isoformat(),
        "generatedAtUtc": _format_utc(source_ref.generated_at_utc),
        "contentHash": source_ref.content_hash,
        "dataQualityStatus": source_ref.data_quality_status,
        "freshness": source_ref.freshness.value,
    }


def _source_ref_receipts_are_valid(
    refs: Sequence[object], *, as_of_date: date, evaluated_at_utc: datetime
) -> bool:
    product_ids: list[str] = []
    for ref in refs:
        if not isinstance(ref, Mapping) or set(ref) != _SOURCE_REF_KEYS:
            return False
        if ref.get("sourceSystem") != SourceSystem.LOTUS_CORE.value:
            return False
        if ref.get("asOfDate") != as_of_date.isoformat():
            return False
        if ref.get("freshness") != EvidenceFreshness.CURRENT.value:
            return False
        if not all(
            isinstance(ref.get(key), str) and str(ref[key]).strip()
            for key in ("productId", "productVersion", "contentHash", "dataQualityStatus")
        ):
            return False
        source_generated_at = _aware_datetime(ref.get("generatedAtUtc"))
        if source_generated_at is None or source_generated_at > evaluated_at_utc:
            return False
        product_ids.append(str(ref["productId"]))
    return tuple(product_ids) == tuple(sorted(CORE_HIGH_CASH_SOURCE_PRODUCT_IDS))


def _source_ref_receipt_hash(refs: Sequence[Mapping[str, Any]]) -> str:
    canonical_refs = [
        {
            "content_hash": ref["contentHash"],
            "data_quality_status": ref["dataQualityStatus"],
            "freshness": ref["freshness"],
            "product_id": ref["productId"],
            "product_version": ref["productVersion"],
            "source_system": ref["sourceSystem"],
        }
        for ref in refs
    ]
    return _sha256_json(canonical_refs)


def _scope_fingerprint(
    *,
    tenant_id: str,
    book_id: str,
    portfolio_id: str,
    client_id: str,
    evaluated_at_utc: datetime,
) -> str:
    return _sha256_json(
        {
            "tenantId": tenant_id,
            "bookId": book_id,
            "portfolioId": portfolio_id,
            "clientId": client_id,
            "evaluatedAtUtc": _format_utc(evaluated_at_utc),
        }
    )


def _sha256_json(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _positive_int(value: object) -> int | None:
    parsed = _non_negative_int(value)
    return parsed if parsed is not None and parsed > 0 else None


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _aware_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
