from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.domain import SourceSystem
from app.infrastructure.downstream_realization import (
    DownstreamRealizationAdapterConfig,
    HttpReportEvidencePackMaterializationClient,
)
from app.ports.downstream_realization import (
    DownstreamRealizationReadConflict,
    DownstreamRealizationReadError,
)
from tests.support.report_materialization import report_materialization_receipt_payload
from tests.unit.test_downstream_realization_adapters import (
    downstream_json_client,
    report_access_scope,
    report_evidence_pack,
    report_service_context,
)


def test_report_adapter_recovers_exact_receipt_with_read_only_owner_contract() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["query"] = dict(request.url.params)
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json=report_materialization_receipt_payload(
                report_evidence_pack(),
                idempotency_key="report-submission-idempotency-001",
            ),
        )

    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            report_recovery_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client("https://report.example", httpx.MockTransport(handler)),
    )

    receipt = adapter.recover_report_evidence_pack_receipt(
        report_evidence_pack(),
        access_scope=report_access_scope(),
        correlation_id="corr-report-recovery",
        trace_id="trace-report-recovery",
        idempotency_key="report-submission-idempotency-001",
    )

    assert receipt.owner_authority is SourceSystem.LOTUS_REPORT
    assert receipt.owner_request_id == "report-request-report-evidence-pack-001"
    assert receipt.owner_realization_id == "report-job-report-evidence-pack-001"
    assert captured["method"] == "GET"
    assert captured["path"] == "/reports/idea-evidence-packs/materializations"
    assert captured["query"] == {
        "idempotencyKey": "report-submission-idempotency-001",
        "reportEvidencePackId": "report-evidence-pack-001",
        "conversionIntentId": "conversion-report-001",
        "candidateId": "idea_high_cash_redacted",
        "evidencePacketId": "iep-redacted",
        "evidenceContentFingerprint": "sha256:evidence-redacted",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
    }
    headers = captured["headers"]
    assert headers["x-caller-application"] == "lotus-idea"
    assert headers["x-tenant-id"] == "tenant-sg"
    assert headers["x-capabilities"] == "report.idea-materialization.recover"
    assert headers["x-correlation-id"] == "corr-report-recovery"
    assert headers["x-trace-id"] == "trace-report-recovery"
    assert "idempotency-key" not in headers


@pytest.mark.parametrize("status_code", (404, 503))
def test_report_recovery_http_failure_exposes_no_untrusted_receipt(status_code: int) -> None:
    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            report_recovery_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client(
            "https://report.example",
            httpx.MockTransport(lambda _request: httpx.Response(status_code, json={})),
        ),
    )

    with pytest.raises(DownstreamRealizationReadError, match="Report materialization receipt"):
        adapter.recover_report_evidence_pack_receipt(
            report_evidence_pack(),
            access_scope=report_access_scope(),
            idempotency_key="report-submission-idempotency-001",
        )


def test_report_recovery_identity_conflict_is_distinct_from_owner_unavailability() -> None:
    adapter = HttpReportEvidencePackMaterializationClient(
        DownstreamRealizationAdapterConfig(
            base_url="https://report.example",
            submit_path="/reports/idea-evidence-packs/materializations",
            report_recovery_path="/reports/idea-evidence-packs/materializations",
            source_authority=SourceSystem.LOTUS_REPORT,
            report_service_context=report_service_context(),
        ),
        client=downstream_json_client(
            "https://report.example",
            httpx.MockTransport(lambda _request: httpx.Response(409, json={})),
        ),
    )

    with pytest.raises(DownstreamRealizationReadConflict):
        adapter.recover_report_evidence_pack_receipt(
            report_evidence_pack(),
            access_scope=report_access_scope(),
            idempotency_key="report-submission-idempotency-001",
        )
