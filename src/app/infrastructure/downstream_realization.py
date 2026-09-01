from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
    ConversionTarget,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    ReviewAccessScope,
    SourceSystem,
)
from app.domain.data_lifecycle import REPORT_EVIDENCE_RETENTION_POLICY_REF
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationOutcome,
)


class DownstreamRealizationConfigurationError(ValueError):
    pass


# Lotus Idea persists the external policy reference as governed lifecycle
# metadata. Report owns a separate, route-specific selector. Keep the
# translation at this anti-corruption boundary so neither persistence nor the
# Idea domain starts depending on Report's local policy vocabulary.
_REPORT_OWNER_RETENTION_POLICY_BY_IDEA_REFERENCE = {
    REPORT_EVIDENCE_RETENTION_POLICY_REF: "generated-report-standard",
}


@dataclass(frozen=True)
class AdviseRealizationServiceContext:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    service_identity: str
    capabilities: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("actor_id", self.actor_id),
            ("role", self.role),
            ("tenant_id", self.tenant_id),
            ("legal_entity_code", self.legal_entity_code),
            ("service_identity", self.service_identity),
            ("capabilities", self.capabilities),
        ):
            if not value.strip():
                raise DownstreamRealizationConfigurationError(
                    f"advise realization {field_name} is required."
                )

    def request_headers(self) -> dict[str, str]:
        return _trusted_local_service_headers(self)


@dataclass(frozen=True)
class ManageRealizationServiceContext:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    service_identity: str
    capabilities: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("actor_id", self.actor_id),
            ("role", self.role),
            ("tenant_id", self.tenant_id),
            ("legal_entity_code", self.legal_entity_code),
            ("service_identity", self.service_identity),
            ("capabilities", self.capabilities),
        ):
            if not value.strip():
                raise DownstreamRealizationConfigurationError(
                    f"manage realization {field_name} is required."
                )

    def request_headers(self) -> dict[str, str]:
        return _trusted_local_service_headers(self)


@dataclass(frozen=True)
class ReportRealizationServiceContext:
    actor_id: str
    caller_application: str
    tenant_id: str
    region: str
    requested_output_formats: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("actor_id", self.actor_id),
            ("caller_application", self.caller_application),
            ("tenant_id", self.tenant_id),
            ("region", self.region),
        ):
            if not value.strip():
                raise DownstreamRealizationConfigurationError(
                    f"report realization {field_name} is required."
                )
        if not self.requested_output_formats:
            raise DownstreamRealizationConfigurationError(
                "report realization requested_output_formats is required."
            )
        if any(not output_format.strip() for output_format in self.requested_output_formats):
            raise DownstreamRealizationConfigurationError(
                "report realization requested_output_formats cannot contain blanks."
            )

    def request_headers(self) -> dict[str, str]:
        return {
            "X-Actor-Id": self.actor_id,
            "X-Caller-Application": self.caller_application,
            "X-Tenant-Id": self.tenant_id,
            "X-Region": self.region,
        }


class _TrustedLocalServiceContext(Protocol):
    @property
    def actor_id(self) -> str: ...

    @property
    def role(self) -> str: ...

    @property
    def tenant_id(self) -> str: ...

    @property
    def legal_entity_code(self) -> str: ...

    @property
    def service_identity(self) -> str: ...

    @property
    def capabilities(self) -> str: ...


def _trusted_local_service_headers(context: _TrustedLocalServiceContext) -> dict[str, str]:
    return {
        "X-Actor-Id": context.actor_id,
        "X-Role": context.role,
        "X-Tenant-Id": context.tenant_id,
        "X-Legal-Entity-Code": context.legal_entity_code,
        "X-Service-Identity": context.service_identity,
        "X-Capabilities": context.capabilities,
        "X-Principal-Status": "ACTIVE",
    }


@dataclass(frozen=True)
class DownstreamRealizationAdapterConfig:
    base_url: str
    submit_path: str
    source_authority: SourceSystem
    history_path_template: str | None = None
    timeout_seconds: float = 2.0
    max_connections: int = 20
    max_keepalive_connections: int = 10
    pool_timeout_seconds: float = 2.0
    retry_max_attempts: int = 1
    retry_initial_backoff_seconds: float = 0.05
    retry_max_backoff_seconds: float = 0.5
    advise_service_context: AdviseRealizationServiceContext | None = None
    manage_service_context: ManageRealizationServiceContext | None = None
    report_service_context: ReportRealizationServiceContext | None = None

    def __post_init__(self) -> None:
        if not self.submit_path.startswith("/"):
            raise DownstreamRealizationConfigurationError("submit_path must start with '/'.")
        if "?" in self.submit_path or "#" in self.submit_path:
            raise DownstreamRealizationConfigurationError(
                "submit_path must not include query string or fragment."
            )
        if self.history_path_template is not None:
            if not self.history_path_template.startswith("/"):
                raise DownstreamRealizationConfigurationError(
                    "history_path_template must start with '/'."
                )
            if self.history_path_template.count("{intake_id}") != 1:
                raise DownstreamRealizationConfigurationError(
                    "history_path_template must contain one {intake_id} placeholder."
                )
            if "?" in self.history_path_template or "#" in self.history_path_template:
                raise DownstreamRealizationConfigurationError(
                    "history_path_template must not include query string or fragment."
                )
        try:
            DownstreamClientConfig(
                base_url=self.base_url,
                dependency=self.source_authority.value,
                timeout_seconds=self.timeout_seconds,
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
                pool_timeout_seconds=self.pool_timeout_seconds,
                retry_max_attempts=self.retry_max_attempts,
                retry_initial_backoff_seconds=self.retry_initial_backoff_seconds,
                retry_max_backoff_seconds=self.retry_max_backoff_seconds,
            )
        except ValueError as exc:
            raise DownstreamRealizationConfigurationError(str(exc)) from exc


class HttpAdviseProposalRealizationClient:
    def __init__(
        self,
        config: DownstreamRealizationAdapterConfig,
        client: DownstreamJsonClient | None = None,
    ) -> None:
        _require_source_authority(config, SourceSystem.LOTUS_ADVISE)
        if config.advise_service_context is None:
            raise DownstreamRealizationConfigurationError(
                "advise realization service context is required."
            )
        self._advise_service_context = config.advise_service_context
        self._config = config
        self._client = _client_from_config(config, client)

    def submit_proposal_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        _require_target(intent, ConversionTarget.ADVISE_PROPOSAL)
        return _post_downstream_envelope(
            self._client,
            self._config.submit_path,
            json_payload=_conversion_intent_envelope(intent, access_scope=access_scope),
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            additional_headers=self._advise_service_context.request_headers(),
            accepted_response_mapper=_advise_outcome_from_receipt,
        )

    def load_proposal_realization(
        self,
        *,
        intake_id: str,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> AdviseProposalRealizationHistory:
        if self._config.history_path_template is None:
            raise DownstreamRealizationConfigurationError(
                "advise realization history_path_template is required."
            )
        normalized_intake_id = intake_id.strip()
        if not normalized_intake_id or not normalized_intake_id.isprintable():
            raise ValueError("intake_id is required")
        headers = self._advise_service_context.request_headers()
        headers.update(
            {
                "X-Portfolio-Id": access_scope.portfolio_id,
                "X-Authorized-Portfolio-Id": access_scope.portfolio_id,
            }
        )
        payload = self._client.get_json(
            self._config.history_path_template.format(intake_id=normalized_intake_id),
            correlation_id=correlation_id,
            trace_id=trace_id,
            additional_headers=headers,
        )
        return _advise_realization_history_from_payload(payload)

    def close(self) -> None:
        self._client.close()


class HttpManageActionRealizationClient:
    def __init__(
        self,
        config: DownstreamRealizationAdapterConfig,
        client: DownstreamJsonClient | None = None,
    ) -> None:
        _require_source_authority(config, SourceSystem.LOTUS_MANAGE)
        if config.manage_service_context is None:
            raise DownstreamRealizationConfigurationError(
                "manage realization service context is required."
            )
        self._manage_service_context = config.manage_service_context
        self._config = config
        self._client = _client_from_config(config, client)

    def submit_action_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        _require_target(intent, ConversionTarget.MANAGE_REVIEW)
        return _post_downstream_envelope(
            self._client,
            self._config.submit_path,
            json_payload=_conversion_intent_envelope(intent, access_scope=access_scope),
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            additional_headers=self._manage_service_context.request_headers(),
        )

    def close(self) -> None:
        self._client.close()


class HttpReportEvidencePackMaterializationClient:
    def __init__(
        self,
        config: DownstreamRealizationAdapterConfig,
        client: DownstreamJsonClient | None = None,
    ) -> None:
        _require_source_authority(config, SourceSystem.LOTUS_REPORT)
        if config.report_service_context is None:
            raise DownstreamRealizationConfigurationError(
                "report realization service context is required."
            )
        self._report_service_context = config.report_service_context
        self._config = config
        self._client = _client_from_config(config, client)

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        return _post_downstream_envelope(
            self._client,
            self._config.submit_path,
            json_payload=_report_evidence_pack_materialization_envelope(
                evidence_pack,
                access_scope=access_scope,
                service_context=self._report_service_context,
            ),
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            additional_headers=self._report_service_context.request_headers(),
        )

    def close(self) -> None:
        self._client.close()


def _client_from_config(
    config: DownstreamRealizationAdapterConfig,
    client: DownstreamJsonClient | None,
) -> DownstreamJsonClient:
    return client or DownstreamJsonClient(
        DownstreamClientConfig(
            base_url=config.base_url,
            dependency=config.source_authority.value,
            timeout_seconds=config.timeout_seconds,
            max_connections=config.max_connections,
            max_keepalive_connections=config.max_keepalive_connections,
            pool_timeout_seconds=config.pool_timeout_seconds,
            retry_max_attempts=config.retry_max_attempts,
            retry_initial_backoff_seconds=config.retry_initial_backoff_seconds,
            retry_max_backoff_seconds=config.retry_max_backoff_seconds,
        )
    )


def _post_downstream_envelope(
    client: DownstreamJsonClient,
    submit_path: str,
    *,
    json_payload: dict[str, Any],
    correlation_id: str | None,
    trace_id: str | None,
    idempotency_key: str | None,
    additional_headers: dict[str, str] | None = None,
    accepted_response_mapper: (
        Callable[[Mapping[str, Any]], DownstreamRealizationOutcome] | None
    ) = None,
) -> DownstreamRealizationOutcome:
    try:
        response_payload = client.post_json(
            submit_path,
            json_payload=json_payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            additional_headers=additional_headers,
        )
    except DownstreamServiceError as exc:
        failure_reason = _failure_reason(exc)
        if exc.status_code is not None and 400 <= exc.status_code < 500:
            return DownstreamRealizationOutcome.rejected_by_downstream(failure_reason)
        return DownstreamRealizationOutcome.unknown(failure_reason)
    if accepted_response_mapper is None:
        return DownstreamRealizationOutcome.accepted_by_downstream()
    try:
        return accepted_response_mapper(response_payload)
    except (KeyError, TypeError, ValueError):
        return DownstreamRealizationOutcome.unknown("downstream_malformed_response")


def _advise_outcome_from_receipt(
    payload: Mapping[str, Any],
) -> DownstreamRealizationOutcome:
    accepted = payload.get("intake_receipt_accepted")
    if accepted is False:
        return DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected")
    if accepted is not True:
        raise ValueError("intake_receipt_accepted must be boolean")
    return DownstreamRealizationOutcome.accepted_by_downstream(
        DownstreamOwnerReceipt(
            owner_authority=SourceSystem.LOTUS_ADVISE,
            owner_request_id=_required_response_text(payload, "intake_id"),
            owner_realization_id=_required_response_text(payload, "realization_id"),
            owner_work_id=_optional_response_text(payload, "review_work_id"),
            source_event_version=_required_response_int(payload, "source_event_version"),
            source_evidence_fingerprint=_required_response_text(
                payload,
                "source_evidence_fingerprint",
            ),
        )
    )


def _required_response_text(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value


def _optional_response_text(payload: Mapping[str, Any], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-blank when present")
    return value


def _required_response_int(payload: Mapping[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _required_response_bool(payload: Mapping[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be boolean")
    return value


def _required_response_datetime(payload: Mapping[str, Any], field_name: str) -> datetime:
    value = _required_response_text(payload, field_name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{field_name} must be UTC")
    return parsed


def _advise_realization_history_from_payload(
    payload: Mapping[str, Any],
) -> AdviseProposalRealizationHistory:
    raw_outcomes = payload.get("outcomes")
    if not isinstance(raw_outcomes, list):
        raise ValueError("outcomes must be an array")
    review_work_status = _optional_response_text(payload, "review_work_status")
    return AdviseProposalRealizationHistory(
        realization_id=_required_response_text(payload, "realization_id"),
        intake_id=_required_response_text(payload, "intake_id"),
        review_work_id=_optional_response_text(payload, "review_work_id"),
        review_work_status=(
            AdviseProposalReviewWorkStatus(review_work_status)
            if review_work_status is not None
            else None
        ),
        source_authority=_required_response_text(payload, "source_authority"),
        realization_authority=_required_response_text(payload, "realization_authority"),
        tenant_id=_required_response_text(payload, "tenant_id"),
        legal_entity_code=_required_response_text(payload, "legal_entity_code"),
        portfolio_id=_required_response_text(payload, "portfolio_id"),
        idea_candidate_id=_required_response_text(payload, "idea_candidate_id"),
        conversion_intent_id=_required_response_text(payload, "conversion_intent_id"),
        source_evidence_fingerprint=_required_response_text(
            payload,
            "source_evidence_fingerprint",
        ),
        current_status=AdviseProposalRealizationStatus(
            _required_response_text(payload, "current_status")
        ),
        current_source_event_version=_required_response_int(
            payload,
            "current_source_event_version",
        ),
        proposal_id=_optional_response_text(payload, "proposal_id"),
        proposal_record_created=_required_response_bool(payload, "proposal_record_created"),
        suitability_authority_granted=_required_response_bool(
            payload,
            "suitability_authority_granted",
        ),
        order_created=_required_response_bool(payload, "order_created"),
        client_publication_authorized=_required_response_bool(
            payload,
            "client_publication_authorized",
        ),
        created_at_utc=_required_response_datetime(payload, "created_at"),
        updated_at_utc=_required_response_datetime(payload, "updated_at"),
        outcomes=tuple(_advise_realization_outcome_from_payload(item) for item in raw_outcomes),
    )


def _advise_realization_outcome_from_payload(
    payload: object,
) -> AdviseProposalRealizationOutcome:
    if not isinstance(payload, Mapping):
        raise ValueError("Advise realization outcome must be an object")
    return AdviseProposalRealizationOutcome(
        outcome_id=_required_response_text(payload, "outcome_id"),
        source_event_version=_required_response_int(payload, "source_event_version"),
        status=AdviseProposalRealizationStatus(_required_response_text(payload, "status")),
        reason_code=_required_response_text(payload, "reason_code"),
        occurred_at_utc=_required_response_datetime(payload, "occurred_at"),
        review_work_id=_optional_response_text(payload, "review_work_id"),
        proposal_id=_optional_response_text(payload, "proposal_id"),
        terminal=_required_response_bool(payload, "terminal"),
    )


def _conversion_intent_envelope(
    intent: GovernedConversionIntent,
    *,
    access_scope: ReviewAccessScope,
) -> dict[str, Any]:
    if intent.intent.target is ConversionTarget.ADVISE_PROPOSAL:
        intent_type = "REVIEW_FOR_ADVISORY_PROPOSAL"
    elif intent.intent.target is ConversionTarget.MANAGE_REVIEW:
        intent_type = "REVIEW_FOR_REBALANCE"
    else:
        raise ValueError("unsupported conversion target for downstream intake envelope")
    envelope = {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": intent.intent.candidate_id,
        "conversion_intent_id": intent.intent.conversion_intent_id,
        "intent_type": intent_type,
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": intent.intent.candidate_id,
                "content_hash": intent.evidence_content_hash,
            }
        ],
    }
    if intent.intent.target is ConversionTarget.ADVISE_PROPOSAL:
        envelope["portfolio_id"] = access_scope.portfolio_id
    return envelope


def _report_evidence_pack_envelope(evidence_pack: GovernedReportEvidencePack) -> dict[str, Any]:
    return {
        "report_evidence_pack_id": evidence_pack.report_evidence_pack_id,
        "conversion_intent_id": evidence_pack.conversion_intent_id,
        "candidate_id": evidence_pack.candidate_id,
        "purpose": _report_intake_purpose(evidence_pack),
        "evidence_packet_id": evidence_pack.evidence_packet_id,
        "evidence_content_fingerprint": evidence_pack.evidence_content_hash,
        "source_signal_ids": list(evidence_pack.source_signal_ids),
        "source_summaries": [
            {
                "product_id": summary.product_id,
                "source_system": summary.source_system.value,
                "product_version": summary.product_version,
                "as_of_date": summary.as_of_date,
                "generated_at_utc": summary.generated_at_utc.isoformat(),
                "data_quality_status": summary.data_quality_status,
                "freshness": summary.freshness,
            }
            for summary in evidence_pack.source_summaries
        ],
        "reason_codes": [reason.value for reason in evidence_pack.reason_codes],
        "report_source_authority": evidence_pack.report_source_authority.value,
        "render_source_authority": evidence_pack.render_source_authority.value,
        "archive_source_authority": evidence_pack.archive_source_authority.value,
        "boundary": "REPORT_INTAKE_ONLY",
        "retention_policy_ref": _report_owner_retention_policy_ref(evidence_pack),
        "requested_at_utc": evidence_pack.requested_at_utc.isoformat(),
        "grants_client_publication_authority": evidence_pack.grants_client_publication_authority,
        "creates_rendered_output": evidence_pack.creates_rendered_output,
        "creates_archive_record": evidence_pack.creates_archive_record,
        "producer": "lotus-idea",
        "supportability_status": "not_certified",
    }


def _report_evidence_pack_materialization_envelope(
    evidence_pack: GovernedReportEvidencePack,
    *,
    access_scope: ReviewAccessScope,
    service_context: ReportRealizationServiceContext,
) -> dict[str, Any]:
    if access_scope.tenant_id != service_context.tenant_id:
        raise DownstreamRealizationConfigurationError(
            "Report materialization candidate tenant does not match the configured service context."
        )
    return {
        "idea_evidence_pack": _report_evidence_pack_envelope(evidence_pack),
        "portfolio_id": access_scope.portfolio_id,
        "as_of_date": _report_materialization_as_of_date(evidence_pack),
        "requested_output_formats": list(service_context.requested_output_formats),
        "boundary": "REPORT_JOB_MATERIALIZATION",
        "grants_client_publication_authority": False,
        "producer": "lotus-idea",
        "supportability_status": "not_certified",
    }


def _report_materialization_as_of_date(evidence_pack: GovernedReportEvidencePack) -> str:
    as_of_dates = {summary.as_of_date.strip() for summary in evidence_pack.source_summaries}
    if len(as_of_dates) != 1:
        raise DownstreamRealizationConfigurationError(
            "Report materialization requires one consistent source as_of_date."
        )
    as_of_date = as_of_dates.pop()
    try:
        return date.fromisoformat(as_of_date).isoformat()
    except ValueError as exc:
        raise DownstreamRealizationConfigurationError(
            "Report materialization source as_of_date must be ISO-8601."
        ) from exc


def _report_intake_purpose(evidence_pack: GovernedReportEvidencePack) -> str:
    purpose_by_idea_purpose = {
        "client_review_report_section": "CLIENT_REPORT_EVIDENCE",
        "advisor_review_evidence": "ADVISOR_REVIEW_APPENDIX",
        "audit_evidence": "ADVISOR_REVIEW_APPENDIX",
    }
    return purpose_by_idea_purpose[evidence_pack.purpose.value]


def _report_owner_retention_policy_ref(evidence_pack: GovernedReportEvidencePack) -> str:
    try:
        return _REPORT_OWNER_RETENTION_POLICY_BY_IDEA_REFERENCE[evidence_pack.retention_policy_ref]
    except KeyError as exc:
        raise DownstreamRealizationConfigurationError(
            "Report retention policy reference is not mapped to an owner policy selector."
        ) from exc


def _failure_reason(exc: DownstreamServiceError) -> str:
    if exc.status_code in {401, 403}:
        return "downstream_permission_denied"
    if exc.status_code is not None and 400 <= exc.status_code < 500:
        return "downstream_rejected"
    if exc.code == "upstream_timeout":
        return "downstream_timeout"
    if exc.code == "upstream_malformed_response":
        return "downstream_malformed_response"
    return "downstream_unavailable"


def _require_source_authority(
    config: DownstreamRealizationAdapterConfig,
    expected: SourceSystem,
) -> None:
    if config.source_authority is not expected:
        raise DownstreamRealizationConfigurationError(f"source_authority must be {expected.value}.")


def _require_target(intent: GovernedConversionIntent, expected: ConversionTarget) -> None:
    if intent.intent.target is not expected:
        raise ValueError(f"conversion intent target must be {expected.value}")
