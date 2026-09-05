from prometheus_client import CollectorRegistry
import pytest

from app.application.lotus_ai_idea_explanation_generation import (
    AIExplanationGenerationStatus,
)
from app.domain.ai_governance import AIWorkflowPurpose
from app.observability.ai_explanation_generation import (
    AI_EXPLANATION_GENERATION_REQUESTS_METRIC,
    AIExplanationGenerationMetrics,
)


def test_generation_metrics_distinguish_request_served_and_unavailable_by_purpose() -> None:
    registry = CollectorRegistry()
    metrics = AIExplanationGenerationMetrics(registry)
    purpose = AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT

    metrics.observe_requested(purpose)
    metrics.observe_outcome(purpose, AIExplanationGenerationStatus.EXPLANATION_SERVED)
    metrics.observe_requested(purpose)
    metrics.observe_outcome(purpose, AIExplanationGenerationStatus.EXPLANATION_UNAVAILABLE)

    labels = {"purpose": purpose.value}
    assert (
        registry.get_sample_value(
            AI_EXPLANATION_GENERATION_REQUESTS_METRIC,
            {**labels, "outcome": "requested"},
        )
        == 2
    )
    assert (
        registry.get_sample_value(
            AI_EXPLANATION_GENERATION_REQUESTS_METRIC,
            {**labels, "outcome": "EXPLANATION_SERVED"},
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            AI_EXPLANATION_GENERATION_REQUESTS_METRIC,
            {**labels, "outcome": "EXPLANATION_UNAVAILABLE"},
        )
        == 1
    )


def test_generation_metrics_reject_ungoverned_outcome_labels() -> None:
    metrics = AIExplanationGenerationMetrics(CollectorRegistry())

    with pytest.raises(
        ValueError,
        match="AI explanation generation metric outcome is not governed",
    ):
        metrics._observe(
            purpose=AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT,
            outcome="candidate-specific-unbounded-label",
        )
