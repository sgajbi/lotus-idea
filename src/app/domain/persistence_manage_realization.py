from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.downstream_submission import (
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
)
from app.domain.ideas import ConversionTarget, SourceSystem
from app.domain.manage_realization import (
    ManageActionRealizationHistory,
    ManageRealizationHistoryMutationDecision,
    ManageRealizationHistoryMutationResult,
    evaluate_manage_realization_history_mutation,
)


class InMemoryManageRealizationRepositoryMixin:
    _manage_realization_histories: dict[str, ManageActionRealizationHistory]

    if TYPE_CHECKING:

        def downstream_submission_by_support_reference(
            self,
            support_reference: str,
        ) -> DownstreamSubmissionRecord | None: ...

    def manage_realization_history_by_support_reference(
        self,
        support_reference: str,
    ) -> ManageActionRealizationHistory | None:
        _require_text(support_reference, "support_reference")
        return self._manage_realization_histories.get(support_reference)

    def persist_manage_realization_history(
        self,
        *,
        support_reference: str,
        history: ManageActionRealizationHistory,
    ) -> ManageRealizationHistoryMutationResult:
        submission = self.downstream_submission_by_support_reference(support_reference)
        if submission is None:
            return ManageRealizationHistoryMutationResult(
                decision=ManageRealizationHistoryMutationDecision.NOT_FOUND,
                history=None,
                blocker="downstream_submission_not_found",
            )
        blocker = manage_realization_submission_blocker(submission, history)
        if blocker is not None:
            return ManageRealizationHistoryMutationResult(
                decision=ManageRealizationHistoryMutationDecision.CONFLICT,
                history=self._manage_realization_histories.get(support_reference),
                blocker=blocker,
            )
        existing = self._manage_realization_histories.get(support_reference)
        decision = evaluate_manage_realization_history_mutation(existing, history)
        appended_event_count = 0
        if decision is ManageRealizationHistoryMutationDecision.ACCEPTED:
            appended_event_count = len(history.events) - (
                len(existing.events) if existing is not None else 0
            )
            self._manage_realization_histories[support_reference] = history
        return ManageRealizationHistoryMutationResult(
            decision=decision,
            history=(
                history
                if decision is not ManageRealizationHistoryMutationDecision.CONFLICT
                else existing
            ),
            blocker=(
                "manage_realization_history_conflict"
                if decision is ManageRealizationHistoryMutationDecision.CONFLICT
                else None
            ),
            appended_event_count=appended_event_count,
        )


def manage_realization_submission_blocker(
    submission: DownstreamSubmissionRecord,
    history: ManageActionRealizationHistory,
) -> str | None:
    if submission.resource_type is not DownstreamSubmissionResourceType.CONVERSION_INTENT:
        return "manage_realization_requires_conversion_intent_submission"
    if submission.target is not ConversionTarget.MANAGE_REVIEW:
        return "manage_realization_requires_manage_target"
    if submission.source_authority is not SourceSystem.LOTUS_MANAGE:
        return "manage_realization_requires_manage_authority"
    if submission.status not in {
        DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
    }:
        return "manage_realization_requires_terminal_owner_submission"
    receipt = submission.owner_receipt
    if receipt is None:
        return "manage_realization_owner_receipt_missing"
    if (
        receipt.owner_authority is not SourceSystem.LOTUS_MANAGE
        or receipt.source_event_version is None
        or receipt.owner_request_id != history.intake_id
        or receipt.owner_realization_id != history.management_action_id
        or receipt.owner_work_id != history.management_action_id
        or submission.resource_id != history.conversion_intent_id
    ):
        return "manage_realization_owner_receipt_conflict"
    if receipt.source_event_version > history.source_event_version:
        return "manage_realization_history_regressed_below_receipt"
    return None


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
