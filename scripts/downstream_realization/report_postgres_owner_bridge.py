from __future__ import annotations

import json
import importlib
import os
from pathlib import Path
import sys
from typing import Any


class _RetainAcceptedCaptureService:
    """Leave the owner job at its first durable state for recovery tests."""

    async def capture_for_job(self, job: Any) -> Any:
        return job


class _UnexpectedRenderService:
    async def render_for_job(self, job: Any) -> Any:
        raise AssertionError("JSON-only Report recovery proof must not invoke rendering")


def main() -> int:
    report_root = Path(os.environ["LOTUS_REPORT_ROOT"]).resolve()
    sys.path.insert(0, str(report_root / "src"))

    from fastapi.testclient import TestClient

    app = importlib.import_module("app.main").app
    get_report_job_ledger = importlib.import_module(
        "app.reporting_jobs.service"
    ).get_report_job_ledger
    get_portfolio_review_snapshot_capture_service = importlib.import_module(
        "app.reporting_lineage.service"
    ).get_portfolio_review_snapshot_capture_service
    get_portfolio_review_render_orchestration_service = importlib.import_module(
        "app.reporting_render.service"
    ).get_portfolio_review_render_orchestration_service

    request = _request_from_stdin()
    if request["method"] == "ADVANCE_COLLECTING":
        ledger = get_report_job_ledger()
        job = ledger.get_job(request["jobId"])
        advanced = ledger.mark_collecting_data(
            job_id=job.job_id,
            actor=job.triggered_by,
            correlation_id=job.correlation_id,
            trace_id=job.trace_id,
        )
        print(
            json.dumps(
                {"statusCode": 200, "body": {"jobId": advanced.job_id, "status": advanced.status}},
                sort_keys=True,
            )
        )
        return 0

    app.dependency_overrides[get_portfolio_review_snapshot_capture_service] = (
        _RetainAcceptedCaptureService
    )
    app.dependency_overrides[get_portfolio_review_render_orchestration_service] = (
        _UnexpectedRenderService
    )
    try:
        with TestClient(app) as client:
            response = client.request(
                request["method"],
                request["path"],
                json=request.get("json"),
                params=request.get("params"),
                headers=request.get("headers"),
            )
    finally:
        app.dependency_overrides.clear()
    print(json.dumps({"statusCode": response.status_code, "body": response.json()}, sort_keys=True))
    return 0


def _request_from_stdin() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("owner bridge request must be an object")
    method = value.get("method")
    if method == "ADVANCE_COLLECTING":
        job_id = value.get("jobId")
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("owner bridge advancement requires jobId")
        return value
    path = value.get("path")
    if method not in {"GET", "POST"}:
        raise ValueError("owner bridge method must be GET, POST, or ADVANCE_COLLECTING")
    if not isinstance(path, str) or not path.startswith(
        "/reports/idea-evidence-packs/materializations"
    ):
        raise ValueError("owner bridge path must target the governed Idea materialization route")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
