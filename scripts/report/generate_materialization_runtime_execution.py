from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.report.materialization_runtime_execution import (  # noqa: E402
    build_report_materialization_runtime_execution_payload,
    source_safe_report_materialization_receipt_digest,
)
from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload  # noqa: E402


_REPORT_ASGI_PROBE = r"""
from datetime import UTC, datetime
import json
import sys
from tempfile import TemporaryDirectory
from pathlib import Path

from fastapi.testclient import TestClient

from app.idea_evidence_intake.service import IdeaEvidenceIntakeLedger
from app.main import app
from app.reporting_jobs.ledger import ReportJobLedger
from app.reporting_jobs.service import get_report_job_ledger
from app.reporting_lineage.models import (
    ReportInputSnapshotCreateRequest,
    ReportUpstreamCallCreateRequest,
)
from app.reporting_lineage.service import get_portfolio_review_snapshot_capture_service
from app.reporting_lineage.store import ReportInputSnapshotStore
from app.reporting_render.service import (
    PortfolioReviewRenderOrchestrationService,
    get_portfolio_review_render_orchestration_service,
)
from app.routers.idea_evidence_intake import get_idea_evidence_intake_ledger


def _payload() -> dict[str, object]:
    return {
        "report_evidence_pack_id": "irep_001",
        "conversion_intent_id": "icnv_001",
        "candidate_id": "icand_001",
        "purpose": "CLIENT_REPORT_EVIDENCE",
        "evidence_packet_id": "ievp_001",
        "evidence_content_fingerprint": "sha256:idea-evidence-content",
        "source_signal_ids": ["sig_high_cash_001"],
        "source_summaries": [
            {
                "product_id": "lotus-core:HoldingsAsOf:v1",
                "source_system": "lotus-core",
                "product_version": "v1",
                "as_of_date": "2026-06-24",
                "generated_at_utc": "2026-06-24T08:00:00Z",
                "data_quality_status": "complete",
                "freshness": "fresh",
            }
        ],
        "reason_codes": ["HIGH_CASH_REVIEWED_FOR_REPORT"],
        "report_source_authority": "lotus-report",
        "render_source_authority": "lotus-render",
        "archive_source_authority": "lotus-archive",
        "boundary": "REPORT_INTAKE_ONLY",
        "retention_policy_ref": "generated-report-standard",
        "requested_at_utc": "2026-06-24T08:15:00Z",
        "grants_client_publication_authority": False,
        "creates_rendered_output": False,
        "creates_archive_record": False,
        "producer": "lotus-idea",
        "supportability_status": "not_certified",
    }


def _materialization_payload() -> dict[str, object]:
    return {
        "idea_evidence_pack": _payload(),
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-06-24",
        "requested_output_formats": ["pdf"],
        "reporting_currency": "USD",
        "options": {"retention_policy_id": "generated-report-standard"},
        "boundary": "REPORT_JOB_MATERIALIZATION",
        "grants_client_publication_authority": False,
        "producer": "lotus-idea",
        "supportability_status": "not_certified",
    }


def _headers(idempotency_key: str) -> dict[str, str]:
    return {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": "advisor-123",
        "X-Caller-Application": "lotus-idea",
        "X-Tenant-Id": "tenant-sg",
        "X-Region": "APAC",
        "X-Booking-Center-Code": "SG",
        "X-Role": "advisor",
        "X-Correlation-ID": "corr-idea-report-intake",
        "X-Trace-ID": "trace-idea-report-intake",
    }


class _IdeaEvidenceCaptureService:
    def __init__(self, ledger: ReportJobLedger, lineage_store: ReportInputSnapshotStore) -> None:
        self._ledger = ledger
        self._lineage_store = lineage_store

    async def capture_for_job(self, job):
        self._ledger.mark_collecting_data(
            job_id=job.job_id,
            actor=job.triggered_by,
            correlation_id=job.correlation_id,
            trace_id=job.trace_id,
        )
        report_input = job.options["proof_pack_report_input"]
        snapshot = self._lineage_store.create_snapshot(
            ReportInputSnapshotCreateRequest(
                report_job_id=job.job_id,
                report_type=job.report_type,
                report_data_contract_version="dpm_proof_pack_report_input.v1",
                portfolio_scope=job.portfolio_scope,
                as_of_date=job.as_of_date,
                snapshot_payload=report_input,
                snapshot_storage_ref=None,
                supportability_status="complete",
                completeness_status="complete",
                lineage_summary={
                    "source_services": ["lotus-idea"],
                    "call_count": 1,
                    "supportability_status": "complete",
                    "completeness_status": "complete",
                    "proof_pack_id": report_input["proof_pack_id"],
                    "source_type": "LOTUS_IDEA_EVIDENCE_PACK_REPORT_INPUT",
                    "source_hash": report_input["content_hash"],
                },
                captured_at=datetime.now(UTC),
                correlation_id=job.correlation_id,
                trace_id=job.trace_id,
            )
        )
        self._lineage_store.create_upstream_calls(
            snapshot_id=snapshot.snapshot_id,
            calls=[
                ReportUpstreamCallCreateRequest(
                    service_name="lotus-idea",
                    endpoint="/reports/idea-evidence-packs/materializations",
                    method="POST",
                    contract_version="LotusIdeaEvidencePackReportInput.1.0",
                    request_hash=report_input["proof_pack_content_hash"],
                    response_hash=report_input["content_hash"],
                    response_ref=report_input["evidence_ref"]["source_id"],
                    status_code=200,
                    latency_ms=0,
                    supportability_status="complete",
                    completeness_status="complete",
                    failure_category="none",
                    failure_message=None,
                    captured_at=datetime.now(UTC),
                    correlation_id=job.correlation_id,
                    trace_id=job.trace_id,
                )
            ],
        )
        return self._ledger.mark_data_ready(
            job_id=job.job_id,
            actor=job.triggered_by,
            correlation_id=job.correlation_id,
            trace_id=job.trace_id,
        )


class _SuccessfulRenderClient:
    async def submit_render_package(self, payload, **kwargs):
        return 201, {
            "status": "rendered",
            "render_job_id": payload["render_job_id"],
            "artifact_sha256": "sha256:idea-evidence-rendered-pdf",
            "bounded_determinism_fingerprint": "fingerprint-idea-evidence",
            "runtime_engine": "typst",
            "runtime_engine_version": "0.14.2",
            "render_duration_ms": 420,
            "artifact_base64": "JVBERi0xLjQ=",
        }


class _SuccessfulArchiveClient:
    async def archive_document(self, payload, **kwargs):
        return 201, {"document_id": "doc_idea_evidence_pack_001"}


class _UnavailableArchiveClient:
    async def archive_document(self, payload, **kwargs):
        return 503, {
            "detail": {
                "code": "archive_unavailable",
                "message": "Archive is temporarily unavailable.",
            }
        }


class _UnexpectedRenderClient:
    async def submit_render_package(self, payload, **kwargs):
        raise AssertionError("JSON-only materialization must not call render")


class _UnexpectedArchiveClient:
    async def archive_document(self, payload, **kwargs):
        raise AssertionError("JSON-only materialization must not call archive")


def _receipt(response, *, forced_codes=None) -> dict[str, object]:
    status_code = response.status_code
    body = response.json()
    if status_code == 202:
        codes = list(body.get("remaining_blockers") or [])
        if body.get("materialization_status") == "failed":
            codes = ["archive_storage_failed", *codes]
        return {
            "statusCode": status_code,
            "materializationStatus": body.get("materialization_status"),
            "materializationProven": body.get("materialization_proven") is True,
            "reportJobCreated": body.get("creates_report_job") is True,
            "renderedOutputCreated": body.get("creates_rendered_output") is True,
            "archiveRecordCreated": body.get("creates_archive_record") is True,
            "clientPublicationAuthorized": body.get("grants_client_publication_authority") is True,
            "supportedFeaturePromoted": body.get("supported_feature_promoted") is True,
            "supportabilityStatus": body.get("supportability_status"),
            "receiptDigest": None,
            "reasonCodes": codes,
        }
    detail = body.get("detail") if isinstance(body, dict) else None
    code = detail.get("code") if isinstance(detail, dict) else None
    return {
        "statusCode": status_code,
        "materializationStatus": None,
        "materializationProven": False,
        "reportJobCreated": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "supportabilityStatus": None,
        "receiptDigest": None,
        "reasonCodes": list(forced_codes or ([code] if code else [])),
    }


def _client_with_services(tmp_path, *, archive_failure=False, json_only=False):
    ledger = ReportJobLedger(Path(tmp_path) / "jobs.sqlite3")
    lineage_store = ReportInputSnapshotStore(Path(tmp_path) / "lineage.sqlite3")
    capture_service = _IdeaEvidenceCaptureService(ledger, lineage_store)
    render_client = _UnexpectedRenderClient() if json_only else _SuccessfulRenderClient()
    archive_client = (
        _UnavailableArchiveClient()
        if archive_failure
        else (_UnexpectedArchiveClient() if json_only else _SuccessfulArchiveClient())
    )
    render_service = PortfolioReviewRenderOrchestrationService(
        render_client=render_client,
        archive_client=archive_client,
        snapshot_store=lineage_store,
        job_ledger=ledger,
    )
    app.dependency_overrides[get_report_job_ledger] = lambda: ledger
    app.dependency_overrides[get_idea_evidence_intake_ledger] = lambda: IdeaEvidenceIntakeLedger()
    app.dependency_overrides[get_portfolio_review_snapshot_capture_service] = lambda: (
        capture_service
    )
    app.dependency_overrides[get_portfolio_review_render_orchestration_service] = lambda: (
        render_service
    )
    return TestClient(app)


def main() -> None:
    receipts = {}
    with TemporaryDirectory(prefix="lotus-report-materialization-runtime-") as tmp:
        client = _client_with_services(tmp)
        try:
            accepted = client.post(
                "/reports/idea-evidence-packs/materializations",
                json=_materialization_payload(),
                headers=_headers("idea-report-materialization-001"),
            )
            replay = client.post(
                "/reports/idea-evidence-packs/materializations",
                json=_materialization_payload(),
                headers=_headers("idea-report-materialization-001"),
            )
            changed = {
                **_materialization_payload(),
                "reporting_currency": "SGD",
            }
            conflict = client.post(
                "/reports/idea-evidence-packs/materializations",
                json=changed,
                headers=_headers("idea-report-materialization-001"),
            )
        finally:
            app.dependency_overrides.clear()
        receipts["acceptedArchived"] = _receipt(accepted)
        receipts["acceptedReplay"] = _receipt(replay)
        receipts["idempotencyConflict"] = _receipt(conflict)

    with TemporaryDirectory(prefix="lotus-report-materialization-json-") as tmp:
        client = _client_with_services(tmp, json_only=True)
        payload = {**_materialization_payload(), "requested_output_formats": ["json"]}
        try:
            json_only = client.post(
                "/reports/idea-evidence-packs/materializations",
                json=payload,
                headers=_headers("idea-report-materialization-json-only"),
            )
        finally:
            app.dependency_overrides.clear()
        receipts["jsonOnlyAccepted"] = _receipt(json_only)

    with TemporaryDirectory(prefix="lotus-report-materialization-archive-failure-") as tmp:
        client = _client_with_services(tmp, archive_failure=True)
        try:
            archive_failure = client.post(
                "/reports/idea-evidence-packs/materializations",
                json=_materialization_payload(),
                headers=_headers("idea-report-materialization-archive-failure"),
            )
        finally:
            app.dependency_overrides.clear()
        receipts["archiveFailure"] = _receipt(archive_failure)

    client = TestClient(app)
    headers = _headers("idea-report-materialization-missing-key")
    headers.pop("Idempotency-Key")
    receipts["missingIdempotencyKey"] = _receipt(
        client.post(
            "/reports/idea-evidence-packs/materializations",
            json=_materialization_payload(),
            headers=headers,
        )
    )
    publication_payload = {
        **_materialization_payload(),
        "grants_client_publication_authority": True,
    }
    receipts["clientPublicationDenied"] = _receipt(
        client.post(
            "/reports/idea-evidence-packs/materializations",
            json=publication_payload,
            headers=_headers("idea-report-materialization-publication-denied"),
        ),
        forced_codes=["client_publication_authority_blocked"],
    )
    print(json.dumps(receipts, sort_keys=True))


main()
"""


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
        report_root = Path(args.report_root).resolve()
        receipt_evidence = _generate_local_asgi_receipts(
            report_root=report_root,
            report_python=args.report_python,
        )
        for receipt in receipt_evidence.values():
            receipt["receiptDigest"] = source_safe_report_materialization_receipt_digest(receipt)
        payload = build_report_materialization_runtime_execution_payload(
            generated_at_utc=generated_at_utc,
            repository_root=Path.cwd(),
            report_root=report_root,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=receipt_evidence,
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"report materialization runtime execution proof error: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        print(
            f"report materialization runtime execution proof error: {detail}",
            file=sys.stderr,
        )
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate receipt-bound lotus-report materialization runtime proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--report-root", default="../lotus-report")
    parser.add_argument("--report-python", default=sys.executable)
    parser.add_argument("--output")
    return parser


def _generate_local_asgi_receipts(
    *,
    report_root: Path,
    report_python: str,
) -> dict[str, dict[str, Any]]:
    result = subprocess.run(
        [report_python, "-c", _report_probe_source(report_root)],
        cwd=report_root,
        check=True,
        capture_output=True,
        text=True,
    )
    receipts = json.loads(result.stdout)
    if not isinstance(receipts, dict):
        raise ValueError("report runtime probe must emit a JSON object")
    return {str(key): dict(value) for key, value in receipts.items() if isinstance(value, dict)}


def _report_probe_source(report_root: Path) -> str:
    src_path = report_root / "src"
    prefix = f"import sys; sys.path.insert(0, {str(src_path)!r});\n"
    return prefix + textwrap.dedent(_REPORT_ASGI_PROBE)


if __name__ == "__main__":
    sys.exit(main())
