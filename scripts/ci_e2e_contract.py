from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_E2E_WORKFLOW_FILES: dict[str, tuple[str, ...]] = {
    "test_critical_idea_workflow.py": (
        "test_critical_idea_workflow_preserves_authority_boundaries",
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        "/api/v1/review-queues/advisor",
        "/api/v1/idea-candidates/{candidate_id}/review-actions",
        "/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        "/api/v1/conversion-intents/critical-e2e-conversion-report-001/report-evidence-packs",
        '"grantsDownstreamAuthority"',
        '"grantsClientPublicationAuthority"',
        '"createsRenderedOutput"',
        '"clientReadyPublicationRequested"',
        '"supportedFeaturePromoted"',
    )
}


def validate_e2e_suite(tests_dir: Path) -> list[str]:
    errors: list[str] = []
    if not tests_dir.exists():
        return [f"Missing {tests_dir.relative_to(ROOT).as_posix()}"]

    for filename, required_fragments in REQUIRED_E2E_WORKFLOW_FILES.items():
        test_path = tests_dir / filename
        if not test_path.exists():
            errors.append(f"tests/e2e missing required critical workflow proof `{filename}`")
            continue
        content = test_path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            if fragment not in content:
                errors.append(
                    f"tests/e2e/{filename} missing critical workflow assertion `{fragment}`"
                )
    return errors
