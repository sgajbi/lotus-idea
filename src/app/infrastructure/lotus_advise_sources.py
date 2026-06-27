from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


PRODUCT_VERSION = "v1"
POLICY_EVALUATION_PRODUCT_ID = "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE = "/advisory/policy-evaluations/{evaluation_id}/workflow"


@dataclass(frozen=True)
class _PolicyEvaluationPosture:
    evaluation_status: str | None
    open_requirement_count: int
    blocked_requirement_count: int
    sign_off_status: str | None
    sign_off_blocker_count: int
    client_ready_publication: str | None


class LotusAdvisePolicyEvaluationSourceAdapter:
    def __init__(self, advise_client: DownstreamJsonClient) -> None:
        self._advise_client = advise_client

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        route = _workflow_route(request.evaluation_id)
        try:
            payload = self._advise_client.get_json(
                route,
                correlation_id=request.correlation_id,
                trace_id=request.trace_id,
            )
        except DownstreamServiceError as exc:
            if exc.status_code in {401, 403}:
                raise AdviseSourceEntitlementDenied from exc
            raise AdviseSourceUnavailable(code=exc.code) from exc

        posture = _policy_evaluation_posture(payload)
        return AdvisePolicyEvaluationEvidence(
            evaluation_status=posture.evaluation_status,
            open_requirement_count=posture.open_requirement_count,
            blocked_requirement_count=posture.blocked_requirement_count,
            sign_off_status=posture.sign_off_status,
            sign_off_blocker_count=posture.sign_off_blocker_count,
            client_ready_publication=posture.client_ready_publication,
            policy_ref=_source_ref(payload, request=request, route=route),
            advise_diagnostic=_diagnostic(posture),
        )


def _workflow_route(evaluation_id: str) -> str:
    return POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE.format(
        evaluation_id=quote(evaluation_id, safe="")
    )


def _policy_evaluation_posture(payload: dict[str, Any]) -> _PolicyEvaluationPosture:
    requirements = (
        _requirement_list(payload, "approval_dependencies")
        + _requirement_list(payload, "disclosure_requirements")
        + _requirement_list(payload, "consent_requirements")
    )
    open_requirement_count = _open_requirement_count(requirements)
    blocked_requirement_count = _blocked_requirement_count(requirements)
    sla_open_count = _sla_open_requirement_count(payload)
    if sla_open_count is not None:
        open_requirement_count = max(open_requirement_count, sla_open_count)

    return _PolicyEvaluationPosture(
        evaluation_status=_text_field(payload, "evaluation_status"),
        open_requirement_count=open_requirement_count,
        blocked_requirement_count=blocked_requirement_count,
        sign_off_status=_text_field(payload, "sign_off_status"),
        sign_off_blocker_count=len(_sign_off_blockers(payload)),
        client_ready_publication=_text_field(payload, "client_ready_publication"),
    )


def _source_ref(
    payload: dict[str, Any],
    *,
    request: AdvisePolicyEvaluationEvidenceRequest,
    route: str,
) -> SourceRef:
    metadata = _optional_object_field(payload, "metadata")
    replay_metadata = _optional_object_field(payload, "replay_metadata")
    return SourceRef(
        product_id=POLICY_EVALUATION_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version=str(
            metadata.get("product_version")
            or metadata.get("productVersion")
            or replay_metadata.get("product_version")
            or replay_metadata.get("productVersion")
            or PRODUCT_VERSION
        ),
        route=route,
        as_of_date=_as_of_date(metadata, replay_metadata, payload, fallback=request.as_of_date),
        generated_at_utc=_generated_at(metadata, replay_metadata, payload),
        content_hash=_content_hash(metadata, replay_metadata, payload),
        data_quality_status=_data_quality_status(metadata, replay_metadata),
        freshness=_freshness(metadata, replay_metadata),
    )


def _requirement_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise AdviseSourceUnavailable(code=f"advise_{key}_malformed")


def _sign_off_blockers(payload: dict[str, Any]) -> list[str]:
    value = payload.get("sign_off_blockers")
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise AdviseSourceUnavailable(code="advise_sign_off_blockers_malformed")


def _open_requirement_count(requirements: list[dict[str, Any]]) -> int:
    return sum(1 for requirement in requirements if _status(requirement) == "OPEN")


def _blocked_requirement_count(requirements: list[dict[str, Any]]) -> int:
    return sum(1 for requirement in requirements if _status(requirement) == "BLOCKED")


def _status(requirement: dict[str, Any]) -> str | None:
    value = requirement.get("status")
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return None


def _sla_open_requirement_count(payload: dict[str, Any]) -> int | None:
    sla_posture = _optional_object_field(payload, "sla_posture")
    value = sla_posture.get("open_requirement_count")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdviseSourceUnavailable(code="advise_open_requirement_count_malformed")
    return value


def _optional_object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise AdviseSourceUnavailable(code=f"advise_{key}_malformed")


def _text_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _generated_at(*payloads: dict[str, Any]) -> datetime:
    for payload in payloads:
        for key in (
            "generated_at",
            "generatedAt",
            "evaluated_at_utc",
            "evaluatedAtUtc",
            "observed_at_utc",
            "observedAtUtc",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise AdviseSourceUnavailable(code="advise_generated_at_naive")
                return parsed
    raise AdviseSourceUnavailable(code="advise_generated_at_missing")


def _as_of_date(
    *payloads: dict[str, Any],
    fallback: date,
) -> date:
    for payload in payloads:
        for key in ("as_of_date", "asOfDate", "evaluated_as_of_date", "evaluatedAsOfDate"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return date.fromisoformat(value)
    return fallback


def _content_hash(*payloads: dict[str, Any]) -> str:
    for payload in payloads:
        for key in (
            "content_hash",
            "contentHash",
            "evaluation_hash",
            "evaluationHash",
            "source_evaluation_hash",
            "sourceEvaluationHash",
            "request_fingerprint",
            "requestFingerprint",
            "lineage_fingerprint",
            "lineageFingerprint",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value if value.startswith("sha256:") else f"sha256:{value}"
    raise AdviseSourceUnavailable(code="advise_content_hash_missing")


def _data_quality_status(*payloads: dict[str, Any]) -> str:
    for payload in payloads:
        value = payload.get("data_quality_status") or payload.get("dataQualityStatus")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _freshness(*payloads: dict[str, Any]) -> EvidenceFreshness:
    for payload in payloads:
        value = (
            payload.get("freshness")
            or payload.get("freshness_state")
            or payload.get("freshnessState")
            or payload.get("freshness_status")
            or payload.get("freshnessStatus")
        )
        if isinstance(value, str) and value.strip():
            normalized = value.strip().lower()
            if "stale" in normalized:
                return EvidenceFreshness.STALE
            if "expired" in normalized:
                return EvidenceFreshness.EXPIRED
            if "unavailable" in normalized:
                return EvidenceFreshness.UNAVAILABLE
            if "current" in normalized:
                return EvidenceFreshness.CURRENT
    return EvidenceFreshness.UNAVAILABLE


def _diagnostic(posture: _PolicyEvaluationPosture) -> str:
    if posture.evaluation_status is None or posture.sign_off_status is None:
        return "advise_policy_evaluation_source_partial"
    if posture.open_requirement_count > 0 or posture.blocked_requirement_count > 0:
        return "advise_policy_requirements_open"
    if posture.sign_off_blocker_count > 0:
        return "advise_policy_sign_off_blocked"
    return "advise_policy_context_available"
