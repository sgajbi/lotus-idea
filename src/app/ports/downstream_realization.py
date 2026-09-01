from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.domain import (
    AdviseProposalRealizationHistory,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    ReviewAccessScope,
    SourceSystem,
)


class DownstreamRealizationOutcomePosture(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DownstreamOwnerReceipt:
    """Source-safe identity returned by the service that accepted durable work."""

    owner_authority: SourceSystem
    owner_request_id: str
    owner_realization_id: str
    owner_work_id: str | None
    source_event_version: int
    source_evidence_fingerprint: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("owner_request_id", self.owner_request_id),
            ("owner_realization_id", self.owner_realization_id),
            ("source_evidence_fingerprint", self.source_evidence_fingerprint),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} is required")
        if self.owner_work_id is not None and not self.owner_work_id.strip():
            raise ValueError("owner_work_id must be non-blank when present")
        if self.source_event_version <= 0:
            raise ValueError("source_event_version must be positive")
        if not self.source_evidence_fingerprint.startswith("sha256:"):
            raise ValueError("source_evidence_fingerprint must use sha256")


@dataclass(frozen=True)
class DownstreamRealizationOutcome:
    posture: DownstreamRealizationOutcomePosture
    failure_reason: str | None = None
    owner_receipt: DownstreamOwnerReceipt | None = None

    def __post_init__(self) -> None:
        if self.posture is DownstreamRealizationOutcomePosture.ACCEPTED:
            if self.failure_reason is not None:
                raise ValueError("accepted outcome forbids failure_reason")
        else:
            if self.failure_reason is None or not self.failure_reason.strip():
                raise ValueError("non-accepted outcome requires failure_reason")
            if self.owner_receipt is not None:
                raise ValueError("non-accepted outcome forbids owner_receipt")

    @property
    def accepted(self) -> bool:
        return self.posture is DownstreamRealizationOutcomePosture.ACCEPTED

    @classmethod
    def accepted_by_downstream(
        cls,
        owner_receipt: DownstreamOwnerReceipt | None = None,
    ) -> "DownstreamRealizationOutcome":
        return cls(
            posture=DownstreamRealizationOutcomePosture.ACCEPTED,
            owner_receipt=owner_receipt,
        )

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
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        """Submit a source-safe proposal intent envelope to lotus-advise."""


class AdviseProposalRealizationReader(Protocol):
    def load_proposal_realization(
        self,
        *,
        intake_id: str,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> AdviseProposalRealizationHistory:
        """Load the exact Advise-owned realization history in trusted scope."""


class ManageActionRealizationClient(Protocol):
    def submit_action_intent(
        self,
        intent: GovernedConversionIntent,
        *,
        access_scope: ReviewAccessScope,
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
