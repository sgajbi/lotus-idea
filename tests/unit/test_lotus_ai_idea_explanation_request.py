from app.application.lotus_ai_idea_explanation_request import (
    build_lotus_ai_idea_explanation_input,
)
from app.domain.ai_governance import build_ai_explanation_request
from app.domain.lotus_ai_execution_digest import lotus_ai_input_evidence_sha256
from tests.unit.test_ai_governance import candidate, command


def test_builds_redacted_review_gated_lotus_ai_input_from_idea_truth() -> None:
    request = build_ai_explanation_request(candidate(), command())

    evidence = build_lotus_ai_idea_explanation_input(request)

    payload = evidence.context_payload
    redacted = payload["redacted_evidence_packet"]
    explanation = payload["explanation_request"]
    supportability = payload["supportability"]
    assert isinstance(redacted, dict)
    assert isinstance(explanation, dict)
    assert isinstance(supportability, dict)
    assert redacted["candidate_id"] == "idea-ai-001"
    assert redacted["evidence_packet_id"] == "iep_ai_test"
    assert redacted["source_revision_vector_digest"] == (
        request.redacted_evidence.source_revision_vector_digest
    )
    assert redacted["source_cut_posture"] == request.redacted_evidence.source_cut_posture.value
    assert redacted["score_components"] == [
        {
            "component": "materiality",
            "input_score": "84",
            "weight": "1",
            "contribution": "84.00",
        }
    ]
    assert redacted["score_conflict_penalty_applied"] == "0"
    assert explanation["workflow_pack_id"] == "lotus-ai:idea-explanation:v1"
    assert explanation["requested_outputs"] == [
        "advisor_review_summary",
        "source_evidence_summary",
        "unsupported_claim_check",
    ]
    assert supportability["human_review_required"] is True
    assert supportability["client_ready_publication"] == "BLOCKED"
    assert "place_orders" in supportability["forbidden_actions"]
    assert evidence.source_refs == ("lotus-idea:evidence-packet:iep_ai_test",)
    assert lotus_ai_input_evidence_sha256(evidence) == (
        "96cd189c6d5ac7449449b9bffb3a6025e7846b2581b4295f6dc0e5fbf521dfeb"
    )


def test_outbound_lotus_ai_input_excludes_raw_and_consequence_authority_fields() -> None:
    request = build_ai_explanation_request(candidate(), command())

    payload_text = str(build_lotus_ai_idea_explanation_input(request).context_payload).lower()

    for forbidden in (
        "raw_payload",
        "raw_prompt",
        "provider_response",
        "suitability_approval': 'allowed",
        "client_ready_publication': 'allowed",
    ):
        assert forbidden not in payload_text
