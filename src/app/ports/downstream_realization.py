from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain import GovernedConversionIntent, GovernedReportEvidencePack


@dataclass(frozen=True)
class DownstreamRealizationOutcome:
    accepted: bool
    failure_reason: str | None = None

    @classmethod
    def accepted_by_downstream(cls) -> "DownstreamRealizationOutcome":
        return cls(accepted=True)

    @classmethod
    def rejected_by_downstream(cls, failure_reason: str) -> "DownstreamRealizationOutcome":
        if not failure_reason.strip():
            raise ValueError("failure_reason is required")
        return cls(accepted=False, failure_reason=failure_reason)


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
        correlation_id: str | None = None,
        trace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DownstreamRealizationOutcome:
        """Submit a source-safe evidence-pack request envelope to lotus-report."""
