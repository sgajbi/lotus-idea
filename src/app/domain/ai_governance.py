from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Mapping

from app.domain.audit import AuditEvent
from app.domain.ai_action_policy import (
    AI_ACTION_POLICY_VERSION,
    AIActionPolicyReason,
    AIProposedActionType as AIProposedActionType,
    evaluate_ai_action_policy,
)
from app.domain.ai_output_integrity import AIOutputIntegrity, build_ai_output_integrity
from app.domain.ai_execution_provenance import AIExecutionProvenancePosture
from app.domain.ai_explanation import (
    AI_CLAIM_GROUNDING_POLICY_VERSION,
    render_grounded_claim_narrative,
)
from app.domain.ai_metadata_policy import validate_ai_metadata_envelope
from app.domain.ideas import (
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SourceSystem,
    UnsupportedEvidenceReason,
)


@dataclass(frozen=True)
class GovernedAIWorkflowPackContract:
    request_workflow_pack_id: str
    proof_workflow_pack_id: str
    workflow_pack_version: str
    evaluation_ref: str
    allowed_purposes: frozenset["AIWorkflowPurpose"]
    workflow_authority_owner: str
    ai_capability_owner: str


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class AIWorkflowPurpose(StrEnum):
    MISSING_EVIDENCE_CHECK = "missing_evidence_check"
    UNSUPPORTED_CLAIM_VERIFICATION = "unsupported_claim_verification"
    ADVISOR_RATIONALE_DRAFT = "advisor_rationale_draft"
    MEETING_PREPARATION_DRAFT = "meeting_preparation_draft"


class AIExplanationPosture(StrEnum):
    READY_FOR_ADVISOR_REVIEW = "ready_for_advisor_review"
    FALLBACK_USED = "fallback_used"
    BLOCKED_UNSUPPORTED_EVIDENCE = "blocked_unsupported_evidence"
    BLOCKED_UNSUPPORTED_CLAIM = "blocked_unsupported_claim"
    BLOCKED_FORBIDDEN_ACTION = "blocked_forbidden_action"
    BLOCKED_REDACTION = "blocked_redaction"


class AIVerifierOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED_UNSUPPORTED_CLAIM = "failed_unsupported_claim"
    FAILED_FORBIDDEN_ACTION = "failed_forbidden_action"
    FAILED_ACTION_CONTENT = "failed_action_content"


class AIFallbackReason(StrEnum):
    AI_UNAVAILABLE = "ai_unavailable"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    REDACTION_REQUIRED = "redaction_required"
    WORKFLOW_NOT_APPROVED = "workflow_not_approved"


class InvalidAIExplanationRequest(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidAIWorkflowOutput(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidAIWorkflowPack(InvalidAIExplanationRequest):
    def __init__(self) -> None:
        super().__init__("AI workflow pack is not registered for idea explanation evaluation")


GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK = GovernedAIWorkflowPackContract(
    request_workflow_pack_id="lotus-ai:idea-explanation:v1",
    proof_workflow_pack_id="idea_explanation.pack@v1",
    workflow_pack_version="v1",
    evaluation_ref="lotus-ai:governed-verifier:v1",
    allowed_purposes=frozenset(
        {
            AIWorkflowPurpose.MISSING_EVIDENCE_CHECK,
            AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
            AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT,
            AIWorkflowPurpose.MEETING_PREPARATION_DRAFT,
        }
    ),
    workflow_authority_owner="lotus-idea",
    ai_capability_owner="lotus-ai",
)


@dataclass(frozen=True)
class AIWorkflowPackRef:
    workflow_pack_id: str
    workflow_pack_version: str
    purpose: AIWorkflowPurpose
    evaluation_ref: str

    def __post_init__(self) -> None:
        _require_text(self.workflow_pack_id, "workflow_pack_id")
        _require_text(self.workflow_pack_version, "workflow_pack_version")
        _require_text(self.evaluation_ref, "evaluation_ref")


@dataclass(frozen=True)
class RedactedSourceRef:
    product_id: str
    source_system: SourceSystem
    product_version: str
    as_of_date: date
    freshness: EvidenceFreshness
    data_quality_status: str

    def __post_init__(self) -> None:
        _require_text(self.product_id, "product_id")
        _require_text(self.product_version, "product_version")
        _require_text(self.data_quality_status, "data_quality_status")


@dataclass(frozen=True)
class RedactedIdeaEvidence:
    candidate_id: str
    family: OpportunityFamily
    lifecycle_status: IdeaLifecycleStatus
    review_posture: ReviewPosture
    evidence_packet_id: str
    evidence_content_hash: str
    supportability: EvidenceSupportability
    source_refs: tuple[RedactedSourceRef, ...]
    reason_codes: tuple[ReasonCode, ...]
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...]
    score_policy_version: str | None
    score: Decimal | None
    source_signal_count: int

    @property
    def source_product_ids(self) -> frozenset[str]:
        return frozenset(source_ref.product_id for source_ref in self.source_refs)

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.evidence_packet_id, "evidence_packet_id")
        _require_text(self.evidence_content_hash, "evidence_content_hash")
        if not self.source_refs:
            raise ValueError("source_refs is required")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if self.source_signal_count <= 0:
            raise ValueError("source_signal_count must be positive")
        if self.score_policy_version is not None:
            _require_text(self.score_policy_version, "score_policy_version")
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "unsupported_reasons", tuple(self.unsupported_reasons))

    @classmethod
    def from_candidate(cls, candidate: IdeaCandidate) -> RedactedIdeaEvidence:
        return cls(
            candidate_id=candidate.candidate_id,
            family=candidate.family,
            lifecycle_status=candidate.lifecycle_status,
            review_posture=candidate.review_posture,
            evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
            evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
            supportability=candidate.evidence_packet.supportability,
            source_refs=tuple(
                RedactedSourceRef(
                    product_id=source_ref.product_id,
                    source_system=source_ref.source_system,
                    product_version=source_ref.product_version,
                    as_of_date=source_ref.as_of_date,
                    freshness=source_ref.freshness,
                    data_quality_status=source_ref.data_quality_status,
                )
                for source_ref in candidate.evidence_packet.source_refs
            ),
            reason_codes=candidate.evidence_packet.reason_codes,
            unsupported_reasons=candidate.evidence_packet.unsupported_reasons,
            score_policy_version=(
                candidate.score.policy_version if candidate.score is not None else None
            ),
            score=(candidate.score.score if candidate.score is not None else None),
            source_signal_count=len(candidate.source_signal_ids),
        )


@dataclass(frozen=True)
class AIExplanationCommand:
    request_id: str
    actor_subject: str
    workflow_pack: AIWorkflowPackRef
    approved_metadata: Mapping[str, str]
    requested_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        require_governed_ai_workflow_pack(self.workflow_pack)
        object.__setattr__(
            self,
            "approved_metadata",
            validate_ai_metadata_envelope(
                self.approved_metadata,
                purpose=self.workflow_pack.purpose.value,
            ),
        )


@dataclass(frozen=True)
class AIExplanationRequest:
    request_id: str
    actor_subject: str
    workflow_pack: AIWorkflowPackRef
    redacted_evidence: RedactedIdeaEvidence
    approved_metadata: Mapping[str, str]
    requested_at_utc: datetime
    reason_codes: tuple[ReasonCode, ...]

    @property
    def purpose(self) -> AIWorkflowPurpose:
        return self.workflow_pack.purpose

    def __post_init__(self) -> None:
        _require_text(self.request_id, "request_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_aware_utc(self.requested_at_utc, "requested_at_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(
            self,
            "approved_metadata",
            validate_ai_metadata_envelope(
                self.approved_metadata,
                purpose=self.workflow_pack.purpose.value,
            ),
        )
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class AIOutputClaim:
    claim_id: str
    claim_text: str
    source_product_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.claim_id, "claim_id")
        _require_text(self.claim_text, "claim_text")
        if not self.source_product_ids:
            raise ValueError("source_product_ids is required")
        if any(not source_product_id.strip() for source_product_id in self.source_product_ids):
            raise ValueError("source_product_ids cannot contain blank values")
        if len(set(self.source_product_ids)) != len(self.source_product_ids):
            raise ValueError("source_product_ids must be unique")
        object.__setattr__(self, "source_product_ids", tuple(self.source_product_ids))


@dataclass(frozen=True)
class AIProposedAction:
    action_type: AIProposedActionType
    action_label: str

    def __post_init__(self) -> None:
        _require_text(self.action_label, "action_label")


@dataclass(frozen=True)
class AIWorkflowOutput:
    output_id: str
    request_id: str
    workflow_pack_id: str
    workflow_pack_version: str
    explanation_text: str
    claims: tuple[AIOutputClaim, ...]
    proposed_actions: tuple[AIProposedAction, ...]
    verifier_ran_at_utc: datetime

    def __post_init__(self) -> None:
        _require_text(self.output_id, "output_id")
        _require_text(self.request_id, "request_id")
        _require_text(self.workflow_pack_id, "workflow_pack_id")
        _require_text(self.workflow_pack_version, "workflow_pack_version")
        _require_text(self.explanation_text, "explanation_text")
        _require_aware_utc(self.verifier_ran_at_utc, "verifier_ran_at_utc")
        if not self.claims:
            raise ValueError("claims is required")
        if len({claim.claim_id for claim in self.claims}) != len(self.claims):
            raise ValueError("claim_ids must be unique")
        if not self.proposed_actions:
            raise ValueError("proposed_actions is required")
        object.__setattr__(self, "claims", tuple(self.claims))
        object.__setattr__(self, "proposed_actions", tuple(self.proposed_actions))


@dataclass(frozen=True)
class AIExplanationResult:
    request: AIExplanationRequest
    posture: AIExplanationPosture
    verifier_outcome: AIVerifierOutcome
    explanation_text: str
    reason_codes: tuple[ReasonCode, ...]
    audit_event: AuditEvent
    output_integrity: AIOutputIntegrity
    execution_provenance_posture: AIExecutionProvenancePosture
    output: AIWorkflowOutput | None = None
    fallback_reason: AIFallbackReason | None = None

    @property
    def fallback_used(self) -> bool:
        return self.fallback_reason is not None

    @property
    def grants_downstream_authority(self) -> bool:
        return False

    def __post_init__(self) -> None:
        _require_text(self.explanation_text, "explanation_text")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if self.posture is AIExplanationPosture.FALLBACK_USED and self.fallback_reason is None:
            raise ValueError("fallback_reason is required for fallback posture")
        if (
            self.posture is not AIExplanationPosture.FALLBACK_USED
            and self.fallback_reason is not None
        ):
            raise ValueError("fallback_reason requires fallback posture")
        if (
            self.posture is AIExplanationPosture.FALLBACK_USED
            and self.execution_provenance_posture
            is not AIExecutionProvenancePosture.NOT_APPLICABLE_FALLBACK
        ):
            raise ValueError("fallback result requires not-applicable execution provenance")
        if (
            self.posture is not AIExplanationPosture.FALLBACK_USED
            and self.execution_provenance_posture
            is AIExecutionProvenancePosture.NOT_APPLICABLE_FALLBACK
        ):
            raise ValueError("evaluated workflow output requires execution provenance posture")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


def build_ai_explanation_request(
    candidate: IdeaCandidate,
    command: AIExplanationCommand,
) -> AIExplanationRequest:
    require_governed_ai_workflow_pack(command.workflow_pack)
    _ensure_purpose_allowed_for_candidate(candidate, command.workflow_pack.purpose)
    return AIExplanationRequest(
        request_id=command.request_id,
        actor_subject=command.actor_subject,
        workflow_pack=command.workflow_pack,
        redacted_evidence=RedactedIdeaEvidence.from_candidate(candidate),
        approved_metadata=command.approved_metadata,
        requested_at_utc=command.requested_at_utc,
        reason_codes=(ReasonCode.AI_REDACTION_APPLIED,),
    )


def deterministic_ai_fallback(
    request: AIExplanationRequest,
    *,
    fallback_reason: AIFallbackReason,
    occurred_at_utc: datetime,
) -> AIExplanationResult:
    _require_aware_utc(occurred_at_utc, "occurred_at_utc")
    evidence = request.redacted_evidence
    explanation_text = (
        "AI explanation is unavailable. Use deterministic evidence: "
        f"{evidence.family.value}, supportability {evidence.supportability.value}, "
        f"reason codes {', '.join(reason.value for reason in evidence.reason_codes)}."
    )
    output_integrity = build_ai_output_integrity(
        explanation_text=explanation_text,
        claims=(),
        proposed_actions=(),
        workflow_pack_id=request.workflow_pack.workflow_pack_id,
        workflow_pack_version=request.workflow_pack.workflow_pack_version,
        evaluation_ref=request.workflow_pack.evaluation_ref,
        action_policy_version=AI_ACTION_POLICY_VERSION,
        output_kind="fallback",
        policy_metadata={"fallback_reason": fallback_reason.value},
    )
    return AIExplanationResult(
        request=request,
        output=None,
        posture=AIExplanationPosture.FALLBACK_USED,
        verifier_outcome=AIVerifierOutcome.NOT_RUN,
        fallback_reason=fallback_reason,
        explanation_text=explanation_text,
        reason_codes=(ReasonCode.AI_FALLBACK_USED,),
        output_integrity=output_integrity,
        execution_provenance_posture=AIExecutionProvenancePosture.NOT_APPLICABLE_FALLBACK,
        audit_event=_ai_audit_event(
            request=request,
            posture=AIExplanationPosture.FALLBACK_USED,
            verifier_outcome=AIVerifierOutcome.NOT_RUN,
            outcome="fallback",
            occurred_at_utc=occurred_at_utc,
            output_integrity=output_integrity,
        ),
    )


def evaluate_ai_workflow_output(
    request: AIExplanationRequest,
    output: AIWorkflowOutput,
) -> AIExplanationResult:
    _ensure_output_matches_request(request, output)
    output_integrity = _workflow_output_integrity(request, output)
    action_decisions = tuple(
        evaluate_ai_action_policy(action.action_type, action.action_label)
        for action in output.proposed_actions
    )
    sanitized_output = replace(
        output,
        proposed_actions=tuple(
            AIProposedAction(action.action_type, decision.canonical_label)
            for action, decision in zip(output.proposed_actions, action_decisions)
        ),
    )
    if any(
        decision.reason is AIActionPolicyReason.FORBIDDEN_ACTION_TYPE
        for decision in action_decisions
    ):
        return _blocked_ai_result(
            request=request,
            output=sanitized_output,
            posture=AIExplanationPosture.BLOCKED_FORBIDDEN_ACTION,
            verifier_outcome=AIVerifierOutcome.FAILED_FORBIDDEN_ACTION,
            reason_code=ReasonCode.AI_FORBIDDEN_ACTION_BLOCKED,
            action_policy_reason=AIActionPolicyReason.FORBIDDEN_ACTION_TYPE,
            output_integrity=output_integrity,
        )
    rejected_content = next(
        (decision for decision in action_decisions if not decision.allowed),
        None,
    )
    if rejected_content is not None:
        return _blocked_ai_result(
            request=request,
            output=sanitized_output,
            posture=AIExplanationPosture.BLOCKED_FORBIDDEN_ACTION,
            verifier_outcome=AIVerifierOutcome.FAILED_ACTION_CONTENT,
            reason_code=ReasonCode.AI_ACTION_CONTENT_BLOCKED,
            action_policy_reason=rejected_content.reason,
            output_integrity=output_integrity,
        )
    allowed_source_product_ids = request.redacted_evidence.source_product_ids
    unsupported_claims = tuple(
        claim
        for claim in sanitized_output.claims
        if not set(claim.source_product_ids).issubset(allowed_source_product_ids)
    )
    if unsupported_claims:
        return _blocked_ai_result(
            request=request,
            output=sanitized_output,
            posture=AIExplanationPosture.BLOCKED_UNSUPPORTED_CLAIM,
            verifier_outcome=AIVerifierOutcome.FAILED_UNSUPPORTED_CLAIM,
            reason_code=ReasonCode.AI_UNSUPPORTED_CLAIM_BLOCKED,
            action_policy_reason=AIActionPolicyReason.ALLOWED,
            output_integrity=output_integrity,
        )
    grounded_output = replace(
        sanitized_output,
        explanation_text=render_grounded_claim_narrative(sanitized_output.claims),
    )
    grounded_output_integrity = _workflow_output_integrity(
        request,
        grounded_output,
        provider_output_digest=output_integrity.digest,
    )
    return AIExplanationResult(
        request=request,
        output=grounded_output,
        posture=AIExplanationPosture.READY_FOR_ADVISOR_REVIEW,
        verifier_outcome=AIVerifierOutcome.PASSED,
        fallback_reason=None,
        explanation_text=grounded_output.explanation_text,
        reason_codes=(ReasonCode.AI_VERIFIER_PASSED,),
        output_integrity=grounded_output_integrity,
        execution_provenance_posture=(AIExecutionProvenancePosture.UNATTESTED_LOCAL_TEST_FIXTURE),
        audit_event=_ai_audit_event(
            request=request,
            posture=AIExplanationPosture.READY_FOR_ADVISOR_REVIEW,
            verifier_outcome=AIVerifierOutcome.PASSED,
            outcome="accepted",
            occurred_at_utc=grounded_output.verifier_ran_at_utc,
            action_policy_reason=AIActionPolicyReason.ALLOWED,
            output_integrity=grounded_output_integrity,
        ),
    )


def _blocked_ai_result(
    *,
    request: AIExplanationRequest,
    output: AIWorkflowOutput,
    posture: AIExplanationPosture,
    verifier_outcome: AIVerifierOutcome,
    reason_code: ReasonCode,
    action_policy_reason: AIActionPolicyReason,
    output_integrity: AIOutputIntegrity,
) -> AIExplanationResult:
    blocked_explanation = _blocked_ai_explanation(reason_code)
    sanitized_output = replace(output, explanation_text=blocked_explanation)
    return AIExplanationResult(
        request=request,
        output=sanitized_output,
        posture=posture,
        verifier_outcome=verifier_outcome,
        fallback_reason=None,
        explanation_text=blocked_explanation,
        reason_codes=(reason_code,),
        output_integrity=output_integrity,
        execution_provenance_posture=(AIExecutionProvenancePosture.UNATTESTED_LOCAL_TEST_FIXTURE),
        audit_event=_ai_audit_event(
            request=request,
            posture=posture,
            verifier_outcome=verifier_outcome,
            outcome="blocked",
            occurred_at_utc=output.verifier_ran_at_utc,
            action_policy_reason=action_policy_reason,
            output_integrity=output_integrity,
        ),
    )


def _blocked_ai_explanation(reason_code: ReasonCode) -> str:
    explanations = {
        ReasonCode.AI_UNSUPPORTED_CLAIM_BLOCKED: (
            "AI explanation was blocked because one or more claims lacked approved "
            "evidence bindings."
        ),
        ReasonCode.AI_FORBIDDEN_ACTION_BLOCKED: (
            "AI explanation was blocked because it proposed an action outside the "
            "Idea authority boundary."
        ),
        ReasonCode.AI_ACTION_CONTENT_BLOCKED: (
            "AI explanation was blocked because proposed action content violated "
            "the governed action policy."
        ),
    }
    try:
        return explanations[reason_code]
    except KeyError as exc:
        raise ValueError("unsupported blocked AI reason code") from exc


def _ensure_purpose_allowed_for_candidate(
    candidate: IdeaCandidate,
    purpose: AIWorkflowPurpose,
) -> None:
    if purpose in {
        AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT,
        AIWorkflowPurpose.MEETING_PREPARATION_DRAFT,
    }:
        if candidate.evidence_packet.supportability is not EvidenceSupportability.READY:
            raise InvalidAIExplanationRequest(
                "rationale drafting requires ready evidence supportability"
            )
        if candidate.lifecycle_status not in {
            IdeaLifecycleStatus.READY_FOR_REVIEW,
            IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
            IdeaLifecycleStatus.APPROVED,
        }:
            raise InvalidAIExplanationRequest(
                "rationale drafting requires review-ready candidate lifecycle"
            )


def _ensure_output_matches_request(
    request: AIExplanationRequest,
    output: AIWorkflowOutput,
) -> None:
    if output.request_id != request.request_id:
        raise InvalidAIWorkflowOutput("output request_id does not match request")
    if output.workflow_pack_id != request.workflow_pack.workflow_pack_id:
        raise InvalidAIWorkflowOutput("output workflow_pack_id does not match request")
    if output.workflow_pack_version != request.workflow_pack.workflow_pack_version:
        raise InvalidAIWorkflowOutput("output workflow_pack_version does not match request")


def ai_workflow_pack_is_governed(workflow_pack: AIWorkflowPackRef) -> bool:
    contract = GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK
    return (
        workflow_pack.workflow_pack_id == contract.request_workflow_pack_id
        and workflow_pack.workflow_pack_version == contract.workflow_pack_version
        and workflow_pack.evaluation_ref == contract.evaluation_ref
        and workflow_pack.purpose in contract.allowed_purposes
    )


def require_governed_ai_workflow_pack(workflow_pack: AIWorkflowPackRef) -> None:
    if not ai_workflow_pack_is_governed(workflow_pack):
        raise InvalidAIWorkflowPack()


def _ai_audit_event(
    *,
    request: AIExplanationRequest,
    posture: AIExplanationPosture,
    verifier_outcome: AIVerifierOutcome,
    outcome: str,
    occurred_at_utc: datetime,
    action_policy_reason: AIActionPolicyReason | None = None,
    output_integrity: AIOutputIntegrity,
) -> AuditEvent:
    return AuditEvent(
        event_type="idea.ai_explanation.evaluated",
        actor_subject=request.actor_subject,
        outcome=outcome,
        occurred_at_utc=occurred_at_utc,
        attributes={
            "evidence_packet_id": request.redacted_evidence.evidence_packet_id,
            "fallback_used": str(posture is AIExplanationPosture.FALLBACK_USED).lower(),
            "posture": posture.value,
            "purpose": request.purpose.value,
            "verifier_outcome": verifier_outcome.value,
            "workflow_pack_id": request.workflow_pack.workflow_pack_id,
            "workflow_pack_version": request.workflow_pack.workflow_pack_version,
            "action_policy_version": AI_ACTION_POLICY_VERSION,
            "action_policy_reason": (
                action_policy_reason.value if action_policy_reason is not None else "not_run"
            ),
            "output_integrity_version": output_integrity.version,
            "output_content_digest": output_integrity.digest,
            "execution_provenance_posture": (
                AIExecutionProvenancePosture.NOT_APPLICABLE_FALLBACK.value
                if posture is AIExplanationPosture.FALLBACK_USED
                else AIExecutionProvenancePosture.UNATTESTED_LOCAL_TEST_FIXTURE.value
            ),
        },
    )


def _workflow_output_integrity(
    request: AIExplanationRequest,
    output: AIWorkflowOutput,
    *,
    provider_output_digest: str | None = None,
) -> AIOutputIntegrity:
    policy_metadata = {
        "claim_grounding_policy": AI_CLAIM_GROUNDING_POLICY_VERSION,
        "verifier_policy": "deterministic_source_and_action_verifier.v1",
    }
    if provider_output_digest is not None:
        policy_metadata["provider_output_digest"] = provider_output_digest
    return build_ai_output_integrity(
        explanation_text=output.explanation_text,
        claims=tuple(
            {
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "source_product_ids": claim.source_product_ids,
            }
            for claim in output.claims
        ),
        proposed_actions=tuple(
            {
                "action_type": action.action_type.value,
                "submitted_action_label": action.action_label,
            }
            for action in output.proposed_actions
        ),
        workflow_pack_id=output.workflow_pack_id,
        workflow_pack_version=output.workflow_pack_version,
        evaluation_ref=request.workflow_pack.evaluation_ref,
        action_policy_version=AI_ACTION_POLICY_VERSION,
        output_kind="workflow_output",
        policy_metadata=policy_metadata,
    )
