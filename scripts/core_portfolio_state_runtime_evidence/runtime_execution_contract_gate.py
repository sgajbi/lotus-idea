from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.application.core_portfolio_state_runtime_evidence import (  # noqa: E402
    CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS,
    CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED,
    EvaluateCorePortfolioStateReadiness,
    build_blocked_core_portfolio_state_runtime_execution,
    build_core_portfolio_state_runtime_execution,
    core_portfolio_state_runtime_execution_is_valid,
    evaluate_core_portfolio_state_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem  # noqa: E402
from app.ports.core_sources import (  # noqa: E402
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
)

try:
    from scripts.proof_source_safety import validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import validate_forbidden_content  # type: ignore[import-not-found,no-redef]

GENERATOR = (
    ROOT / "scripts" / "core_portfolio_state_runtime_evidence" / "generate_runtime_execution.py"
)
PROHIBITED_PATHS = (
    ROOT / "src" / "app" / "application" / "core_portfolio_state_live_proof.py",
    ROOT / "scripts" / "generate_core_portfolio_state_live_proof.py",
    ROOT / "scripts" / "core_portfolio_state_live_proof_contract_gate.py",
    ROOT / "tests" / "unit" / "test_core_portfolio_state_live_proof.py",
)
FORBIDDEN_KEYS = {
    "accountId",
    "clientId",
    "correlationId",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "tenantId",
    "traceId",
}
FORBIDDEN_TEXT = {"PB_SG_GLOBAL_BAL_001", "tenant-a", "portfolio-a", "corr-a"}
NOW = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


class _CoreSource:
    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
        return _evidence(request)


def validate_core_portfolio_state_runtime_execution_contract() -> list[str]:
    errors: list[str] = []
    if not GENERATOR.exists():
        errors.append("capability-owned Core portfolio-state generator is required")
    for path in PROHIBITED_PATHS:
        if path.exists():
            errors.append(
                f"retired Core portfolio-state path is prohibited: {path.relative_to(ROOT)}"
            )

    command = _command()
    result = evaluate_core_portfolio_state_readiness(command, core_source=_CoreSource())
    payload = build_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        result=result,
    )
    if not core_portfolio_state_runtime_execution_is_valid(payload):
        errors.append("authoritative Core portfolio-state runtime fixture must validate")
    if payload.get("aggregateBlockersSatisfied") != list(
        CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED
    ):
        errors.append("runtime evidence must clear only the Core portfolio-state source blocker")
    if payload.get("remainingCertificationBlockers") != list(
        CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS
    ):
        errors.append("runtime evidence must preserve unrelated certification blockers")

    claims = payload.get("nonProofClaims")
    if not isinstance(claims, dict) or claims.get("portfolioStateOwned") != "lotus-core":
        errors.append("runtime evidence must preserve Core portfolio-state authority")
    elif any(value is not False for key, value in claims.items() if key != "portfolioStateOwned"):
        errors.append("runtime evidence must reject non-proof claim inflation")

    missing_snapshot = build_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        result=replace(result, evidence=replace(result.evidence, snapshot_id=None)),
    )
    if core_portfolio_state_runtime_execution_is_valid(missing_snapshot):
        errors.append("runtime evidence must reject missing Core snapshot identity")
    blocked = build_blocked_core_portfolio_state_runtime_execution(
        generated_at_utc=NOW,
        command=command,
        error_code="core_source_entitlement_denied",
    )
    if core_portfolio_state_runtime_execution_is_valid(blocked):
        errors.append("blocked Core portfolio-state execution must not validate")
    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    validate_forbidden_content(blocked, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _command() -> EvaluateCorePortfolioStateReadiness:
    return EvaluateCorePortfolioStateReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=NOW,
        correlation_id="corr-a",
        trace_id="trace-a",
    )


def _evidence(request: CorePortfolioStateEvidenceRequest) -> CorePortfolioStateEvidence:
    content_hash = "sha256:" + "a" * 64
    source_generated = request.evaluated_at_utc - timedelta(minutes=1)
    return CorePortfolioStateEvidence(
        portfolio_state_ref=SourceRef(
            product_id="lotus-core:PortfolioStateSnapshot:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/integration/portfolios/{portfolio_id}/core-snapshot",
            as_of_date=request.as_of_date,
            generated_at_utc=source_generated,
            content_hash=content_hash,
            data_quality_status="COMPLETE",
            freshness=EvidenceFreshness.CURRENT,
        ),
        source_evidence_available=True,
        response_product_name="PortfolioStateSnapshot",
        response_product_version="v1",
        response_tenant_id=request.tenant_id,
        response_portfolio_id=request.portfolio_id,
        snapshot_mode="BASELINE",
        request_fingerprint="core-snapshot-request:test",
        snapshot_id="pss_test_snapshot",
        source_batch_fingerprint=content_hash,
        response_content_hash=content_hash,
        response_source_digest=content_hash,
        restatement_version="restatement-v1",
        reconciliation_status="COMPLETE",
        latest_evidence_at_utc=source_generated - timedelta(minutes=1),
        source_evidence_current=True,
        policy_version="tenant-policy-v1",
        source_correlation_id=request.correlation_id,
        applied_sections=("portfolio_state", "portfolio_totals"),
        portfolio_state_diagnostic="core_portfolio_state_ready",
    )


def main() -> int:
    errors = validate_core_portfolio_state_runtime_execution_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Core portfolio-state runtime execution contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
