from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from app.api.downstream_realization import (
    DownstreamSubmissionApiResponse,
    DownstreamSubmissionResultResponse,
)
from app.api.examples.openapi import apply_named_response_examples, build_named_openapi_examples
from app.application.downstream_realization import (
    RealizeConversionIntentCommand,
    RealizeReportEvidencePackCommand,
    submit_conversion_intent_to_downstream,
    submit_report_evidence_pack_to_downstream,
)
from app.domain import (
    CandidatePersistenceRecord,
    ConversionTarget,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionClaimResult,
    DownstreamSubmissionMutationResult,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    GovernedConversionIntent,
    IdeaConversionIntent,
    IdeaLifecycleStatus,
    ReasonCode,
    ReviewAccessScope,
    SourceSystem,
    evaluate_downstream_submission_claim,
    finalize_downstream_submission,
)
from app.domain.report_evidence import (
    GovernedReportEvidencePack,
    ReportEvidencePackPurpose,
    ReportEvidenceSourceSummary,
)
from app.ports.downstream_realization import DownstreamRealizationOutcome


CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH = (
    "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"
)
REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH = (
    "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"
)
DOWNSTREAM_SUBMISSION_200_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "Downstream owner accepted the first submission",
    "rejected": "Downstream owner rejected the first submission without transferring authority",
    "acceptedReplayed": "Accepted submission replayed without a duplicate downstream call",
    "rejectedReplayed": "Rejected submission replayed without a duplicate downstream call",
}
DOWNSTREAM_SUBMISSION_202_SUCCESS_EXAMPLE_SUMMARIES = {
    "reconciliationRequired": "Uncertain downstream result is preserved for governed reconciliation",
}

_SUBMITTED_AT = datetime(2026, 6, 21, 10, 30, tzinfo=UTC)
_ACTOR = "advisor-001"


def build_conversion_downstream_submission_200_response_examples() -> dict[str, dict[str, Any]]:
    examples = _build_conversion_examples()
    return {name: examples[name] for name in DOWNSTREAM_SUBMISSION_200_SUCCESS_EXAMPLE_SUMMARIES}


def build_conversion_downstream_submission_202_response_examples() -> dict[str, dict[str, Any]]:
    examples = _build_conversion_examples()
    return {"reconciliationRequired": examples["reconciliationRequired"]}


def build_report_downstream_submission_200_response_examples() -> dict[str, dict[str, Any]]:
    examples = _build_report_examples()
    return {name: examples[name] for name in DOWNSTREAM_SUBMISSION_200_SUCCESS_EXAMPLE_SUMMARIES}


def build_report_downstream_submission_202_response_examples() -> dict[str, dict[str, Any]]:
    examples = _build_report_examples()
    return {"reconciliationRequired": examples["reconciliationRequired"]}


def apply_downstream_submission_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH,
            build_conversion_downstream_submission_200_response_examples(),
        ),
        (
            REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH,
            build_report_downstream_submission_200_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples, DOWNSTREAM_SUBMISSION_200_SUCCESS_EXAMPLE_SUMMARIES
            ),
        )
    for operation_path, examples in (
        (
            CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH,
            build_conversion_downstream_submission_202_response_examples(),
        ),
        (
            REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH,
            build_report_downstream_submission_202_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            response_status_code="202",
            examples=build_named_openapi_examples(
                examples, DOWNSTREAM_SUBMISSION_202_SUCCESS_EXAMPLE_SUMMARIES
            ),
        )
    return openapi_schema


def _build_conversion_examples() -> dict[str, dict[str, Any]]:
    accepted = _conversion_submission(
        target=ConversionTarget.ADVISE_PROPOSAL,
        idempotency_key="downstream-example-conversion-accepted",
        outcome=DownstreamRealizationOutcome.accepted_by_downstream(),
    )
    rejected = _conversion_submission(
        target=ConversionTarget.MANAGE_REVIEW,
        idempotency_key="downstream-example-conversion-rejected",
        outcome=DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected"),
    )
    accepted_replayed = _conversion_submission(
        target=ConversionTarget.ADVISE_PROPOSAL,
        idempotency_key="downstream-example-conversion-accepted-replayed",
        outcome=DownstreamRealizationOutcome.accepted_by_downstream(),
        replay=True,
    )
    rejected_replayed = _conversion_submission(
        target=ConversionTarget.MANAGE_REVIEW,
        idempotency_key="downstream-example-conversion-rejected-replayed",
        outcome=DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected"),
        replay=True,
    )
    reconciliation_required = _conversion_submission(
        target=ConversionTarget.ADVISE_PROPOSAL,
        idempotency_key="downstream-example-conversion-reconciliation",
        outcome=DownstreamRealizationOutcome.unknown("downstream_timeout"),
    )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "acceptedReplayed": accepted_replayed,
        "rejectedReplayed": rejected_replayed,
        "reconciliationRequired": reconciliation_required,
    }


def _build_report_examples() -> dict[str, dict[str, Any]]:
    accepted = _report_submission(
        idempotency_key="downstream-example-report-accepted",
        outcome=DownstreamRealizationOutcome.accepted_by_downstream(),
    )
    rejected = _report_submission(
        idempotency_key="downstream-example-report-rejected",
        outcome=DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected"),
    )
    accepted_replayed = _report_submission(
        idempotency_key="downstream-example-report-accepted-replayed",
        outcome=DownstreamRealizationOutcome.accepted_by_downstream(),
        replay=True,
    )
    rejected_replayed = _report_submission(
        idempotency_key="downstream-example-report-rejected-replayed",
        outcome=DownstreamRealizationOutcome.rejected_by_downstream("downstream_rejected"),
        replay=True,
    )
    reconciliation_required = _report_submission(
        idempotency_key="downstream-example-report-reconciliation",
        outcome=DownstreamRealizationOutcome.unknown("downstream_unavailable"),
    )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "acceptedReplayed": accepted_replayed,
        "rejectedReplayed": rejected_replayed,
        "reconciliationRequired": reconciliation_required,
    }


def _conversion_submission(
    *,
    target: ConversionTarget,
    idempotency_key: str,
    outcome: DownstreamRealizationOutcome,
    replay: bool = False,
) -> dict[str, Any]:
    intent = _conversion_intent(target)
    repository = _ExampleDownstreamSubmissionRepository(conversion_intent=intent)
    command = RealizeConversionIntentCommand(
        conversion_intent_id=intent.intent.conversion_intent_id,
        idempotency_key=idempotency_key,
        actor_subject=_ACTOR,
        correlation_id="corr-example",
        trace_id="trace-example",
        submitted_at_utc=_SUBMITTED_AT,
    )
    client = _ExampleConversionClient(outcome)
    result = submit_conversion_intent_to_downstream(
        command,
        repository=repository,
        advise_client=client if target is ConversionTarget.ADVISE_PROPOSAL else None,
        manage_client=client if target is ConversionTarget.MANAGE_REVIEW else None,
    )
    if replay:
        result = submit_conversion_intent_to_downstream(
            command,
            repository=repository,
            advise_client=client if target is ConversionTarget.ADVISE_PROPOSAL else None,
            manage_client=client if target is ConversionTarget.MANAGE_REVIEW else None,
        )
    return _serialize(result)


def _report_submission(
    *, idempotency_key: str, outcome: DownstreamRealizationOutcome, replay: bool = False
) -> dict[str, Any]:
    evidence_pack = _report_evidence_pack()
    repository = _ExampleDownstreamSubmissionRepository(report_evidence_pack=evidence_pack)
    command = RealizeReportEvidencePackCommand(
        report_evidence_pack_id=evidence_pack.report_evidence_pack_id,
        idempotency_key=idempotency_key,
        actor_subject=_ACTOR,
        correlation_id="corr-example",
        trace_id="trace-example",
        submitted_at_utc=_SUBMITTED_AT,
    )
    client = _ExampleReportClient(outcome)
    result = submit_report_evidence_pack_to_downstream(
        command, repository=repository, report_client=client
    )
    if replay:
        result = submit_report_evidence_pack_to_downstream(
            command, repository=repository, report_client=client
        )
    return _serialize(result)


def _serialize(result: Any) -> dict[str, Any]:
    return DownstreamSubmissionApiResponse(
        downstreamSubmission=DownstreamSubmissionResultResponse.from_domain(result),
        durableStorageBacked=False,
        supportedFeaturePromoted=False,
    ).model_dump(mode="json", by_alias=True)


def _conversion_intent(target: ConversionTarget) -> GovernedConversionIntent:
    source_authority = (
        SourceSystem.LOTUS_ADVISE
        if target is ConversionTarget.ADVISE_PROPOSAL
        else SourceSystem.LOTUS_MANAGE
    )
    return GovernedConversionIntent(
        intent=IdeaConversionIntent(
            conversion_intent_id=f"conversion-example-{target.value}",
            candidate_id="idea_example",
            target=target,
            source_status=IdeaLifecycleStatus.APPROVED,
            requested_at_utc=_SUBMITTED_AT,
        ),
        evidence_packet_id="iep_example",
        evidence_content_hash="sha256:example-evidence",
        source_signal_ids=("signal_example",),
        actor_subject=_ACTOR,
        idempotency_key="conversion-example",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        target_source_authority=source_authority,
    )


def _report_evidence_pack() -> GovernedReportEvidencePack:
    return GovernedReportEvidencePack(
        report_evidence_pack_id="report-pack-example",
        conversion_intent_id="conversion-example-report",
        candidate_id="idea_example",
        evidence_packet_id="iep_example",
        evidence_content_hash="sha256:example-evidence",
        source_signal_ids=("signal_example",),
        source_summaries=(
            ReportEvidenceSourceSummary(
                product_id="lotus-core:PortfolioStateSnapshot:v1",
                source_system=SourceSystem.LOTUS_CORE,
                product_version="v1",
                as_of_date="2026-06-21",
                generated_at_utc=_SUBMITTED_AT,
                content_hash="sha256:example-source",
                data_quality_status="complete",
                freshness="current",
            ),
        ),
        purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
        actor_subject=_ACTOR,
        idempotency_key="report-pack-example",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=_SUBMITTED_AT,
        retention_policy_ref="lotus-report:idea-evidence-retention:v1",
    )


@dataclass(frozen=True)
class _ExampleCandidate:
    access_scope: ReviewAccessScope


@dataclass(frozen=True)
class _ExampleReportEvidencePackCandidateRecord:
    candidate: _ExampleCandidate


class _ExampleDownstreamSubmissionRepository:
    def __init__(
        self,
        *,
        conversion_intent: GovernedConversionIntent | None = None,
        report_evidence_pack: GovernedReportEvidencePack | None = None,
    ) -> None:
        self._conversion_intent = conversion_intent
        self._report_evidence_pack = report_evidence_pack
        self._report_evidence_pack_candidate: CandidatePersistenceRecord | None = (
            cast(
                CandidatePersistenceRecord,
                _ExampleReportEvidencePackCandidateRecord(
                    candidate=_ExampleCandidate(
                        access_scope=ReviewAccessScope(
                            tenant_id="tenant-sg",
                            book_id="book-private-bank-sg",
                            portfolio_id="PB_SG_GLOBAL_BAL_001",
                            client_id="client-example",
                        )
                    )
                ),
            )
            if report_evidence_pack is not None
            else None
        )
        self._records: dict[str, DownstreamSubmissionRecord] = {}

    def conversion_intent_by_id(self, conversion_intent_id: str) -> GovernedConversionIntent | None:
        if (
            self._conversion_intent
            and self._conversion_intent.intent.conversion_intent_id == conversion_intent_id
        ):
            return self._conversion_intent
        return None

    def candidate_record_for_report_evidence_pack(
        self, report_evidence_pack_id: str
    ) -> CandidatePersistenceRecord | None:
        if (
            self._report_evidence_pack
            and self._report_evidence_pack.report_evidence_pack_id == report_evidence_pack_id
        ):
            return self._report_evidence_pack_candidate
        return None

    def report_evidence_pack_by_id(
        self, report_evidence_pack_id: str
    ) -> GovernedReportEvidencePack | None:
        if (
            self._report_evidence_pack
            and self._report_evidence_pack.report_evidence_pack_id == report_evidence_pack_id
        ):
            return self._report_evidence_pack
        return None

    def downstream_submission_by_idempotency_key(
        self, idempotency_key: str
    ) -> DownstreamSubmissionRecord | None:
        return self._records.get(idempotency_key)

    def claim_downstream_submission(
        self, record: DownstreamSubmissionRecord
    ) -> DownstreamSubmissionClaimResult:
        existing = self._records.get(record.idempotency_key)
        decision = evaluate_downstream_submission_claim(
            existing, request_fingerprint=record.request_fingerprint
        )
        if decision is DownstreamSubmissionClaimDecision.ACCEPTED:
            self._records[record.idempotency_key] = record
            return DownstreamSubmissionClaimResult(decision=decision, record=record)
        return DownstreamSubmissionClaimResult(decision=decision, record=existing)

    def finalize_downstream_submission(
        self,
        *,
        idempotency_key: str,
        lease_owner: str,
        lease_attempt_id: str,
        posture: DownstreamSubmissionPosture,
        finalized_at_utc: datetime,
        failure_reason: str | None = None,
    ) -> DownstreamSubmissionMutationResult:
        record = self._records[idempotency_key]
        result = finalize_downstream_submission(
            record,
            lease_owner=lease_owner,
            lease_attempt_id=lease_attempt_id,
            posture=posture,
            finalized_at_utc=finalized_at_utc,
            failure_reason=failure_reason,
        )
        if result.record is not None:
            self._records[record.idempotency_key] = result.record
        return result

    def downstream_submissions_requiring_reconciliation(
        self, *, limit: int = 100
    ) -> tuple[DownstreamSubmissionRecord, ...]:
        return tuple(
            record
            for record in self._records.values()
            if record.status
            in {
                DownstreamSubmissionPosture.IN_FLIGHT,
                DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
                DownstreamSubmissionPosture.QUARANTINED,
            }
        )[:limit]

    def downstream_submission_by_support_reference(
        self, support_reference: str
    ) -> DownstreamSubmissionRecord | None:
        return next(
            (
                record
                for record in self._records.values()
                if record.support_reference == support_reference
            ),
            None,
        )

    def reconcile_downstream_submission(
        self,
        *,
        support_reference: str,
        resolution: DownstreamSubmissionResolution,
        actor_subject: str,
        reason: str,
        change_reference: str,
        reconciled_at_utc: datetime,
    ) -> DownstreamSubmissionMutationResult:
        raise AssertionError("example submissions do not invoke operator reconciliation")


class _ExampleConversionClient:
    def __init__(self, outcome: DownstreamRealizationOutcome) -> None:
        self._outcome = outcome

    def submit_proposal_intent(self, *_: Any, **__: Any) -> DownstreamRealizationOutcome:
        return self._outcome

    def submit_action_intent(self, *_: Any, **__: Any) -> DownstreamRealizationOutcome:
        return self._outcome


class _ExampleReportClient:
    def __init__(self, outcome: DownstreamRealizationOutcome) -> None:
        self._outcome = outcome

    def submit_report_evidence_pack_request(
        self, *_: Any, **__: Any
    ) -> DownstreamRealizationOutcome:
        return self._outcome


__all__ = [
    "CONVERSION_DOWNSTREAM_SUBMISSION_OPERATION_PATH",
    "DOWNSTREAM_SUBMISSION_200_SUCCESS_EXAMPLE_SUMMARIES",
    "DOWNSTREAM_SUBMISSION_202_SUCCESS_EXAMPLE_SUMMARIES",
    "REPORT_DOWNSTREAM_SUBMISSION_OPERATION_PATH",
    "apply_downstream_submission_openapi_examples",
    "build_conversion_downstream_submission_200_response_examples",
    "build_conversion_downstream_submission_202_response_examples",
    "build_report_downstream_submission_200_response_examples",
    "build_report_downstream_submission_202_response_examples",
]
