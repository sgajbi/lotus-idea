from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    RealizeConversionIntentCommand,
    submit_conversion_intent_to_downstream,
)
from app.application.manage_realization_reconciliation import (
    ManageRealizationReconciliationStatus,
    ReconcileManageRealizationCommand,
    reconcile_manage_realization_history,
)
from app.domain import (
    ConversionTarget,
    ManageActionRealizationHistory,
    ReviewAccessScope,
    SourceSystem,
)
from app.infrastructure.postgres_repository import PostgresConnection, PostgresIdeaRepository
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationNotObserved,
    DownstreamRealizationOutcome,
)
from tests.unit.test_downstream_realization_application import (
    AUTHORIZED_SCOPE_FILTER,
    CapturingManageClient,
    repository_with_conversion,
)
from tests.unit.test_manage_realization_reconciliation import RECORDED_AT, _history


@dataclass
class _CountingManageReader:
    history: ManageActionRealizationHistory
    recovery_calls: int = 0
    history_calls: int = 0
    acceptance_observed: bool = True

    def load_realization_by_conversion_intent(
        self,
        *,
        conversion_intent_id: str,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> ManageActionRealizationHistory:
        self.recovery_calls += 1
        assert conversion_intent_id == "conversion-manage_review-001"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        if not self.acceptance_observed:
            raise DownstreamRealizationNotObserved(
                "Manage has no realization for this conversion intent"
            )
        return self.history

    def load_action_realization(
        self,
        *,
        intake_id: str,
        access_scope: ReviewAccessScope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> ManageActionRealizationHistory:
        self.history_calls += 1
        assert intake_id == "iai_001"
        assert access_scope.portfolio_id == "PB_SG_GLOBAL_BAL_001"
        return self.history


def test_postgres_recovers_manage_acceptance_after_finalize_failure_and_restart(
    postgres_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_repository = repository_with_conversion(ConversionTarget.MANAGE_REVIEW)
    accepted_client = CapturingManageClient(
        DownstreamRealizationOutcome.accepted_by_downstream(
            DownstreamOwnerReceipt(
                owner_authority=SourceSystem.LOTUS_MANAGE,
                owner_request_id="iai_001",
                owner_realization_id="ima_001",
                owner_work_id="ima_001",
                source_event_version=1,
                source_evidence_fingerprint="sha256:aabbccddeeff",
            )
        )
    )
    submission_command = RealizeConversionIntentCommand(
        conversion_intent_id="conversion-manage_review-001",
        idempotency_key="postgres-manage-finalize-failure-001",
        actor_subject="advisor-redacted",
        access_scope_filter=AUTHORIZED_SCOPE_FILTER,
        submitted_at_utc=RECORDED_AT,
    )

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        repository.replace_snapshot(source_repository.snapshot())

        def fail_finalize(**_: object) -> None:
            raise RuntimeError("simulated Idea commit failure after Manage acceptance")

        monkeypatch.setattr(repository, "finalize_downstream_submission", fail_finalize)
        submitted = submit_conversion_intent_to_downstream(
            submission_command,
            repository=repository,
            advise_client=None,
            manage_client=accepted_client,
        )
        assert submitted.status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
        assert submitted.support_reference is not None
        support_reference = submitted.support_reference
        pending = repository.downstream_submission_by_support_reference(support_reference)
        assert pending is not None
        assert pending.status.value == "in_flight"
        assert pending.owner_receipt is None
        assert pending.lease_expires_at_utc is not None
        accepted_at_utc = pending.lease_expires_at_utc

    reader = _CountingManageReader(_history(version=2), acceptance_observed=False)
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        not_observed = reconcile_manage_realization_history(
            ReconcileManageRealizationCommand(
                support_reference=support_reference,
                actor_subject="operator-redacted",
                access_scope_filter=AUTHORIZED_SCOPE_FILTER,
                accepted_at_utc=accepted_at_utc,
            ),
            repository=restarted,
            manage_reader=reader,
        )
        unchanged = restarted.downstream_submission_by_support_reference(support_reference)
        assert (
            not_observed.status
            is ManageRealizationReconciliationStatus.OWNER_ACCEPTANCE_NOT_OBSERVED
        )
        assert unchanged == pending

    reader.acceptance_observed = True
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted = PostgresIdeaRepository(cast(PostgresConnection, connection))
        recovered = reconcile_manage_realization_history(
            ReconcileManageRealizationCommand(
                support_reference=support_reference,
                actor_subject="operator-redacted",
                access_scope_filter=AUTHORIZED_SCOPE_FILTER,
                accepted_at_utc=accepted_at_utc,
            ),
            repository=restarted,
            manage_reader=reader,
        )
        assert recovered.status is ManageRealizationReconciliationStatus.ACCEPTED

    replay_client = CapturingManageClient(
        DownstreamRealizationOutcome.rejected_by_downstream("must-not-call")
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        restarted_again = PostgresIdeaRepository(cast(PostgresConnection, connection))
        replayed = submit_conversion_intent_to_downstream(
            submission_command,
            repository=restarted_again,
            advise_client=None,
            manage_client=replay_client,
        )
        persisted = restarted_again.downstream_submission_by_support_reference(support_reference)
        history = restarted_again.manage_realization_history_by_support_reference(support_reference)

        assert replayed.status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
        assert replayed.idempotency_replayed is True
        assert replay_client.submitted == ()
        assert persisted is not None
        assert persisted.attempt_count == 1
        assert persisted.updated_at_utc == accepted_at_utc
        assert [entry.action.value for entry in persisted.audit_history] == [
            "claimed",
            "reconciled",
        ]
        assert persisted.audit_history[-1].occurred_at_utc == accepted_at_utc
        assert persisted.owner_receipt is not None
        assert persisted.owner_receipt.source_evidence_fingerprint == "sha256:aabbccddeeff"
        assert history == _history(version=2)

    assert len(accepted_client.submitted) == 1
    assert reader.recovery_calls == 2
    assert reader.history_calls == 0
