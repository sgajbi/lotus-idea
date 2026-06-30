from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain import (
    ConversionTarget,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    SourceSystem,
)
from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamJsonClient,
    DownstreamServiceError,
)
from app.ports.downstream_realization import DownstreamRealizationOutcome


class DownstreamRealizationConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class DownstreamRealizationAdapterConfig:
    base_url: str
    submit_path: str
    source_authority: SourceSystem
    timeout_seconds: float = 2.0
    max_connections: int = 20
    max_keepalive_connections: int = 10
    pool_timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not self.submit_path.startswith("/"):
            raise DownstreamRealizationConfigurationError("submit_path must start with '/'.")
        if "?" in self.submit_path or "#" in self.submit_path:
            raise DownstreamRealizationConfigurationError(
                "submit_path must not include query string or fragment."
            )
        try:
            DownstreamClientConfig(
                base_url=self.base_url,
                timeout_seconds=self.timeout_seconds,
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
                pool_timeout_seconds=self.pool_timeout_seconds,
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
        self._config = config
        self._client = _client_from_config(config, client)

    def submit_proposal_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        _require_target(intent, ConversionTarget.ADVISE_PROPOSAL)
        return _post_downstream_envelope(
            self._client,
            self._config.submit_path,
            json_payload=_conversion_intent_envelope(intent),
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

    def close(self) -> None:
        self._client.close()


class HttpManageActionRealizationClient:
    def __init__(
        self,
        config: DownstreamRealizationAdapterConfig,
        client: DownstreamJsonClient | None = None,
    ) -> None:
        _require_source_authority(config, SourceSystem.LOTUS_MANAGE)
        self._config = config
        self._client = _client_from_config(config, client)

    def submit_action_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        _require_target(intent, ConversionTarget.MANAGE_REVIEW)
        return _post_downstream_envelope(
            self._client,
            self._config.submit_path,
            json_payload=_conversion_intent_envelope(intent),
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
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
        self._config = config
        self._client = _client_from_config(config, client)

    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        return _post_downstream_envelope(
            self._client,
            self._config.submit_path,
            json_payload=_report_evidence_pack_envelope(evidence_pack),
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
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
            timeout_seconds=config.timeout_seconds,
            max_connections=config.max_connections,
            max_keepalive_connections=config.max_keepalive_connections,
            pool_timeout_seconds=config.pool_timeout_seconds,
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
) -> DownstreamRealizationOutcome:
    try:
        client.post_json(
            submit_path,
            json_payload=json_payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
    except DownstreamServiceError as exc:
        return DownstreamRealizationOutcome.rejected_by_downstream(_failure_reason(exc))
    return DownstreamRealizationOutcome.accepted_by_downstream()


def _conversion_intent_envelope(intent: GovernedConversionIntent) -> dict[str, Any]:
    return {
        "conversionIntentId": intent.intent.conversion_intent_id,
        "candidateId": intent.intent.candidate_id,
        "target": intent.intent.target.value,
        "sourceStatus": intent.intent.source_status.value,
        "targetSourceAuthority": intent.target_source_authority.value,
        "evidencePacketId": intent.evidence_packet_id,
        "evidenceContentFingerprint": intent.evidence_content_hash,
        "sourceSignalIds": list(intent.source_signal_ids),
        "boundary": intent.boundary.value,
        "reasonCodes": [reason.value for reason in intent.reason_codes],
        "requestedAtUtc": intent.intent.requested_at_utc.isoformat(),
        "grantsDownstreamAuthority": intent.grants_downstream_authority,
        "producer": "lotus-idea",
        "supportabilityStatus": "not_certified",
    }


def _report_evidence_pack_envelope(evidence_pack: GovernedReportEvidencePack) -> dict[str, Any]:
    return {
        "reportEvidencePackId": evidence_pack.report_evidence_pack_id,
        "conversionIntentId": evidence_pack.conversion_intent_id,
        "candidateId": evidence_pack.candidate_id,
        "purpose": evidence_pack.purpose.value,
        "evidencePacketId": evidence_pack.evidence_packet_id,
        "evidenceContentFingerprint": evidence_pack.evidence_content_hash,
        "sourceSignalIds": list(evidence_pack.source_signal_ids),
        "sourceSummaries": [
            {
                "productId": summary.product_id,
                "sourceSystem": summary.source_system.value,
                "productVersion": summary.product_version,
                "asOfDate": summary.as_of_date,
                "generatedAtUtc": summary.generated_at_utc.isoformat(),
                "dataQualityStatus": summary.data_quality_status,
                "freshness": summary.freshness,
            }
            for summary in evidence_pack.source_summaries
        ],
        "reasonCodes": [reason.value for reason in evidence_pack.reason_codes],
        "reportSourceAuthority": evidence_pack.report_source_authority.value,
        "renderSourceAuthority": evidence_pack.render_source_authority.value,
        "archiveSourceAuthority": evidence_pack.archive_source_authority.value,
        "boundary": evidence_pack.boundary.value,
        "retentionPolicyRef": evidence_pack.retention_policy_ref,
        "requestedAtUtc": evidence_pack.requested_at_utc.isoformat(),
        "grantsClientPublicationAuthority": evidence_pack.grants_client_publication_authority,
        "createsRenderedOutput": evidence_pack.creates_rendered_output,
        "createsArchiveRecord": evidence_pack.creates_archive_record,
        "producer": "lotus-idea",
        "supportabilityStatus": "not_certified",
    }


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
