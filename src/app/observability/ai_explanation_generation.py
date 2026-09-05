from __future__ import annotations

from prometheus_client import REGISTRY, CollectorRegistry, Counter

from app.application.lotus_ai_idea_explanation_generation import (
    AIExplanationGenerationStatus,
)
from app.domain.ai_governance import AIWorkflowPurpose


AI_EXPLANATION_GENERATION_REQUESTS_METRIC = "lotus_idea_ai_explanation_generation_requests_total"
AI_EXPLANATION_GENERATION_METRIC_LABELS = ("purpose", "outcome")
AI_EXPLANATION_GENERATION_OUTCOMES = frozenset(
    {
        "requested",
        AIExplanationGenerationStatus.EXPLANATION_SERVED.value,
        AIExplanationGenerationStatus.EXPLANATION_UNAVAILABLE.value,
    }
)


class AIExplanationGenerationMetrics:
    """Low-cardinality product telemetry for the governed generation journey."""

    def __init__(self, registry: CollectorRegistry = REGISTRY) -> None:
        self._requests = Counter(
            AI_EXPLANATION_GENERATION_REQUESTS_METRIC,
            (
                "Count of valid governed Idea explanation generation requests and their "
                "served or unavailable outcomes."
            ),
            AI_EXPLANATION_GENERATION_METRIC_LABELS,
            registry=registry,
        )

    def observe_requested(self, purpose: AIWorkflowPurpose) -> None:
        self._observe(purpose=purpose, outcome="requested")

    def observe_outcome(
        self,
        purpose: AIWorkflowPurpose,
        status: AIExplanationGenerationStatus,
    ) -> None:
        self._observe(purpose=purpose, outcome=status.value)

    def _observe(self, *, purpose: AIWorkflowPurpose, outcome: str) -> None:
        if outcome not in AI_EXPLANATION_GENERATION_OUTCOMES:
            raise ValueError("AI explanation generation metric outcome is not governed")
        self._requests.labels(purpose=purpose.value, outcome=outcome).inc()


_METRICS = AIExplanationGenerationMetrics()


def observe_ai_explanation_generation_requested(purpose: AIWorkflowPurpose) -> None:
    _METRICS.observe_requested(purpose)


def observe_ai_explanation_generation_outcome(
    purpose: AIWorkflowPurpose,
    status: AIExplanationGenerationStatus,
) -> None:
    _METRICS.observe_outcome(purpose, status)


__all__ = [
    "AI_EXPLANATION_GENERATION_METRIC_LABELS",
    "AI_EXPLANATION_GENERATION_OUTCOMES",
    "AI_EXPLANATION_GENERATION_REQUESTS_METRIC",
    "AIExplanationGenerationMetrics",
    "observe_ai_explanation_generation_outcome",
    "observe_ai_explanation_generation_requested",
]
