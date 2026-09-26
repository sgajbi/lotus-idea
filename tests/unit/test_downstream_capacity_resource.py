from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.application.downstream_capacity_resource import (
    DownstreamCapacityResourcePosture,
    SelectDownstreamCapacityResourceCommand,
    build_downstream_capacity_resource_artifact,
    select_downstream_capacity_resource,
)


ACCEPTED_AT = datetime(2026, 9, 25, 6, 0, tzinfo=UTC)


def _detail() -> dict[str, object]:
    return {
        "candidate": {
            "candidateId": "idea_low_income_001",
            "identity": {"materialVersion": 2, "evidenceVersion": 3},
        },
        "evidence": {"sourceCutPosture": "coherent"},
        "conversionIntents": [
            {
                "conversionIntentId": "conversion-current-001",
                "target": "advise_proposal",
                "requestedAtUtc": "2026-09-25T06:00:00Z",
                "acceptedAtUtc": "2026-09-25T06:00:01Z",
                "targetSourceAuthority": "lotus-advise",
                "boundary": "intent_only",
                "reasonCodes": ["review_approved_for_conversion", "income_attention"],
                "reviewId": "review-current-001",
                "reviewChannel": "workbench",
                "reviewPolicyVersion": "idea-human-review-v1",
                "authorityPolicyVersion": "idea-review-authority-v1",
                "presentationReceiptId": "presentation-current-001",
                "candidateMaterialVersion": 2,
                "candidateEvidenceVersion": 3,
                "grantsDownstreamAuthority": False,
            }
        ],
    }


class RecordingPort:
    def __init__(self, detail: dict[str, object] | None = None) -> None:
        self.detail = detail or _detail()
        self.calls: list[dict[str, str]] = []

    def fetch_candidate_detail(self, **kwargs: str) -> dict[str, object]:
        self.calls.append(kwargs)
        return self.detail

    def close(self) -> None:
        pass


def _command(
    *, accepted_not_before_utc: datetime | None = ACCEPTED_AT
) -> SelectDownstreamCapacityResourceCommand:
    return SelectDownstreamCapacityResourceCommand(
        candidate_id="idea_low_income_001",
        tenant_id="tenant-sg",
        book_id="BOOK_SG_BALANCED_DPM",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="CLIENT_SCOPE_PB_SG_GLOBAL_BAL_001",
        accepted_not_before_utc=accepted_not_before_utc,
    )


def test_selects_one_current_presentation_backed_conversion_intent() -> None:
    port = RecordingPort()

    result = select_downstream_capacity_resource(_command(), port=port)

    assert result.candidate_id == "idea_low_income_001"
    assert result.conversion_intent_id == "conversion-current-001"
    assert result.downstream_submission_path == (
        "/api/v1/conversion-intents/conversion-current-001/downstream-submissions"
    )
    assert result.resource_posture is DownstreamCapacityResourcePosture.FRESH_AUTHORIZED_SUBMISSION
    assert port.calls == [
        {
            "candidate_id": "idea_low_income_001",
            "tenant_id": "tenant-sg",
            "book_id": "BOOK_SG_BALANCED_DPM",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CLIENT_SCOPE_PB_SG_GLOBAL_BAL_001",
        }
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("candidate", "candidateId", "idea_low_income_other"), "candidate identity"),
        (("candidate", None), "missing candidate"),
        (("candidate", "identity", "materialVersion", 0), "positive integer"),
        (("evidence", "sourceCutPosture", "unknown"), "authoritative source cut"),
        (("conversionIntents", None), "missing conversion intents"),
        (("conversionIntents", 0, "acceptedAtUtc", 1), "exactly one"),
        (("conversionIntents", 0, "acceptedAtUtc", "not-a-date"), "exactly one"),
        (
            ("conversionIntents", 0, "acceptedAtUtc", "2026-09-25T06:00:01"),
            "exactly one",
        ),
        (("conversionIntents", 0, "reasonCodes", None), "exactly one"),
        (("conversionIntents", 0, "presentationReceiptId", None), "exactly one"),
        (("conversionIntents", 0, "reviewChannel", "operator"), "exactly one"),
        (("conversionIntents", 0, "candidateMaterialVersion", 1), "exactly one"),
        (("conversionIntents", 0, "candidateEvidenceVersion", 2), "exactly one"),
        (("conversionIntents", 0, "grantsDownstreamAuthority", True), "exactly one"),
        (("conversionIntents", 0, "reasonCodes", ["review_required"]), "exactly one"),
    ],
)
def test_rejects_stale_or_unproven_conversion_authority(
    mutation: tuple[object, ...], message: str
) -> None:
    detail = deepcopy(_detail())
    target: object = detail
    for key in mutation[:-2]:
        target = target[key]  # type: ignore[index]
    target[mutation[-2]] = mutation[-1]  # type: ignore[index]

    with pytest.raises(ValueError, match=message):
        select_downstream_capacity_resource(_command(), port=RecordingPort(detail))


def test_rejects_ambiguous_current_conversion_intents() -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    duplicate = deepcopy(intents[0])
    duplicate["conversionIntentId"] = "conversion-current-002"
    intents.append(duplicate)

    with pytest.raises(ValueError, match="exactly one"):
        select_downstream_capacity_resource(_command(), port=RecordingPort(detail))


def test_replays_exact_current_authority_without_a_run_timestamp_cutoff() -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["acceptedAtUtc"] = "2026-09-24T05:00:00Z"

    result = select_downstream_capacity_resource(
        _command(accepted_not_before_utc=None), port=RecordingPort(detail)
    )

    assert result.conversion_intent_id == "conversion-current-001"


def test_optional_timestamp_cutoff_rejects_an_older_current_intent() -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["acceptedAtUtc"] = "2026-09-25T05:59:59Z"

    with pytest.raises(ValueError, match="exactly one"):
        select_downstream_capacity_resource(_command(), port=RecordingPort(detail))


def test_selects_retained_accepted_submission_without_reauthorizing_stale_evidence() -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["candidateEvidenceVersion"] = 1
    detail["downstreamSubmissions"] = [_accepted_submission()]

    result = select_downstream_capacity_resource(_command(), port=RecordingPort(detail))

    assert result.resource_posture is DownstreamCapacityResourcePosture.RETAINED_ACCEPTED_SUBMISSION
    assert result.conversion_intent_id == "conversion-current-001"
    assert result.downstream_submission_path is None
    assert result.owner_source_event_version == 1


def test_prefers_retained_accepted_submission_over_a_duplicate_mutation() -> None:
    detail = _detail()
    detail["downstreamSubmissions"] = [_accepted_submission()]

    result = select_downstream_capacity_resource(_command(), port=RecordingPort(detail))

    assert result.resource_posture is DownstreamCapacityResourcePosture.RETAINED_ACCEPTED_SUBMISSION
    assert result.downstream_submission_path is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("submissionPosture", "reconciliation_required"), "exactly one current"),
        (("ownerReceipt", None), "exactly one current"),
        (("ownerReceipt", "ownerAuthority", "lotus-manage"), "exactly one current"),
        (("ownerReceipt", "sourceEventVersion", 0), "exactly one current"),
        (
            ("ownerReceipt", "sourceEvidenceFingerprint", "sha256:not-a-digest"),
            "exactly one current",
        ),
    ],
)
def test_rejects_unproven_retained_submission_when_intent_is_historical(
    mutation: tuple[object, ...], message: str
) -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["candidateEvidenceVersion"] = 1
    submission = _accepted_submission()
    target: object = submission
    for key in mutation[:-2]:
        target = target[key]  # type: ignore[index]
    target[mutation[-2]] = mutation[-1]  # type: ignore[index]
    detail["downstreamSubmissions"] = [submission]

    with pytest.raises(ValueError, match=message):
        select_downstream_capacity_resource(_command(), port=RecordingPort(detail))


def test_rejects_ambiguous_retained_accepted_submissions() -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    second_intent = deepcopy(intents[0])
    second_intent["conversionIntentId"] = "conversion-current-002"
    intents.append(second_intent)
    second_submission = _accepted_submission()
    second_submission["resourceId"] = "conversion-current-002"
    detail["downstreamSubmissions"] = [_accepted_submission(), second_submission]

    with pytest.raises(ValueError, match="ambiguous retained"):
        select_downstream_capacity_resource(_command(), port=RecordingPort(detail))


def test_rejects_retained_submission_with_future_candidate_evidence_version() -> None:
    detail = _detail()
    intents = detail["conversionIntents"]
    assert isinstance(intents, list)
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["candidateEvidenceVersion"] = 4
    detail["downstreamSubmissions"] = [_accepted_submission()]

    with pytest.raises(ValueError, match="exactly one current"):
        select_downstream_capacity_resource(_command(), port=RecordingPort(detail))


def test_resource_artifact_is_current_run_bound_and_non_certifying() -> None:
    result = select_downstream_capacity_resource(_command(), port=RecordingPort())

    artifact = build_downstream_capacity_resource_artifact(
        result,
        generated_at_utc=ACCEPTED_AT,
        commit_sha="a" * 40,
        branch="main",
        run_id="canonical-run-001",
    )

    assert artifact["schemaVersion"] == "lotus-idea.downstream-capacity-resource.v2"
    assert artifact["proofScope"] == "governed_downstream_resource_state"
    assert artifact["claimPosture"] == "selected_resource_state_not_capacity_evidence"
    assert artifact["resourcePosture"] == "fresh_authorized_submission"
    assert artifact["retainedAcceptedSubmissionVerified"] is False
    assert artifact["syntheticResource"] is False
    assert artifact["candidateId"] == "idea_low_income_001"
    assert artifact["productionCapacityCertified"] is False
    assert artifact["supportedFeaturePromoted"] is False


def test_retained_resource_artifact_has_no_mutation_path_or_private_receipt_identity() -> None:
    detail = _detail()
    detail["downstreamSubmissions"] = [_accepted_submission()]
    result = select_downstream_capacity_resource(_command(), port=RecordingPort(detail))

    artifact = build_downstream_capacity_resource_artifact(
        result,
        generated_at_utc=ACCEPTED_AT,
        commit_sha="a" * 40,
        branch="main",
        run_id="canonical-run-001",
    )

    assert artifact["resourcePosture"] == "retained_accepted_submission"
    assert artifact["retainedAcceptedSubmissionVerified"] is True
    assert artifact["ownerSourceAuthority"] == "lotus-advise"
    assert artifact["ownerSourceEventVersion"] == 1
    assert "downstreamSubmissionPath" not in artifact
    serialized = str(artifact)
    assert "owner-request-001" not in serialized
    assert "owner-realization-001" not in serialized
    assert "owner-work-001" not in serialized


def test_fresh_resource_artifact_requires_mutation_path() -> None:
    result = replace(
        select_downstream_capacity_resource(_command(), port=RecordingPort()),
        downstream_submission_path=None,
    )

    with pytest.raises(ValueError, match="requires a downstream submission path"):
        build_downstream_capacity_resource_artifact(
            result,
            generated_at_utc=ACCEPTED_AT,
            commit_sha="a" * 40,
            branch="main",
            run_id="canonical-run-001",
        )


def test_retained_resource_artifact_forbids_mutation_path() -> None:
    result = replace(
        select_downstream_capacity_resource(_command(), port=RecordingPort()),
        resource_posture=DownstreamCapacityResourcePosture.RETAINED_ACCEPTED_SUBMISSION,
        owner_source_event_version=1,
    )

    with pytest.raises(ValueError, match="forbids a downstream submission path"):
        build_downstream_capacity_resource_artifact(
            result,
            generated_at_utc=ACCEPTED_AT,
            commit_sha="a" * 40,
            branch="main",
            run_id="canonical-run-001",
        )


def test_retained_resource_artifact_requires_owner_version() -> None:
    result = replace(
        select_downstream_capacity_resource(_command(), port=RecordingPort()),
        resource_posture=DownstreamCapacityResourcePosture.RETAINED_ACCEPTED_SUBMISSION,
        downstream_submission_path=None,
        owner_source_event_version=None,
    )

    with pytest.raises(ValueError, match="requires an owner source event version"):
        build_downstream_capacity_resource_artifact(
            result,
            generated_at_utc=ACCEPTED_AT,
            commit_sha="a" * 40,
            branch="main",
            run_id="canonical-run-001",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"generated_at_utc": datetime(2026, 9, 25)}, "timezone-aware"),
        ({"commit_sha": " "}, "commit_sha"),
        ({"branch": " "}, "branch"),
        ({"run_id": " "}, "run_id"),
    ],
)
def test_resource_artifact_rejects_ambiguous_provenance(
    overrides: dict[str, object], message: str
) -> None:
    arguments: dict[str, object] = {
        "generated_at_utc": ACCEPTED_AT,
        "commit_sha": "a" * 40,
        "branch": "main",
        "run_id": "canonical-run-001",
    }
    arguments.update(overrides)

    with pytest.raises(ValueError, match=message):
        build_downstream_capacity_resource_artifact(
            select_downstream_capacity_resource(_command(), port=RecordingPort()),
            **arguments,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("candidate_id", " ", "candidate_id"),
        ("tenant_id", " ", "tenant_id"),
        ("accepted_not_before_utc", datetime(2026, 9, 25), "timezone-aware"),
    ],
)
def test_command_rejects_ambiguous_authority_inputs(
    field: str, value: object, message: str
) -> None:
    values = {
        "candidate_id": "idea_low_income_001",
        "tenant_id": "tenant-sg",
        "book_id": "BOOK_SG_BALANCED_DPM",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CLIENT_SCOPE_PB_SG_GLOBAL_BAL_001",
        "accepted_not_before_utc": ACCEPTED_AT,
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        SelectDownstreamCapacityResourceCommand(**values)  # type: ignore[arg-type]


def _accepted_submission() -> dict[str, object]:
    return {
        "resourceType": "conversion_intent",
        "resourceId": "conversion-current-001",
        "target": "advise_proposal",
        "sourceAuthority": "lotus-advise",
        "submissionPosture": "accepted_by_downstream",
        "submittedAtUtc": "2026-09-25T06:00:02Z",
        "updatedAtUtc": "2026-09-25T06:00:03Z",
        "attemptCount": 1,
        "operatorReconciliationRequired": False,
        "recordsDownstreamOutcome": False,
        "grantsDownstreamAuthority": False,
        "ownerReceipt": {
            "ownerAuthority": "lotus-advise",
            "ownerRequestId": "owner-request-001",
            "ownerRealizationId": "owner-realization-001",
            "ownerWorkId": "owner-work-001",
            "sourceEventVersion": 1,
            "sourceEvidenceFingerprint": f"sha256:{'a' * 64}",
        },
    }
