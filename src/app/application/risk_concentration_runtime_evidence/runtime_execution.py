from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any

from app.application.concentration_risk_signal import (
    ConcentrationRiskSignalPersistenceResult,
    EvaluateAndPersistConcentrationRiskFromRiskCommand,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    OpportunityFamily,
    SourceRef,
    SourceSystem,
)
from app.domain.evidence_hashing import evidence_hash_for_source_refs
from app.domain.proof_evidence import EvidenceClass, evidence_class_can_clear
from app.domain.proof_evidence import parse_timezone_aware_datetime

RISK_CONCENTRATION_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF"
RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.risk-concentration.runtime-execution.v2"
)
RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_risk_source_proof_missing",
)
RISK_CONCENTRATION_REMAINING_BLOCKERS = (
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_supported_feature_promotion_missing",
    "opportunity_archetype_client_publication_not_approved",
    "deployment_certification_missing",
    "production_certification_missing",
)
RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/risk_concentration_runtime_evidence/runtime_execution.py",
    "src/app/application/concentration_risk_signal.py",
    "src/app/ports/risk_sources.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "scripts/risk_concentration_runtime_evidence/generate_runtime_execution.py",
    "make risk-concentration-live-proof-contract-gate",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "evidenceClass",
        "proofFamily",
        "proofType",
        "sourceAuthority",
        "generatedAtUtc",
        "execution",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "evidenceRefs",
        "nonProofClaims",
    }
)
_EXECUTION_KEYS = frozenset(
    {
        "status",
        "durableStorageBacked",
        "evaluatedAtUtc",
        "asOfDate",
        "requestFingerprint",
        "sourceReceipt",
        "persistenceReceipt",
        "qualificationBlockers",
    }
)
_SOURCE_RECEIPT_KEYS = frozenset(
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
_PERSISTENCE_RECEIPT_KEYS = frozenset(
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
_NON_PROOF_CLAIM_KEYS = frozenset(
    {
        "officialRiskCalculationOwned",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "clientPublicationApproved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
    }
)
_PRODUCT_ID = "lotus-risk:ConcentrationRiskReport:v1"


def build_risk_concentration_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    result: ConcentrationRiskSignalPersistenceResult,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    source_receipt, persistence_receipt = _receipts(command=command, result=result)
    blockers = _qualification_blockers(
        result=result,
        durable_storage_backed=durable_storage_backed,
        source_receipt=source_receipt,
        persistence_receipt=persistence_receipt,
    )
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="completed",
        durable_storage_backed=durable_storage_backed,
        source_receipt=source_receipt,
        persistence_receipt=persistence_receipt,
        qualification_blockers=blockers,
    )


def build_blocked_risk_concentration_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    error_code: str,
    durable_storage_backed: bool,
) -> dict[str, Any]:
    _require_aware(generated_at_utc, "generated_at_utc")
    blockers = [f"source_error_{error_code.strip() or 'risk_source_unavailable'}"]
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    blockers.extend(("authoritative_source_receipt_missing", "persistence_receipt_missing"))
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="blocked",
        durable_storage_backed=durable_storage_backed,
        source_receipt=None,
        persistence_receipt=None,
        qualification_blockers=tuple(blockers),
    )


def risk_concentration_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_LEVEL_KEYS, _TOP_LEVEL_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if payload.get("schemaVersion") != RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        return False
    if payload.get("proofFamily") != "risk_concentration":
        return False
    if payload.get("proofType") != "lotus_risk_concentration_candidate_persistence":
        return False
    if payload.get("sourceAuthority") != SourceSystem.LOTUS_RISK.value:
        return False
    generated_at_utc = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if (
        generated_at_utc is None
        or not isinstance(execution, Mapping)
        or set(execution) != _EXECUTION_KEYS
    ):
        return False
    if not isinstance(claims, Mapping) or set(claims) != _NON_PROOF_CLAIM_KEYS:
        return False
    if claims.get("officialRiskCalculationOwned") != "lotus-risk":
        return False
    if any(
        value is not False for key, value in claims.items() if key != "officialRiskCalculationOwned"
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != RISK_CONCENTRATION_REMAINING_BLOCKERS
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS:
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if not _execution_is_valid(execution, generated_at_utc=generated_at_utc):
        return False
    return evidence_class_can_clear(
        actual=EvidenceClass.RUNTIME_EXECUTION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )


def _payload(
    *,
    generated_at_utc: datetime,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    status: str,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    request = command.evaluation
    return {
        "schemaVersion": RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "risk_concentration",
        "proofType": "lotus_risk_concentration_candidate_persistence",
        "sourceAuthority": SourceSystem.LOTUS_RISK.value,
        "generatedAtUtc": _format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "durableStorageBacked": durable_storage_backed,
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "asOfDate": request.as_of_date.isoformat(),
            "requestFingerprint": _request_fingerprint(command),
            "sourceReceipt": source_receipt,
            "persistenceReceipt": persistence_receipt,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(RISK_CONCENTRATION_REMAINING_BLOCKERS),
        "evidenceRefs": list(RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "officialRiskCalculationOwned": "lotus-risk",
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
        },
    }


def _receipts(
    *,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    result: ConcentrationRiskSignalPersistenceResult,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    persistence = result.persistence
    candidate = result.evaluation.candidate
    if persistence is None or persistence.record is None or candidate is None:
        return None, None
    if persistence.decision not in {
        CandidatePersistenceDecision.ACCEPTED,
        CandidatePersistenceDecision.REPLAYED,
    }:
        return None, None
    record = persistence.record
    if record.candidate != candidate or candidate.family is not OpportunityFamily.CONCENTRATION:
        return None, None
    source_refs = candidate.evidence_packet.source_refs
    if len(source_refs) != 1:
        return None, None
    source_ref = source_refs[0]
    if not _source_ref_matches_command(source_ref, command=command):
        return None, None
    if record.evidence_hash != evidence_hash_for_source_refs(source_refs):
        return None, None
    source_receipt = _source_receipt(source_ref)
    scope = candidate.access_scope
    if scope is None or scope.portfolio_id != command.evaluation.portfolio_id:
        return None, None
    persistence_receipt: dict[str, Any] = {
        "decision": persistence.decision.value,
        "candidateFamily": candidate.family.value,
        "candidateLifecycleStatus": candidate.lifecycle_status.value,
        "sourceEvidenceHash": record.evidence_hash,
        "scopeFingerprint": _sha256_json(
            {
                "tenantId": scope.tenant_id,
                "bookId": scope.book_id,
                "portfolioId": scope.portfolio_id,
                "clientId": scope.client_id,
                "requestFingerprint": _request_fingerprint(command),
            }
        ),
        "persistedAtUtc": _format_utc(record.persisted_at_utc),
    }
    persistence_receipt["persistenceReceiptSha256"] = _sha256_json(persistence_receipt)
    return source_receipt, persistence_receipt


def _qualification_blockers(
    *,
    result: ConcentrationRiskSignalPersistenceResult,
    durable_storage_backed: bool,
    source_receipt: Mapping[str, Any] | None,
    persistence_receipt: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    if source_receipt is None:
        blockers.append("authoritative_source_receipt_missing")
    if persistence_receipt is None:
        blockers.append("persistence_receipt_missing")
    if result.source_diagnostic_codes and any(
        code in {"risk_source_unavailable", "risk_source_entitlement_denied"}
        for code in result.source_diagnostic_codes
    ):
        blockers.append("risk_source_execution_blocked")
    return tuple(blockers)


def _execution_is_valid(execution: Mapping[str, Any], *, generated_at_utc: datetime) -> bool:
    if execution.get("status") != "completed" or execution.get("durableStorageBacked") is not True:
        return False
    if tuple(execution.get("qualificationBlockers") or ()):
        return False
    evaluated_at_utc = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if evaluated_at_utc is None or evaluated_at_utc > generated_at_utc:
        return False
    try:
        as_of_date = date.fromisoformat(str(execution.get("asOfDate")))
    except ValueError:
        return False
    if not _is_sha256(execution.get("requestFingerprint")):
        return False
    source = execution.get("sourceReceipt")
    persistence = execution.get("persistenceReceipt")
    if not _source_receipt_is_valid(
        source, as_of_date=as_of_date, evaluated_at_utc=evaluated_at_utc
    ):
        return False
    if not _persistence_receipt_is_valid(persistence, generated_at_utc=generated_at_utc):
        return False
    assert isinstance(source, Mapping) and isinstance(persistence, Mapping)
    return persistence.get("sourceEvidenceHash") == _source_evidence_hash(source)


def _source_ref_matches_command(
    source_ref: SourceRef,
    *,
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
) -> bool:
    return bool(
        source_ref.product_id == _PRODUCT_ID
        and source_ref.source_system is SourceSystem.LOTUS_RISK
        and source_ref.as_of_date == command.evaluation.as_of_date
        and source_ref.generated_at_utc <= command.evaluation.evaluated_at_utc
        and source_ref.freshness is EvidenceFreshness.CURRENT
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
    receipt["sourceReceiptSha256"] = _sha256_json(receipt)
    return receipt


def _source_receipt_is_valid(
    value: object,
    *,
    as_of_date: date,
    evaluated_at_utc: datetime,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != _SOURCE_RECEIPT_KEYS:
        return False
    if (
        value.get("productId") != _PRODUCT_ID
        or value.get("sourceSystem") != SourceSystem.LOTUS_RISK.value
    ):
        return False
    if (
        value.get("asOfDate") != as_of_date.isoformat()
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
    return value.get("sourceReceiptSha256") == _sha256_json(unsigned)


def _persistence_receipt_is_valid(value: object, *, generated_at_utc: datetime) -> bool:
    if not isinstance(value, Mapping) or set(value) != _PERSISTENCE_RECEIPT_KEYS:
        return False
    if value.get("decision") not in {"accepted", "replayed"}:
        return False
    if value.get("candidateFamily") != OpportunityFamily.CONCENTRATION.value:
        return False
    if not all(_is_sha256(value.get(key)) for key in ("sourceEvidenceHash", "scopeFingerprint")):
        return False
    persisted_at_utc = parse_timezone_aware_datetime(value.get("persistedAtUtc"))
    if persisted_at_utc is None or persisted_at_utc > generated_at_utc:
        return False
    unsigned = {key: item for key, item in value.items() if key != "persistenceReceiptSha256"}
    return value.get("persistenceReceiptSha256") == _sha256_json(unsigned)


def _source_evidence_hash(source_receipt: Mapping[str, Any]) -> str:
    return _sha256_json(
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


def _request_fingerprint(command: EvaluateAndPersistConcentrationRiskFromRiskCommand) -> str:
    request = command.evaluation
    return _sha256_json(
        {
            "portfolioId": request.portfolio_id,
            "asOfDate": request.as_of_date.isoformat(),
            "evaluatedAtUtc": _format_utc(request.evaluated_at_utc),
            "idempotencyKey": command.idempotency_key,
            "actorSubject": command.actor_subject,
        }
    )


def _sha256_json(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
