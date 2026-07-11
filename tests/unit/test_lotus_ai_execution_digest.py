from app.domain.lotus_ai_execution_digest import (
    LotusAIExecutionInputEvidence,
    LotusAIExecutionOutputContent,
    lotus_ai_input_evidence_sha256,
    lotus_ai_output_content_sha256,
)


def test_reproduces_producer_input_and_output_digest_contract() -> None:
    input_evidence = LotusAIExecutionInputEvidence(
        task_id="explain.v1",
        context_summary="Generate a review-gated explanation.",
        context_payload={
            "redacted_evidence_packet": {
                "evidence_packet_id": "idea-evidence-001",
                "supportability": "READY",
            },
            "explanation_request": {"request_id": "request-001"},
        },
        source_refs=("lotus-idea:evidence-packet:idea-evidence-001",),
        expected_output_label="EXPLANATION_ONLY",
    )
    output_content = LotusAIExecutionOutputContent(
        status="COMPLETED",
        output_label="EXPLANATION_ONLY",
        message="Source-grounded explanation.",
        structured_output={
            "advisor_review_summary": "Review the source evidence.",
            "human_review_required": True,
        },
    )

    assert lotus_ai_input_evidence_sha256(input_evidence) == (
        "5c394ca288c68fdf5f8ad7a51750c830ee7ae14905674cc614e68bd32e5a63c3"
    )
    assert lotus_ai_output_content_sha256(output_content) == (
        "7a256c5a5150b8a9b94c274240d442135e359a569c82d57e82db4d08f71e951b"
    )


def test_digest_changes_for_material_input_or_output_change() -> None:
    baseline_input = LotusAIExecutionInputEvidence(
        task_id="explain.v1",
        context_summary="summary",
        context_payload={"evidence": "one"},
        source_refs=("source:one",),
        expected_output_label="EXPLANATION_ONLY",
    )
    changed_input = LotusAIExecutionInputEvidence(
        task_id="explain.v1",
        context_summary="summary",
        context_payload={"evidence": "two"},
        source_refs=("source:one",),
        expected_output_label="EXPLANATION_ONLY",
    )
    baseline_output = LotusAIExecutionOutputContent(
        status="COMPLETED",
        output_label="EXPLANATION_ONLY",
        message="one",
        structured_output={"value": 1},
    )
    changed_output = LotusAIExecutionOutputContent(
        status="COMPLETED",
        output_label="EXPLANATION_ONLY",
        message="two",
        structured_output={"value": 1},
    )

    assert lotus_ai_input_evidence_sha256(baseline_input) != lotus_ai_input_evidence_sha256(
        changed_input
    )
    assert lotus_ai_output_content_sha256(baseline_output) != lotus_ai_output_content_sha256(
        changed_output
    )
