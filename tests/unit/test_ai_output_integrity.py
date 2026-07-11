from __future__ import annotations

from app.domain.ai_output_integrity import build_ai_output_integrity


def _integrity(
    *,
    explanation_text: str = "Review this evidence.",
    claim_text: str = "Cash exceeds the governed threshold.",
    action_label: str = "Review the evidence as an advisor",
    claims: tuple[dict[str, object], ...] | None = None,
    action_policy_version: str = "lotus-idea.ai-action-content-policy.v1",
) -> str:
    return build_ai_output_integrity(
        explanation_text=explanation_text,
        claims=claims
        or (
            {
                "claim_id": "claim-1",
                "claim_text": claim_text,
                "source_product_ids": ("lotus-core:PortfolioSnapshot:v1",),
            },
        ),
        proposed_actions=(
            {
                "action_type": "advisor_review",
                "submitted_action_label": action_label,
            },
        ),
        workflow_pack_id="lotus-ai:idea-explanation:v1",
        workflow_pack_version="v1",
        evaluation_ref="lotus-ai:governed-verifier:v1",
        action_policy_version=action_policy_version,
        output_kind="workflow_output",
    ).digest


def test_output_integrity_covers_every_advisor_visible_content_dimension() -> None:
    baseline = _integrity()

    assert _integrity(explanation_text="Changed explanation.") != baseline
    assert _integrity(claim_text="Changed claim.") != baseline
    assert _integrity(action_label="Changed safe label.") != baseline
    assert _integrity(action_policy_version="lotus-idea.ai-action-content-policy.v2") != baseline


def test_output_integrity_preserves_contractually_meaningful_claim_order() -> None:
    first = {
        "claim_id": "claim-1",
        "claim_text": "First claim.",
        "source_product_ids": ("product-1",),
    }
    second = {
        "claim_id": "claim-2",
        "claim_text": "Second claim.",
        "source_product_ids": ("product-2",),
    }

    assert _integrity(claims=(first, second)) != _integrity(claims=(second, first))


def test_output_integrity_canonicalizes_encoding_and_line_endings_only() -> None:
    assert _integrity(explanation_text="Cafe\u0301\r\nReview") == _integrity(
        explanation_text="Caf\u00e9\nReview"
    )
    assert _integrity(explanation_text="Review  evidence") != _integrity(
        explanation_text="Review evidence"
    )
