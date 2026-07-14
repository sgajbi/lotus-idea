from __future__ import annotations

from enum import StrEnum


class EvidenceClass(StrEnum):
    SOURCE_CONTRACT = "source_contract"
    TEST_EXECUTION = "test_execution"
    CI_EXECUTION = "ci_execution"
    RUNTIME_EXECUTION = "runtime_execution"
    DEPLOYMENT = "deployment"
    PRODUCTION_CERTIFICATION = "production_certification"


def evidence_class_can_clear(*, actual: EvidenceClass, required: EvidenceClass) -> bool:
    """Prevent one proof class from being promoted into a different claim."""

    return actual is required
