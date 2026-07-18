from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.domain import GovernedConversionIntent, GovernedReportEvidencePack, ReviewAccessScope


class DownstreamRealizationOutcomePosture(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DownstreamRealizationOutcome:
    posture: DownstreamRealizationOutcomePosture
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.posture is DownstreamRealizationOutcomePosture.ACCEPTED:
            if self.failure_reason is not None:
                raise ValueError("accepted outcome forbids failure_reason")
        elif self.failure_reason is None or not self.failure_reason.strip():
            raise ValueError("non-accepted outcome requires failure_reason")

    @property
    def accepted(self) -> bool:
        return self.posture is DownstreamRealizationOutcomePosture.ACCEPTED

    @classmethod
    def accepted_by_downstream(cls) -> "DownstreamRealizationOutcome":
        return cls(posture=DownstreamRealizationOutcomePosture.ACCEPTED)

    @classmethod
    def rejected_by_downstream(cls, failure_reason: str) -> "DownstreamRealizationOutcome":
        if not failure_reason.strip():
            raise ValueError("failure_reason is required")
        return cls(
            posture=DownstreamRealizationOutcomePosture.REJECTED,
            failure_reason=failure_reason,
        )

    @classmethod
    def unknown(cls, failure_reason: str) -> "DownstreamRealizationOutcome":
        return cls(
            posture=DownstreamRealizationOutcomePosture.UNKNOWN,
            failure_reason=failure_reason,
        )


class AdviseProposalRealizationClient(Protocol):
    def submit_proposal_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        """Submit a source-safe proposal intent envelope to lotus-advise."""


class ManageActionRealizationClient(Protocol):
    def submit_action_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        """Submit a source-safe action intent envelope to lotus-manage."""


class ReportEvidencePackMaterializationClient(Protocol):
    def submit_report_evidence_pack_request(
        self,
        evidence_pack: GovernedReportEvidencePack,
        *,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        """Submit a source-safe evidence-pack request envelope to lotus-report."""
