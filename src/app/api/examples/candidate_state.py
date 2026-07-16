from __future__ import annotations

from typing import Any

from app.api.candidate_evidence_replay import CandidateEvidenceReplayResponse
from app.api.candidate_lifecycle import CandidateLifecycleTransitionResponse
from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)


CANDIDATE_LIFECYCLE_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions"
CANDIDATE_EVIDENCE_REPLAY_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/evidence-replay"
CANDIDATE_LIFECYCLE_SUCCESS_EXAMPLE_SUMMARIES = {
    "accepted": "New candidate lifecycle transition accepted and persisted",
    "replayed": "Existing lifecycle transition replayed without duplicate mutation",
}
CANDIDATE_EVIDENCE_REPLAY_SUCCESS_EXAMPLE_SUMMARIES = {
    "matched": "Current source references match the persisted evidence hash",
    "hashMismatch": "Current source references produce a different evidence hash",
    "staleSource": "Current source references contain stale evidence",
    "expired": "Candidate lifecycle no longer permits evidence replay comparison",
}


def build_candidate_lifecycle_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "accepted": _validated_candidate_lifecycle_response(
            {
                "transition": {
                    "transitionId": "lifecycle-ready-for-review-001",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "ready_for_review",
                    "changedAtUtc": "2026-06-21T10:04:00Z",
                    "reasonCodes": ["review_required"],
                    "grantsDownstreamAuthority": False,
                },
                "persistence": {
                    "decision": "accepted",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "ready_for_review",
                    "auditEventType": "idea.lifecycle.transitioned",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
        "replayed": _validated_candidate_lifecycle_response(
            {
                "transition": None,
                "persistence": {
                    "decision": "replayed",
                    "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                    "lifecycleStatus": "ready_for_review",
                    "auditEventType": "idea.lifecycle.transitioned",
                },
                "durableStorageBacked": False,
                "supportedFeaturePromoted": False,
            }
        ),
    }


def build_candidate_evidence_replay_response_examples() -> dict[str, dict[str, Any]]:
    base = {
        "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
        "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
        "recordedEvidenceHash": "sha256:evidence-lineage",
        "sourceRefCount": 1,
        "durableStorageBacked": False,
        "supportedFeaturePromoted": False,
        "grantsDownstreamAuthority": False,
    }
    return {
        "matched": _validated_candidate_evidence_replay_response(
            {
                **base,
                "replayStatus": "matched",
                "currentEvidenceHash": "sha256:evidence-lineage",
            }
        ),
        "hashMismatch": _validated_candidate_evidence_replay_response(
            {
                **base,
                "replayStatus": "hash_mismatch",
                "currentEvidenceHash": "sha256:changed-evidence-lineage",
            }
        ),
        "staleSource": _validated_candidate_evidence_replay_response(
            {
                **base,
                "replayStatus": "stale_source",
                "currentEvidenceHash": None,
            }
        ),
        "expired": _validated_candidate_evidence_replay_response(
            {
                **base,
                "replayStatus": "expired",
                "currentEvidenceHash": None,
            }
        ),
    }


def apply_candidate_state_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    apply_named_response_examples(
        openapi_schema,
        operation_path=CANDIDATE_LIFECYCLE_OPERATION_PATH,
        examples=build_named_openapi_examples(
            build_candidate_lifecycle_response_examples(),
            CANDIDATE_LIFECYCLE_SUCCESS_EXAMPLE_SUMMARIES,
        ),
    )
    apply_named_response_examples(
        openapi_schema,
        operation_path=CANDIDATE_EVIDENCE_REPLAY_OPERATION_PATH,
        examples=build_named_openapi_examples(
            build_candidate_evidence_replay_response_examples(),
            CANDIDATE_EVIDENCE_REPLAY_SUCCESS_EXAMPLE_SUMMARIES,
        ),
    )
    return openapi_schema


def _validated_candidate_lifecycle_response(payload: dict[str, Any]) -> dict[str, Any]:
    return CandidateLifecycleTransitionResponse.model_validate(payload).model_dump(
        mode="json",
        by_alias=True,
    )


def _validated_candidate_evidence_replay_response(payload: dict[str, Any]) -> dict[str, Any]:
    return CandidateEvidenceReplayResponse.model_validate(payload).model_dump(
        mode="json",
        by_alias=True,
    )


__all__ = [
    "CANDIDATE_EVIDENCE_REPLAY_OPERATION_PATH",
    "CANDIDATE_EVIDENCE_REPLAY_SUCCESS_EXAMPLE_SUMMARIES",
    "CANDIDATE_LIFECYCLE_OPERATION_PATH",
    "CANDIDATE_LIFECYCLE_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_candidate_state_openapi_examples",
    "build_candidate_evidence_replay_response_examples",
    "build_candidate_lifecycle_response_examples",
]
