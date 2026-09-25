from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from app.ports.downstream_capacity_resource import DownstreamCapacityResourcePort


ACCEPTED_SOURCE_CUT_POSTURES = frozenset({"coherent", "coherent_with_declared_tolerance"})
EXPECTED_AUTHORITY_POLICY_VERSION = "idea-review-authority-v1"
EXPECTED_REVIEW_POLICY_VERSION = "idea-human-review-v1"


@dataclass(frozen=True)
class SelectDownstreamCapacityResourceCommand:
    candidate_id: str
    tenant_id: str
    book_id: str
    portfolio_id: str
    client_id: str
    accepted_not_before_utc: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("candidate_id", "tenant_id", "book_id", "portfolio_id", "client_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.accepted_not_before_utc is not None and (
            self.accepted_not_before_utc.tzinfo is None
            or self.accepted_not_before_utc.utcoffset() is None
        ):
            raise ValueError("accepted_not_before_utc must be timezone-aware")


@dataclass(frozen=True)
class DownstreamCapacityResourceResult:
    candidate_id: str
    conversion_intent_id: str
    downstream_submission_path: str
    accepted_at_utc: datetime


def select_downstream_capacity_resource(
    command: SelectDownstreamCapacityResourceCommand,
    *,
    port: DownstreamCapacityResourcePort,
) -> DownstreamCapacityResourceResult:
    detail = port.fetch_candidate_detail(
        candidate_id=command.candidate_id,
        tenant_id=command.tenant_id,
        book_id=command.book_id,
        portfolio_id=command.portfolio_id,
        client_id=command.client_id,
    )
    candidate = _mapping(detail.get("candidate"), "candidate")
    if candidate.get("candidateId") != command.candidate_id:
        raise ValueError("capacity resource candidate identity does not match the request")
    identity = _mapping(candidate.get("identity"), "candidate identity")
    material_version = _positive_int(identity.get("materialVersion"), "materialVersion")
    evidence_version = _positive_int(identity.get("evidenceVersion"), "evidenceVersion")
    evidence = _mapping(detail.get("evidence"), "candidate evidence")
    if evidence.get("sourceCutPosture") not in ACCEPTED_SOURCE_CUT_POSTURES:
        raise ValueError("capacity resource candidate does not have an authoritative source cut")

    intents = detail.get("conversionIntents")
    if not isinstance(intents, list):
        raise ValueError("capacity resource candidate response is missing conversion intents")
    eligible = [
        intent
        for item in intents
        if isinstance(item, Mapping)
        and (
            intent := _eligible_intent(
                item,
                material_version=material_version,
                evidence_version=evidence_version,
                accepted_not_before_utc=command.accepted_not_before_utc,
            )
        )
        is not None
    ]
    if len(eligible) != 1:
        raise ValueError(
            "capacity resource requires exactly one current, presentation-backed conversion intent"
        )
    intent = eligible[0]
    conversion_intent_id = cast(str, intent["conversionIntentId"])
    accepted_at_utc = _aware_datetime(intent.get("acceptedAtUtc"), "acceptedAtUtc")
    return DownstreamCapacityResourceResult(
        candidate_id=command.candidate_id,
        conversion_intent_id=conversion_intent_id,
        downstream_submission_path=(
            f"/api/v1/conversion-intents/{conversion_intent_id}/downstream-submissions"
        ),
        accepted_at_utc=accepted_at_utc,
    )


def build_downstream_capacity_resource_artifact(
    result: DownstreamCapacityResourceResult,
    *,
    generated_at_utc: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
) -> dict[str, object]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    for name, value in (("commit_sha", commit_sha), ("branch", branch), ("run_id", run_id)):
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    return {
        "schemaVersion": "lotus-idea.downstream-capacity-resource.v1",
        "repository": "lotus-idea",
        "proofScope": "current_authoritative_downstream_resource",
        "claimPosture": "selected_conversion_intent_not_capacity_evidence",
        "generatedAtUtc": _utc_text(generated_at_utc),
        "commitSha": commit_sha,
        "branch": branch,
        "runId": run_id,
        "syntheticResource": False,
        "candidateId": result.candidate_id,
        "conversionIntentId": result.conversion_intent_id,
        "conversionIntentAcceptedAtUtc": _utc_text(result.accepted_at_utc),
        "downstreamSubmissionPath": result.downstream_submission_path,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def _eligible_intent(
    intent: Mapping[str, Any],
    *,
    material_version: int,
    evidence_version: int,
    accepted_not_before_utc: datetime | None,
) -> Mapping[str, Any] | None:
    accepted_at_raw = intent.get("acceptedAtUtc")
    try:
        accepted_at_utc = _aware_datetime(accepted_at_raw, "acceptedAtUtc")
    except ValueError:
        return None
    reason_codes = intent.get("reasonCodes")
    if not isinstance(reason_codes, list):
        return None
    required_text = (
        intent.get("target") == "advise_proposal"
        and intent.get("targetSourceAuthority") == "lotus-advise"
        and intent.get("boundary") == "intent_only"
        and intent.get("reviewChannel") == "workbench"
        and intent.get("reviewPolicyVersion") == EXPECTED_REVIEW_POLICY_VERSION
        and intent.get("authorityPolicyVersion") == EXPECTED_AUTHORITY_POLICY_VERSION
        and _is_non_blank_text(intent.get("reviewId"))
        and _is_non_blank_text(intent.get("presentationReceiptId"))
        and _is_non_blank_text(intent.get("conversionIntentId"))
        and intent.get("grantsDownstreamAuthority") is False
    )
    if not required_text:
        return None
    if intent.get("candidateMaterialVersion") != material_version:
        return None
    if intent.get("candidateEvidenceVersion") != evidence_version:
        return None
    if "review_approved_for_conversion" not in reason_codes:
        return None
    if accepted_not_before_utc is not None and accepted_at_utc < accepted_not_before_utc.astimezone(
        UTC
    ):
        return None
    return intent


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"capacity resource response is missing {name}")
    return value


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"capacity resource {name} must be a positive integer")
    return value


def _is_non_blank_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _aware_datetime(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"capacity resource {name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"capacity resource {name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"capacity resource {name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
