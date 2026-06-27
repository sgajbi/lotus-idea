from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.application.risk_drawdown_live_proof import (
    RISK_DRAWDOWN_LIVE_PROOF_SCHEMA_VERSION,
    build_risk_drawdown_live_proof_payload,
    risk_drawdown_live_proof_is_valid,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
    RiskOpportunitySourcePort,
    RiskSourceUnavailable,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
)


ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 6, 21)
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


@dataclass
class RecordingRiskSource(RiskOpportunitySourcePort):
    error: Exception | None = None

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        raise AssertionError("concentration evidence is not used by drawdown proof tests")

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        raise AssertionError("volatility evidence is not used by drawdown proof tests")

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        if self.error is not None:
            raise self.error
        return _risk_evidence()


def test_risk_drawdown_live_proof_payload_is_source_safe_and_not_promoted() -> None:
    payload = build_risk_drawdown_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_risk_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-risk",
            "sourceProductId": "lotus-risk:DrawdownAnalyticsReport:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "riskSupportabilityReady": True,
            "sourceDiagnosticCodes": ["risk_drawdown_source_ready"],
            "reasonCodes": ["drawdown_attention"],
            "unsupportedReasons": [],
        },
    )

    assert payload["schemaVersion"] == RISK_DRAWDOWN_LIVE_PROOF_SCHEMA_VERSION
    assert payload["runStatus"] == "completed"
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["riskSupportabilityReady"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert payload["proofClosed"] is False
    assert payload["proofBlockers"] == []
    assert payload["aggregateBlockersCleared"] == [
        "opportunity_archetype_drawdown_source_proof_missing"
    ]
    assert risk_drawdown_live_proof_is_valid(payload) is True
    serialized = json.dumps(payload)
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "correlationId" not in serialized
    assert "PB_SG_GLOBAL_BAL_001" not in serialized


def test_blocked_risk_drawdown_live_proof_does_not_validate() -> None:
    payload = build_risk_drawdown_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_risk_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-risk",
            "sourceProductId": "lotus-risk:DrawdownAnalyticsReport:v1",
            "evaluationOutcome": "blocked",
            "sourceEvidenceCurrent": False,
            "riskSupportabilityReady": False,
            "errorCode": "risk_source_unavailable",
            "sourceDiagnosticCodes": ["risk_source_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )

    assert payload["runStatus"] == "blocked"
    assert "drawdown_source_run_blocked" in payload["proofBlockers"]
    assert "source_error_risk_source_unavailable" in payload["proofBlockers"]
    assert "drawdown_source_evidence_not_current" in payload["proofBlockers"]
    assert "drawdown_supportability_not_ready" in payload["proofBlockers"]
    assert "no_drawdown_review_candidate_generated" in payload["proofBlockers"]
    assert risk_drawdown_live_proof_is_valid(payload) is False


def test_risk_drawdown_live_proof_records_missing_live_source_attempt() -> None:
    payload = build_risk_drawdown_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_risk_source_attempted=False,
        evaluation_summary={
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "riskSupportabilityReady": True,
            "sourceDiagnosticCodes": "not-a-list",
            "reasonCodes": "not-a-list",
            "unsupportedReasons": "not-a-list",
        },
    )

    assert payload["runStatus"] == "completed"
    assert payload["sourceDiagnosticCodes"] == []
    assert payload["reasonCodes"] == []
    assert payload["unsupportedReasons"] == []
    assert "drawdown_source_proof_missing" in payload["proofBlockers"]
    assert risk_drawdown_live_proof_is_valid(payload) is False


def test_risk_drawdown_live_proof_rejects_non_candidate_source_evidence() -> None:
    payload = build_risk_drawdown_live_proof_payload(
        generated_at_utc=GENERATED_AT,
        live_risk_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-risk",
            "sourceProductId": "lotus-risk:DrawdownAnalyticsReport:v1",
            "evaluationOutcome": "not_eligible",
            "sourceEvidenceCurrent": True,
            "riskSupportabilityReady": True,
            "sourceDiagnosticCodes": ["risk_drawdown_source_ready"],
            "reasonCodes": ["below_materiality"],
            "unsupportedReasons": [],
        },
    )

    assert "no_drawdown_review_candidate_generated" in payload["proofBlockers"]
    assert risk_drawdown_live_proof_is_valid(payload) is False


def test_risk_drawdown_live_proof_cli_writes_source_safe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "risk-drawdown-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusRiskDrawdownSourceAdapter",
        lambda _client: RecordingRiskSource(),
    )

    result = module.main(
        [
            "--risk-base-url",
            "http://localhost:8300",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--period-name",
            "YTD",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--correlation-id",
            "corr-123",
            "--trace-id",
            "trace-123",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "completed"
    assert payload["liveRiskSourceAttempted"] is True
    assert payload["candidateGenerated"] is True
    assert payload["sourceEvidenceCurrent"] is True
    assert payload["riskSupportabilityReady"] is True
    assert (
        "opportunity_archetype_drawdown_source_proof_missing"
        in (payload["aggregateBlockersCleared"])
    )
    serialized = json.dumps(payload)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "corr-123" not in serialized
    assert "trace-123" not in serialized


def test_risk_drawdown_live_proof_cli_writes_blocked_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_live_proof_script()
    output_path = tmp_path / "risk-drawdown-live-proof.json"

    monkeypatch.setattr(
        module,
        "LotusRiskDrawdownSourceAdapter",
        lambda _client: RecordingRiskSource(
            error=RiskSourceUnavailable(code="risk_source_unavailable")
        ),
    )

    result = module.main(
        [
            "--risk-base-url",
            "http://localhost:8300",
            "--portfolio-id",
            "PB_SG_GLOBAL_BAL_001",
            "--as-of-date",
            "2026-06-21",
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 3
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runStatus"] == "blocked"
    assert "source_error_risk_source_unavailable" in payload["proofBlockers"]
    assert payload["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)


def _risk_evidence() -> RiskDrawdownEvidence:
    return RiskDrawdownEvidence(
        source_reported_max_drawdown=Decimal("-0.1245"),
        risk_supportability_state="ready",
        risk_ref=SourceRef(
            product_id="lotus-risk:DrawdownAnalyticsReport:v1",
            source_system=SourceSystem.LOTUS_RISK,
            product_version="v1",
            route="/analytics/risk/drawdown",
            as_of_date=AS_OF_DATE,
            generated_at_utc=GENERATED_AT,
            content_hash="sha256:drawdown-analytics-report",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        risk_diagnostic="risk_drawdown_source_ready",
    )


def _load_live_proof_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_risk_drawdown_live_proof.py"
    spec = importlib.util.spec_from_file_location("generate_risk_drawdown_live_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
