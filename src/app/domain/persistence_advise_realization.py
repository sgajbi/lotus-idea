from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.advise_realization import (
    AdviseProposalRealizationHistory,
    AdviseRealizationHistoryMutationDecision,
    AdviseRealizationHistoryMutationResult,
    evaluate_advise_realization_history_mutation,
)
from app.domain.downstream_submission import (
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
)
from app.domain.ideas import ConversionTarget, SourceSystem


class InMemoryAdviseRealizationRepositoryMixin:
    _advise_realization_histories: dict[str, AdviseProposalRealizationHistory]

    if TYPE_CHECKING:

        def downstream_submission_by_support_reference(
            self,
            support_reference: str,
        ) -> DownstreamSubmissionRecord | None: ...

    def advise_realization_history_by_support_reference(
        self,
        support_reference: str,
    ) -> AdviseProposalRealizationHistory | None:
        _require_text(support_reference, "support_reference")
        return self._advise_realization_histories.get(support_reference)

    def persist_advise_realization_history(
        self,
        *,
        support_reference: str,
        history: AdviseProposalRealizationHistory,
    ) -> AdviseRealizationHistoryMutationResult:
        submission = self.downstream_submission_by_support_reference(support_reference)
        if submission is None:
            return AdviseRealizationHistoryMutationResult(
                decision=AdviseRealizationHistoryMutationDecision.NOT_FOUND,
                history=None,
                blocker="downstream_submission_not_found",
            )
        blocker = advise_realization_submission_blocker(submission, history)
        if blocker is not None:
            return AdviseRealizationHistoryMutationResult(
                decision=AdviseRealizationHistoryMutationDecision.CONFLICT,
                history=self._advise_realization_histories.get(support_reference),
                blocker=blocker,
            )
        existing = self._advise_realization_histories.get(support_reference)
        decision = evaluate_advise_realization_history_mutation(existing, history)
        if decision is AdviseRealizationHistoryMutationDecision.ACCEPTED:
            self._advise_realization_histories[support_reference] = history
        return AdviseRealizationHistoryMutationResult(
            decision=decision,
            history=(
                history
                if decision is not AdviseRealizationHistoryMutationDecision.CONFLICT
                else existing
            ),
            blocker=(
                "advise_realization_history_conflict"
                if decision is AdviseRealizationHistoryMutationDecision.CONFLICT
                else None
            ),
        )


def advise_realization_submission_blocker(
    submission: DownstreamSubmissionRecord,
    history: AdviseProposalRealizationHistory,
) -> str | None:
    if submission.resource_type is not DownstreamSubmissionResourceType.CONVERSION_INTENT:
        return "advise_realization_requires_conversion_intent_submission"
    if submission.target is not ConversionTarget.ADVISE_PROPOSAL:
        return "advise_realization_requires_advise_target"
    if submission.source_authority is not SourceSystem.LOTUS_ADVISE:
        return "advise_realization_requires_advise_authority"
    if submission.status not in {
        DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
    }:
        return "advise_realization_requires_terminal_owner_submission"
    receipt = submission.owner_receipt
    if receipt is None:
        return "advise_realization_owner_receipt_missing"
    if (
        receipt.owner_authority is not SourceSystem.LOTUS_ADVISE
        or receipt.source_event_version is None
        or receipt.owner_request_id != history.intake_id
        or receipt.owner_realization_id != history.realization_id
        or receipt.owner_work_id != history.review_work_id
        or receipt.source_evidence_fingerprint != history.source_evidence_fingerprint
        or submission.resource_id != history.conversion_intent_id
    ):
        return "advise_realization_owner_receipt_conflict"
    if receipt.source_event_version > history.current_source_event_version:
        return "advise_realization_history_regressed_below_receipt"
    return None


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
