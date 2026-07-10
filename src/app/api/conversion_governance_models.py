from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.persistence_summary import persistence_summary_payload
from app.api.request_validation import require_non_empty_reason_codes
from app.api.temporal_validation import require_timezone_aware
from app.application.conversion_workflow import (
    RecordConversionOutcomeToRepositoryCommand,
    RequestConversionIntentToRepositoryCommand,
)
from app.domain import (
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    ConversionTarget,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    ReasonCode,
    SourceSystem,
)
from app.security.caller_context import CallerContext


class ConversionIntentRequest(CamelModel):
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: ConversionTarget
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")

    @field_validator("conversion_intent_id")
    @classmethod
    def _intent_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("conversionIntentId is required")
        return value

    _reason_codes_must_not_be_empty = field_validator("reason_codes")(
        require_non_empty_reason_codes
    )

    @field_validator("requested_at_utc")
    @classmethod
    def _requested_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="requestedAtUtc")

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        idempotency_key: str,
    ) -> RequestConversionIntentToRepositoryCommand:
        return RequestConversionIntentToRepositoryCommand(
            candidate_id=candidate_id,
            conversion=ConversionIntentCommand(
                conversion_intent_id=self.conversion_intent_id,
                target=self.target,
                actor_subject=caller.subject,
                idempotency_key=idempotency_key,
                reason_codes=self.reason_codes,
                requested_at_utc=self.requested_at_utc,
            ),
            idempotency_key=idempotency_key,
        )


class ConversionOutcomeRequest(CamelModel):
    conversion_outcome_id: str = Field(..., alias="conversionOutcomeId")
    status: ConversionOutcomeStatus
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    source_event_version: int = Field(..., alias="sourceEventVersion", gt=0)
    downstream_reference: str | None = Field(default=None, alias="downstreamReference")
    supersedes_conversion_outcome_id: str | None = Field(
        default=None,
        alias="supersedesConversionOutcomeId",
    )
    correction_reason: str | None = Field(default=None, alias="correctionReason")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @field_validator("conversion_outcome_id")
    @classmethod
    def _outcome_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("conversionOutcomeId is required")
        return value

    @field_validator("downstream_reference")
    @classmethod
    def _downstream_reference_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("downstreamReference cannot be blank")
        return value

    @field_validator("supersedes_conversion_outcome_id", "correction_reason")
    @classmethod
    def _correction_fields_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("correction fields cannot be blank")
        return value

    @field_validator("recorded_at_utc")
    @classmethod
    def _recorded_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="recordedAtUtc")

    def to_command(
        self,
        *,
        conversion_intent_id: str,
        caller: CallerContext,
        idempotency_key: str,
    ) -> RecordConversionOutcomeToRepositoryCommand:
        return RecordConversionOutcomeToRepositoryCommand(
            conversion_intent_id=conversion_intent_id,
            outcome=ConversionOutcomeCommand(
                conversion_outcome_id=self.conversion_outcome_id,
                status=self.status,
                source_system=self.source_system,
                source_event_version=self.source_event_version,
                downstream_reference=self.downstream_reference,
                recorded_at_utc=self.recorded_at_utc,
                actor_subject=caller.subject,
                supersedes_conversion_outcome_id=self.supersedes_conversion_outcome_id,
                correction_reason=self.correction_reason,
            ),
            idempotency_key=idempotency_key,
        )


class ConversionIntentResponse(CamelModel):
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    candidate_id: str = Field(..., alias="candidateId")
    target: ConversionTarget
    source_status: str = Field(..., alias="sourceStatus")
    target_source_authority: SourceSystem = Field(..., alias="targetSourceAuthority")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    boundary: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, intent: GovernedConversionIntent) -> "ConversionIntentResponse":
        return cls(
            conversionIntentId=intent.intent.conversion_intent_id,
            candidateId=intent.intent.candidate_id,
            target=intent.intent.target,
            sourceStatus=intent.intent.source_status.value,
            targetSourceAuthority=intent.target_source_authority,
            evidencePacketId=intent.evidence_packet_id,
            evidenceContentHash=intent.evidence_content_hash,
            sourceSignalIds=intent.source_signal_ids,
            boundary=intent.boundary.value,
            reasonCodes=tuple(reason.value for reason in intent.reason_codes),
            requestedAtUtc=intent.intent.requested_at_utc,
            grantsDownstreamAuthority=intent.grants_downstream_authority,
        )


class ConversionOutcomeResponse(CamelModel):
    conversion_outcome_id: str = Field(..., alias="conversionOutcomeId")
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: ConversionTarget
    status: ConversionOutcomeStatus
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    source_event_version: int = Field(..., alias="sourceEventVersion")
    downstream_reference: str | None = Field(default=None, alias="downstreamReference")
    supersedes_conversion_outcome_id: str | None = Field(
        default=None,
        alias="supersedesConversionOutcomeId",
    )
    correction_reason: str | None = Field(default=None, alias="correctionReason")
    boundary: str
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")
    grants_execution_authority: bool = Field(False, alias="grantsExecutionAuthority")
    grants_client_communication_authority: bool = Field(
        False,
        alias="grantsClientCommunicationAuthority",
    )
    grants_suitability_authority: bool = Field(False, alias="grantsSuitabilityAuthority")

    @classmethod
    def from_domain(cls, outcome: GovernedConversionOutcome) -> "ConversionOutcomeResponse":
        return cls(
            conversionOutcomeId=outcome.outcome.conversion_outcome_id,
            conversionIntentId=outcome.conversion_intent_id,
            target=outcome.target,
            status=outcome.outcome.status,
            sourceSystem=outcome.source_system,
            sourceEventVersion=outcome.source_event_version,
            downstreamReference=outcome.outcome.downstream_reference,
            supersedesConversionOutcomeId=outcome.supersedes_conversion_outcome_id,
            correctionReason=outcome.correction_reason,
            boundary=outcome.boundary.value,
            recordedAtUtc=outcome.outcome.recorded_at_utc,
            grantsExecutionAuthority=outcome.grants_execution_authority,
            grantsClientCommunicationAuthority=outcome.grants_client_communication_authority,
            grantsSuitabilityAuthority=outcome.grants_suitability_authority,
        )


class ConversionPersistenceSummaryResponse(CamelModel):
    decision: ConversionPersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    review_posture: str | None = Field(default=None, alias="reviewPosture")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_result(
        cls,
        result: ConversionPersistenceResult,
    ) -> "ConversionPersistenceSummaryResponse":
        return cls(**persistence_summary_payload(result))


class ConversionIntentApiResponse(CamelModel):
    conversion_intent: ConversionIntentResponse | None = Field(
        default=None,
        alias="conversionIntent",
    )
    persistence: ConversionPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class ConversionOutcomeApiResponse(CamelModel):
    conversion_outcome: ConversionOutcomeResponse | None = Field(
        default=None,
        alias="conversionOutcome",
    )
    persistence: ConversionPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


__all__ = [
    "ConversionIntentApiResponse",
    "ConversionIntentRequest",
    "ConversionIntentResponse",
    "ConversionOutcomeApiResponse",
    "ConversionOutcomeRequest",
    "ConversionOutcomeResponse",
    "ConversionPersistenceSummaryResponse",
]
