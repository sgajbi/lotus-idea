from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any

from app.domain import (
    CandidatePersistenceDecision,
    CandidatePersistenceResult,
    EvidenceFreshness,
    IdeaCandidate,
    OpportunityFamily,
    SourceRef,
    SourceSystem,
)
from app.domain.evidence_hashing import evidence_hash_for_source_refs
from app.domain.proof_evidence import parse_timezone_aware_datetime

SOURCE_RECEIPT_KEYS = frozenset(
    {
        "productId",
        "sourceSystem",
        "productVersion",
        "asOfDate",
        "generatedAtUtc",
        "contentHash",
        "dataQualityStatus",
        "freshness",
        "sourceReceiptSha256",
    }
)
PERSISTENCE_RECEIPT_KEYS = frozenset(
    {
        "decision",
        "candidateFamily",
        "candidateLifecycleStatus",
        "sourceEvidenceHash",
        "scopeFingerprint",
        "persistedAtUtc",
        "persistenceReceiptSha256",
    }
)


def build_runtime_receipts(
    *,
    candidate: IdeaCandidate | None,
    persistence: CandidatePersistenceResult | None,
    expected_family: OpportunityFamily,
    expected_portfolio_id: str,
    request_fingerprint: str,
    source_ref_is_authoritative: Callable[[SourceRef], bool],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if candidate is None or persistence is None or persistence.record is None:
        return None, None
    if persistence.decision not in {
        CandidatePersistenceDecision.ACCEPTED,
        CandidatePersistenceDecision.REPLAYED,
    }:
        return None, None
    record = persistence.record
    if record.candidate != candidate or candidate.family is not expected_family:
        return None, None
    source_refs = candidate.evidence_packet.source_refs
    if len(source_refs) != 1 or not source_ref_is_authoritative(source_refs[0]):
        return None, None
    if record.evidence_hash != evidence_hash_for_source_refs(source_refs):
        return None, None
    scope = candidate.access_scope
    if scope is None or scope.portfolio_id != expected_portfolio_id:
        return None, None

    source_receipt = _source_receipt(source_refs[0])
    persistence_receipt: dict[str, Any] = {
        "decision": persistence.decision.value,
        "candidateFamily": candidate.family.value,
        "candidateLifecycleStatus": candidate.lifecycle_status.value,
        "sourceEvidenceHash": record.evidence_hash,
        "scopeFingerprint": sha256_json(
            {
                "tenantId": scope.tenant_id,
                "bookId": scope.book_id,
                "portfolioId": scope.portfolio_id,
                "clientId": scope.client_id,
                "requestFingerprint": request_fingerprint,
            }
        ),
        "persistedAtUtc": _format_utc(record.persisted_at_utc),
    }
    persistence_receipt["persistenceReceiptSha256"] = sha256_json(persistence_receipt)
    return source_receipt, persistence_receipt


def source_receipt_is_valid(
    value: object,
    *,
    product_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != SOURCE_RECEIPT_KEYS:
        return False
    if (
        value.get("productId") != product_id
        or value.get("sourceSystem") != SourceSystem.LOTUS_RISK.value
        or value.get("asOfDate") != as_of_date.isoformat()
        or value.get("freshness") != EvidenceFreshness.CURRENT.value
    ):
        return False
    if not all(
        isinstance(value.get(key), str) and str(value[key]).strip()
        for key in ("productVersion", "contentHash", "dataQualityStatus")
    ):
        return False
    source_generated_at = parse_timezone_aware_datetime(value.get("generatedAtUtc"))
    if source_generated_at is None or source_generated_at > evaluated_at_utc:
        return False
    unsigned = {key: item for key, item in value.items() if key != "sourceReceiptSha256"}
    return value.get("sourceReceiptSha256") == sha256_json(unsigned)


def persistence_receipt_is_valid(
    value: object,
    *,
    family: OpportunityFamily,
    generated_at_utc: datetime,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != PERSISTENCE_RECEIPT_KEYS:
        return False
    if value.get("decision") not in {"accepted", "replayed"}:
        return False
    if value.get("candidateFamily") != family.value:
        return False
    if not all(is_sha256(value.get(key)) for key in ("sourceEvidenceHash", "scopeFingerprint")):
        return False
    persisted_at_utc = parse_timezone_aware_datetime(value.get("persistedAtUtc"))
    if persisted_at_utc is None or persisted_at_utc > generated_at_utc:
        return False
    unsigned = {key: item for key, item in value.items() if key != "persistenceReceiptSha256"}
    return value.get("persistenceReceiptSha256") == sha256_json(unsigned)


def source_evidence_hash(source_receipt: Mapping[str, Any]) -> str:
    return sha256_json(
        [
            {
                "content_hash": source_receipt["contentHash"],
                "data_quality_status": source_receipt["dataQualityStatus"],
                "freshness": source_receipt["freshness"],
                "product_id": source_receipt["productId"],
                "product_version": source_receipt["productVersion"],
                "source_system": source_receipt["sourceSystem"],
            }
        ]
    )


def sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _source_receipt(source_ref: SourceRef) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "productId": source_ref.product_id,
        "sourceSystem": source_ref.source_system.value,
        "productVersion": source_ref.product_version,
        "asOfDate": source_ref.as_of_date.isoformat(),
        "generatedAtUtc": _format_utc(source_ref.generated_at_utc),
        "contentHash": source_ref.content_hash,
        "dataQualityStatus": source_ref.data_quality_status,
        "freshness": source_ref.freshness.value,
    }
    receipt["sourceReceiptSha256"] = sha256_json(receipt)
    return receipt


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
