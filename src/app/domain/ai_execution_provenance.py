from __future__ import annotations

from enum import StrEnum

AI_EXECUTION_PROVENANCE_POLICY_VERSION = "lotus-idea.ai-execution-provenance-policy.v1"


class AIExecutionProvenancePosture(StrEnum):
    NOT_APPLICABLE_FALLBACK = "not_applicable_fallback"
    UNATTESTED_LOCAL_TEST_FIXTURE = "unattested_local_test_fixture"
    PRE_ATTESTATION_UNVERIFIABLE = "pre_attestation_unverifiable"


class AIWorkflowOutputTrustPolicy(StrEnum):
    UNATTESTED_LOCAL_TEST_FIXTURE_ALLOWED = "unattested_local_test_fixture_allowed"
    LOTUS_AI_ATTESTATION_REQUIRED = "lotus_ai_attestation_required"


class UntrustedAIWorkflowOutput(ValueError):
    """Raised when workflow output lacks provenance required by the runtime profile."""
