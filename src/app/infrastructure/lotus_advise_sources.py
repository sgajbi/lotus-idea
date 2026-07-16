from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.infrastructure.downstream_client import DownstreamJsonClient, DownstreamServiceError
from app.ports.advise_sources import (
    ADVISE_POLICY_EVALUATION_PRODUCT_ID,
    ADVISE_POLICY_EVALUATION_PRODUCT_VERSION,
    ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdvisePolicyEvaluationRuntimeEvidence,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


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

    def close(self) -> None:
        self._advise_client.close()

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
        runtime_evidence = _runtime_evidence(payload, posture=posture, route=route)
        return AdvisePolicyEvaluationEvidence(
            evaluation_status=posture.evaluation_status,
            open_requirement_count=posture.open_requirement_count,
            blocked_requirement_count=posture.blocked_requirement_count,
            sign_off_status=posture.sign_off_status,
            sign_off_blocker_count=posture.sign_off_blocker_count,
            client_ready_publication=posture.client_ready_publication,
            policy_ref=_source_ref(runtime_evidence),
            workflow_runtime=runtime_evidence,
            advise_diagnostic=_diagnostic(posture, payload),
        )


def _workflow_route(evaluation_id: str) -> str:
    return ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE.format(
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


def _source_ref(runtime: AdvisePolicyEvaluationRuntimeEvidence) -> SourceRef | None:
    if (
        runtime.as_of_date is None
        or runtime.generated_at_utc is None
        or runtime.content_hash is None
    ):
        return None
    freshness = _evidence_freshness(runtime.freshness)
    return SourceRef(
        product_id=runtime.product_id,
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version=runtime.product_version,
        route=runtime.route,
        as_of_date=runtime.as_of_date,
        generated_at_utc=runtime.generated_at_utc,
        content_hash=runtime.content_hash,
        data_quality_status=runtime.data_quality_status,
        freshness=freshness,
    )


def _runtime_evidence(
    payload: dict[str, Any],
    *,
    posture: _PolicyEvaluationPosture,
    route: str,
) -> AdvisePolicyEvaluationRuntimeEvidence:
    metadata = _optional_object_field(payload, "metadata")
    replay_metadata = _optional_object_field(payload, "replay_metadata")
    return AdvisePolicyEvaluationRuntimeEvidence(
        product_id=_text_from_payloads("product_id", metadata, replay_metadata)
        or ADVISE_POLICY_EVALUATION_PRODUCT_ID,
        product_version=_text_from_payloads("product_version", metadata, replay_metadata)
        or ADVISE_POLICY_EVALUATION_PRODUCT_VERSION,
        route=route,
        evaluation_id=_text_from_payloads("evaluation_id", metadata, payload),
        tenant_scope_hash=_text_from_payloads(
            "tenant_scope_hash", metadata, replay_metadata, payload
        ),
        portfolio_id=_text_from_payloads("portfolio_id", metadata, payload),
        correlation_id=_text_from_payloads("correlation_id", metadata, replay_metadata, payload),
        trace_id=_text_from_payloads("trace_id", metadata, replay_metadata, payload),
        as_of_date=_as_of_date(metadata, replay_metadata, payload),
        generated_at_utc=_optional_generated_at(metadata, replay_metadata, payload),
        content_hash=_optional_hash(
            ("content_hash", "evaluation_hash"), metadata, replay_metadata, payload
        ),
        source_evidence_hash=_optional_hash(
            ("source_evidence_hash",), metadata, replay_metadata, payload
        ),
        policy_content_hash=_optional_hash(
            ("policy_content_hash",), metadata, replay_metadata, payload
        ),
        policy_pack_id=_text_from_payloads("policy_pack_id", metadata, replay_metadata),
        policy_version=_text_from_payloads("policy_version", metadata, replay_metadata),
        evaluation_status=posture.evaluation_status,
        open_requirement_count=posture.open_requirement_count,
        blocked_requirement_count=posture.blocked_requirement_count,
        sign_off_status=posture.sign_off_status,
        sign_off_blocker_count=posture.sign_off_blocker_count,
        client_ready_publication=posture.client_ready_publication,
        data_quality_status=_data_quality_status(metadata, replay_metadata),
        freshness=_freshness_text(metadata, replay_metadata),
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
    return int(value)


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


def _optional_generated_at(*payloads: dict[str, Any]) -> datetime | None:
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
    return None


def _as_of_date(
    *payloads: dict[str, Any],
) -> date | None:
    for payload in payloads:
        for key in ("as_of_date", "asOfDate", "evaluated_as_of_date", "evaluatedAsOfDate"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return date.fromisoformat(value)
    return None


def _optional_hash(keys: tuple[str, ...], *payloads: dict[str, Any]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value if value.startswith("sha256:") else f"sha256:{value}"
    return None


def _text_from_payloads(key: str, *payloads: dict[str, Any]) -> str | None:
    aliases = (key, _camel_case(key))
    for payload in payloads:
        for alias in aliases:
            value = payload.get(alias)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


def _data_quality_status(*payloads: dict[str, Any]) -> str:
    for payload in payloads:
        value = payload.get("data_quality_status") or payload.get("dataQualityStatus")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _freshness_text(*payloads: dict[str, Any]) -> str:
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
                return EvidenceFreshness.STALE.value
            if "expired" in normalized:
                return EvidenceFreshness.EXPIRED.value
            if "unavailable" in normalized:
                return EvidenceFreshness.UNAVAILABLE.value
            if "current" in normalized:
                return EvidenceFreshness.CURRENT.value
    return EvidenceFreshness.UNAVAILABLE.value


def _evidence_freshness(value: str) -> EvidenceFreshness:
    return EvidenceFreshness(value)


def _diagnostic(posture: _PolicyEvaluationPosture, payload: dict[str, Any]) -> str:
    explicit_diagnostic = _source_diagnostic(payload)
    if explicit_diagnostic is not None:
        return explicit_diagnostic
    if posture.evaluation_status is None or posture.sign_off_status is None:
        return "advise_policy_evaluation_source_partial"
    if posture.open_requirement_count > 0 or posture.blocked_requirement_count > 0:
        return "advise_policy_requirements_open"
    if posture.sign_off_blocker_count > 0:
        return "advise_policy_sign_off_blocked"
    return "advise_policy_context_available"


def _source_diagnostic(payload: dict[str, Any]) -> str | None:
    for key in ("advise_diagnostic", "diagnostic", "source_diagnostic"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("diagnostic_codes", "source_diagnostic_codes"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return None
