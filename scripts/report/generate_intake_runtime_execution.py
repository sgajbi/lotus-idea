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

from app.application.report.intake_runtime_execution import (  # noqa: E402
    build_report_intake_runtime_execution_payload,
    source_safe_report_intake_receipt_digest,
)
from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload  # noqa: E402


_REPORT_ASGI_PROBE = r"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.idea_evidence_intake.service import IdeaEvidenceIntakeLedger
from app.main import app
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


def _client(tmp_path):
    ledger = IdeaEvidenceIntakeLedger(Path(tmp_path) / "idea-evidence-intake.sqlite3")
    app.dependency_overrides[get_idea_evidence_intake_ledger] = lambda: ledger
    return TestClient(app)


def _receipt(response, *, forced_codes=None) -> dict[str, object]:
    status_code = response.status_code
    body = response.json()
    if status_code == 202:
        return {
            "statusCode": status_code,
            "intakeStatus": body.get("intake_status"),
            "routeExistenceProven": body.get("route_existence_proven") is True,
            "materializationProven": body.get("materialization_proven") is True,
            "reportJobCreated": body.get("creates_report_job") is True,
            "renderedOutputCreated": body.get("creates_rendered_output") is True,
            "archiveRecordCreated": body.get("creates_archive_record") is True,
            "clientPublicationAuthorized": body.get("grants_client_publication_authority") is True,
            "supportedFeaturePromoted": False,
            "supportabilityStatus": body.get("supportability_status"),
            "receiptDigest": None,
            "reasonCodes": list(body.get("remaining_blockers") or []),
        }
    detail = body.get("detail") if isinstance(body, dict) else None
    code = detail.get("code") if isinstance(detail, dict) else None
    return {
        "statusCode": status_code,
        "intakeStatus": None,
        "routeExistenceProven": False,
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


def main() -> None:
    receipts = {}
    with TemporaryDirectory(prefix="lotus-report-intake-runtime-") as tmp:
        client = _client(tmp)
        try:
            accepted = client.post(
                "/reports/idea-evidence-packs",
                json=_payload(),
                headers=_headers("idea-report-intake-001"),
            )
            replay = client.post(
                "/reports/idea-evidence-packs",
                json=_payload(),
                headers=_headers("idea-report-intake-001"),
            )
            changed = {
                **_payload(),
                "reason_codes": ["DIFFERENT_REPORT_REASON"],
            }
            conflict = client.post(
                "/reports/idea-evidence-packs",
                json=changed,
                headers=_headers("idea-report-intake-001"),
            )
        finally:
            app.dependency_overrides.clear()
        receipts["accepted"] = _receipt(accepted)
        receipts["acceptedReplay"] = _receipt(replay)
        receipts["idempotencyConflict"] = _receipt(conflict)

    with TemporaryDirectory(prefix="lotus-report-intake-rejections-") as tmp:
        client = _client(tmp)
        headers = _headers("idea-report-intake-missing-key")
        headers.pop("Idempotency-Key")
        publication_payload = {**_payload(), "grants_client_publication_authority": True}
        render_claim_payload = {**_payload(), "creates_rendered_output": True}
        try:
            missing_idempotency_key = client.post(
                "/reports/idea-evidence-packs",
                json=_payload(),
                headers=headers,
            )
            client_publication_denied = client.post(
                "/reports/idea-evidence-packs",
                json=publication_payload,
                headers=_headers("idea-report-intake-publication-denied"),
            )
            render_claim_denied = client.post(
                "/reports/idea-evidence-packs",
                json=render_claim_payload,
                headers=_headers("idea-report-intake-render-claim-denied"),
            )
        finally:
            app.dependency_overrides.clear()
        receipts["missingIdempotencyKey"] = _receipt(missing_idempotency_key)
        receipts["clientPublicationDenied"] = _receipt(
            client_publication_denied,
            forced_codes=["client_publication_authority_blocked"],
        )
        receipts["renderClaimDenied"] = _receipt(
            render_claim_denied,
            forced_codes=["render_archive_authority_blocked"],
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
            receipt["receiptDigest"] = source_safe_report_intake_receipt_digest(receipt)
        payload = build_report_intake_runtime_execution_payload(
            generated_at_utc=generated_at_utc,
            repository_root=Path.cwd(),
            report_root=report_root,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=receipt_evidence,
        )
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"report intake runtime execution proof error: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"report intake runtime execution proof error: {detail}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate receipt-bound lotus-report intake runtime proof."
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
        raise ValueError("report intake runtime probe must emit a JSON object")
    return {str(key): dict(value) for key, value in receipts.items() if isinstance(value, dict)}


def _report_probe_source(report_root: Path) -> str:
    src_path = report_root / "src"
    prefix = f"import sys; sys.path.insert(0, {str(src_path)!r});\n"
    return prefix + textwrap.dedent(_REPORT_ASGI_PROBE)


if __name__ == "__main__":
    sys.exit(main())
