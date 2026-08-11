from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from scripts.downstream_realization import generate_advise_intake_runtime_execution as generator


def test_advise_testclient_execution_runs_source_safe_scenarios(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(
        args: list[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured.update(
            {
                "args": args,
                "cwd": cwd,
                "env": dict(env),
                "check": check,
                "capture_output": capture_output,
                "text": text,
            }
        )
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(_advise_receipt_responses()),
            stderr="",
        )

    monkeypatch.setattr(
        "scripts.downstream_realization.generate_advise_intake_runtime_execution.subprocess.run",
        fake_run,
    )

    receipts = generator._execute_advise_testclient(
        advise_root=tmp_path,
        advise_python="python-test",
    )

    assert set(receipts) == {
        "accepted",
        "acceptedReplay",
        "rejected",
        "idempotencyConflict",
        "authorizationDenied",
        "tenantScopedIdempotency",
    }
    assert captured["args"][0:2] == ["python-test", "-c"]
    assert "acceptedReplay" in captured["args"][2]
    assert "authorizationDenied" in captured["args"][2]
    assert captured["cwd"] == tmp_path
    assert captured["check"] is True
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["env"]["PYTHONPATH"] == str(tmp_path.resolve())
    assert captured["env"]["ENVIRONMENT"] == "test"
    assert captured["env"]["PROPOSAL_STORE_BACKEND"] == "POSTGRES"
    assert captured["env"]["POLICY_STORE_BACKEND"] == "POSTGRES"
    assert captured["env"]["WORKSPACE_STORE_BACKEND"] == "POSTGRES"

    accepted = receipts["accepted"]
    assert accepted["statusCode"] == 202
    assert accepted["intakeStatus"] == "ACCEPTED"
    assert accepted["intakeReceiptAccepted"] is True
    assert accepted["idempotencyReplay"] is False
    assert accepted["proposalRecordCreated"] is False
    assert accepted["suitabilityAuthorityGranted"] is False
    assert accepted["orderCreated"] is False
    assert accepted["clientPublicationAuthorized"] is False
    assert isinstance(accepted["receiptDigest"], str)

    conflict = receipts["idempotencyConflict"]
    assert conflict["statusCode"] == 409
    assert conflict["reasonCodes"] == ["IDEA_PROPOSAL_INTAKE_IDEMPOTENCY_CONFLICT"]


def test_advise_testclient_stdout_decoder_rejects_non_object() -> None:
    with pytest.raises(
        ValueError,
        match="Advise testclient execution did not return a JSON object",
    ):
        generator._json_object_from_stdout(
            "[1, 2, 3]",
            "Advise testclient execution did not return a JSON object",
        )


def _advise_receipt_responses() -> dict[str, dict[str, object]]:
    return {
        "accepted": _response(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=["idea_intake_receipt_accepted"],
        ),
        "acceptedReplay": _response(
            status_code=202,
            intake_status="ACCEPTED_REPLAYED",
            accepted=True,
            replay=True,
            reason_codes=["idea_intake_receipt_replayed"],
        ),
        "rejected": _response(
            status_code=202,
            intake_status="REJECTED",
            accepted=False,
            replay=False,
            reason_codes=["idea_intake_receipt_rejected_no_proposal_created"],
        ),
        "idempotencyConflict": _error_response(
            status_code=409,
            detail="IDEA_PROPOSAL_INTAKE_IDEMPOTENCY_CONFLICT",
        ),
        "authorizationDenied": _error_response(
            status_code=403,
            detail="IDEA_PROPOSAL_INTAKE_CAPABILITY_REQUIRED",
        ),
        "tenantScopedIdempotency": _response(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=["idea_intake_receipt_accepted"],
        ),
    }


def _response(
    *,
    status_code: int,
    intake_status: str,
    accepted: bool,
    replay: bool,
    reason_codes: list[str],
) -> dict[str, object]:
    return {
        "statusCode": status_code,
        "body": {
            "intake_status": intake_status,
            "intake_receipt_accepted": accepted,
            "idempotency_replay": replay,
            "outcome_reason_codes": reason_codes,
            "proposal_record_created": False,
            "suitability_authority_granted": False,
            "order_created": False,
            "client_publication_authorized": False,
        },
    }


def _error_response(*, status_code: int, detail: str) -> dict[str, object]:
    return {"statusCode": status_code, "body": {"detail": detail}}
