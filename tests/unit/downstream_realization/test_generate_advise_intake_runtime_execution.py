from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_OWNER_RESTART_TEST_NODES,
    IDEA_ADVISE_RECONCILIATION_TEST_NODES,
)
from scripts.downstream_realization import generate_advise_intake_runtime_execution as generator
from scripts.downstream_realization import advise_postgres_restart_evidence as postgres_evidence


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
        "concurrentAccepted",
        "concurrentReplay",
        "rejected",
        "idempotencyConflict",
        "authorizationDenied",
        "tenantScopedIdempotency",
        "ownerRealization",
        "ownerAdvancement",
        "submittedIntent",
        "preCommitTimeout",
    }
    assert captured["args"][0:2] == ["python-test", "-c"]
    assert "acceptedReplay" in captured["args"][2]
    assert "ThreadPoolExecutor" in captured["args"][2]
    assert "/realization" in captured["args"][2]
    assert "reset_proposal_workflow_service_for_tests" in captured["args"][2]
    assert "InMemoryProposalRepository" in captured["args"][2]
    assert "preCommitTimeout" in captured["args"][2]
    assert "stale_owner_correction" in captured["args"][2]
    assert "concurrent_owner_advancement" in captured["args"][2]
    assert '"failureStage": "before_owner_request_dispatch"' in captured["args"][2]
    assert '"portfolio_id": "PB_SG_GLOBAL_BAL_001"' in captured["args"][2]
    assert "authorizationDenied" in captured["args"][2]
    assert captured["cwd"] == tmp_path
    assert captured["check"] is True
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["env"]["PYTHONPATH"] == str(tmp_path.resolve())
    assert captured["env"]["ENVIRONMENT"] == "test"
    assert captured["env"]["IDEA_PROPOSAL_RECONCILIATION_ENABLED"] == "true"
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
    assert accepted["ownerIdentityDigest"].startswith("sha256:")
    assert accepted["scopeDigest"].startswith("sha256:")

    conflict = receipts["idempotencyConflict"]
    assert conflict["statusCode"] == 409
    assert conflict["reasonCodes"] == ["IDEA_PROPOSAL_INTAKE_IDEMPOTENCY_CONFLICT"]

    owner = receipts["ownerRealization"]
    assert owner["statusCode"] == 200
    assert owner["ownerIdentityDigest"] == accepted["ownerIdentityDigest"]
    assert owner["scopeDigest"] == accepted["scopeDigest"]
    assert owner["currentSourceEventVersion"] == 1
    advancement = receipts["ownerAdvancement"]
    assert advancement["staleCorrectionStatusCode"] == 409
    assert advancement["sourceEventVersionAfterRefusal"] == 2
    assert advancement["concurrentStatusCodes"] == [200, 200]
    assert advancement["concurrentSourceEventVersions"] == [3, 3]
    assert advancement["finalOutcomeVersions"] == [1, 2, 3]
    assert advancement["finalStatus"] == "ADVISORY_REJECTED"

    submitted = receipts["submittedIntent"]
    assert submitted["scopeDigest"].startswith("sha256:")
    assert submitted["sourceIntentDigest"].startswith("sha256:")
    pre_commit_timeout = receipts["preCommitTimeout"]
    assert pre_commit_timeout["failureStage"] == "before_owner_request_dispatch"
    assert pre_commit_timeout["ownerLookupStatusCode"] == 404
    assert pre_commit_timeout["repeatedOwnerLookupStatusCode"] == 404
    assert pre_commit_timeout["downstreamPostAttemptCount"] == 0
    assert pre_commit_timeout["automaticResubmissionAttemptCount"] == 0
    assert pre_commit_timeout["ownerStateObserved"] is False
    serialized_evidence = json.dumps(receipts)
    for forbidden_marker in (
        "portfolioId",
        "candidateId",
        "tenantId",
        "legalEntityCode",
        "intakeId",
        "realizationId",
        "reviewWorkId",
        "conversionIntentId",
    ):
        assert forbidden_marker not in serialized_evidence


def test_advise_testclient_stdout_decoder_rejects_non_object() -> None:
    with pytest.raises(
        ValueError,
        match="Advise testclient execution did not return a JSON object",
    ):
        generator._json_object_from_stdout(
            "[1, 2, 3]",
            "Advise testclient execution did not return a JSON object",
        )


def test_advise_postgres_restart_tests_emit_source_safe_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_source = (
        tmp_path / "tests/integration/advisory/engine/"
        "test_engine_proposal_repository_postgres_integration.py"
    )
    test_source.parent.mkdir(parents=True)
    test_source.write_text("def test_restart(): pass\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(
        args: list[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured.update(args=args, cwd=cwd, env=dict(env), check=check)
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="2 passed", stderr="")

    monkeypatch.setattr(
        "scripts.downstream_realization.advise_postgres_restart_evidence.subprocess.run",
        fake_run,
    )
    evidence = postgres_evidence.execute_advise_postgres_restart_tests(
        advise_root=tmp_path,
        advise_python="python-owner",
        postgres_dsn="postgresql://test-only",
        allow_database_reset=True,
    )

    assert captured["args"] == [
        "python-owner",
        "-m",
        "pytest",
        *ADVISE_OWNER_RESTART_TEST_NODES,
        "-q",
    ]
    assert captured["cwd"] == tmp_path
    assert captured["env"]["PROPOSAL_POSTGRES_INTEGRATION_DSN"] == "postgresql://test-only"  # type: ignore[index]
    assert evidence["testProcessExitCode"] == 0
    assert evidence["testPassedCount"] == 2
    assert evidence["restartOutcomeVersions"] == (1, 2, 3)
    assert evidence["ownerHistoryUnchangedAcrossRestart"] is True
    assert evidence["ownerIdentitiesUnchangedAcrossRestart"] is True
    assert evidence["duplicateOwnerWorkCount"] == 0
    assert evidence["testSourceDigest"].startswith("sha256:")
    assert "postgresql://test-only" not in json.dumps(evidence)


@pytest.mark.parametrize(
    ("postgres_dsn", "allow_database_reset", "message"),
    (
        ("", True, "--advise-postgres-dsn is required"),
        ("postgresql://test-only", False, "--allow-destructive-test-database-reset is required"),
    ),
)
def test_advise_postgres_restart_tests_require_explicit_disposable_database_authority(
    tmp_path: Path,
    postgres_dsn: str,
    allow_database_reset: bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        postgres_evidence.execute_advise_postgres_restart_tests(
            advise_root=tmp_path,
            advise_python="python-owner",
            postgres_dsn=postgres_dsn,
            allow_database_reset=allow_database_reset,
        )


def test_advise_postgres_restart_tests_reject_skipped_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_source = (
        tmp_path / "tests/integration/advisory/engine/"
        "test_engine_proposal_repository_postgres_integration.py"
    )
    test_source.parent.mkdir(parents=True)
    test_source.write_text("def test_restart(): pass\n", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.downstream_realization.advise_postgres_restart_evidence.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="2 skipped", stderr=""
        ),
    )

    with pytest.raises(ValueError, match="requires exactly two passed tests"):
        postgres_evidence.execute_advise_postgres_restart_tests(
            advise_root=tmp_path,
            advise_python="python-owner",
            postgres_dsn="postgresql://test-only",
            allow_database_reset=True,
        )


def test_idea_postgres_reconciliation_test_emits_zero_delta_replay_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_source = tmp_path / "tests/integration/test_postgres_downstream_submission_runtime.py"
    test_source.parent.mkdir(parents=True)
    test_source.write_text("def test_reconciliation(): pass\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(
        args: list[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured.update(args=args, cwd=cwd, env=dict(env), check=check)
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed", stderr="")

    monkeypatch.setattr(
        "scripts.downstream_realization.advise_postgres_restart_evidence.subprocess.run",
        fake_run,
    )
    evidence = postgres_evidence.execute_idea_postgres_reconciliation_test(
        repository_root=tmp_path,
        idea_python="python-idea",
        postgres_dsn="postgresql://idea-test-only",
        allow_database_reset=True,
    )

    assert captured["args"] == [
        "python-idea",
        "-m",
        "pytest",
        *IDEA_ADVISE_RECONCILIATION_TEST_NODES,
        "-q",
    ]
    assert captured["cwd"] == tmp_path
    assert captured["env"]["LOTUS_IDEA_POSTGRES_INTEGRATION_URL"] == (  # type: ignore[index]
        "postgresql://idea-test-only"
    )
    assert captured["env"]["LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED"] == "1"  # type: ignore[index]
    assert evidence["firstReconciliationAppendedOutcomeCount"] == 3
    assert evidence["exactReplayAppendedOutcomeCount"] == 0
    assert evidence["submissionAttemptCount"] == 1
    assert evidence["ownerIdentityUnchanged"] is True
    assert evidence["governedTableCountsUnchangedOnReplay"] is True
    assert "postgresql://idea-test-only" not in json.dumps(evidence)


@pytest.mark.parametrize(
    ("postgres_dsn", "allow_database_reset", "message"),
    (
        ("", True, "--idea-postgres-dsn is required"),
        (
            "postgresql://idea-test-only",
            False,
            "--allow-destructive-test-database-reset is required",
        ),
    ),
)
def test_idea_postgres_reconciliation_test_requires_disposable_database_authority(
    tmp_path: Path,
    postgres_dsn: str,
    allow_database_reset: bool,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        postgres_evidence.execute_idea_postgres_reconciliation_test(
            repository_root=tmp_path,
            idea_python="python-idea",
            postgres_dsn=postgres_dsn,
            allow_database_reset=allow_database_reset,
        )


def test_idea_postgres_reconciliation_test_rejects_skipped_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_source = tmp_path / "tests/integration/test_postgres_downstream_submission_runtime.py"
    test_source.parent.mkdir(parents=True)
    test_source.write_text("def test_reconciliation(): pass\n", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.downstream_realization.advise_postgres_restart_evidence.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="1 skipped", stderr=""
        ),
    )

    with pytest.raises(ValueError, match="requires exactly one passed test"):
        postgres_evidence.execute_idea_postgres_reconciliation_test(
            repository_root=tmp_path,
            idea_python="python-idea",
            postgres_dsn="postgresql://idea-test-only",
            allow_database_reset=True,
        )


def _advise_receipt_responses() -> dict[str, dict[str, object]]:
    responses = {
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
        "concurrentAccepted": _response(
            status_code=202,
            intake_status="ACCEPTED",
            accepted=True,
            replay=False,
            reason_codes=["idea_intake_receipt_accepted"],
        ),
        "concurrentReplay": _response(
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
    responses["ownerRealization"] = {
        "statusCode": 200,
        "body": {
            "intake_id": "ipi_001",
            "realization_id": "ipr_001",
            "review_work_id": "iarw_001",
            "review_work_status": "PENDING_ADVISER_REVIEW",
            "tenant_id": "tenant-private-bank-sg",
            "legal_entity_code": "SGPB",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "source_evidence_fingerprint": "sha256:" + "a" * 64,
            "current_status": "ACCEPTED_FOR_REVIEW",
            "current_source_event_version": 1,
            "proposal_id": None,
            "proposal_record_created": False,
            "suitability_authority_granted": False,
            "order_created": False,
            "client_publication_authorized": False,
            "outcomes": [{"source_event_version": 1, "status": "ACCEPTED_FOR_REVIEW"}],
        },
    }
    responses["submittedIntent"] = {
        "ideaCandidateId": "idea_candidate_001",
        "conversionIntentId": "conversion_intent_001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "tenantId": "tenant-private-bank-sg",
        "legalEntityCode": "SGPB",
    }
    linked_history = _owner_history_response(version=2)
    final_history = _owner_history_response(version=3)
    responses["ownerAdvancement"] = {
        "linked": linked_history,
        "staleCorrection": _error_response(
            status_code=409,
            detail="IDEA_PROPOSAL_REALIZATION_VERSION_CONFLICT",
        ),
        "afterStaleCorrection": linked_history,
        "concurrentAdvancement": [final_history, final_history],
        "finalReadback": final_history,
    }
    responses["preCommitTimeout"] = {
        "failureStage": "before_owner_request_dispatch",
        "downstreamPostAttemptCount": 0,
        "automaticResubmissionAttemptCount": 0,
        "ownerStateObserved": False,
        "ideaCandidateId": "idea_candidate_precommit_timeout_001",
        "conversionIntentId": "conversion_intent_precommit_timeout_001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "tenantId": "tenant-private-bank-sg",
        "legalEntityCode": "SGPB",
        "ownerLookup": _error_response(
            status_code=404,
            detail="IDEA_PROPOSAL_REALIZATION_NOT_FOUND",
        ),
        "repeatedOwnerLookup": _error_response(
            status_code=404,
            detail="IDEA_PROPOSAL_REALIZATION_NOT_FOUND",
        ),
    }
    return responses


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
            "intake_id": "ipi_001",
            "realization_id": "ipr_001",
            "review_work_id": "iarw_001",
            "review_work_status": "PENDING_ADVISER_REVIEW",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "idea_candidate_id": "idea_candidate_001",
            "conversion_intent_id": "conversion_intent_001",
            "source_evidence_fingerprint": "sha256:" + "a" * 64,
            "realization_status": "ACCEPTED_FOR_REVIEW",
            "source_event_version": 1,
            "trusted_scope": {
                "tenant_id": "tenant-private-bank-sg",
                "legal_entity_code": "SGPB",
            },
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


def _owner_history_response(*, version: int) -> dict[str, object]:
    outcomes: list[dict[str, object]] = [
        {
            "source_event_version": 1,
            "status": "ACCEPTED_FOR_REVIEW",
            "reason_code": "idea_intake_accepted_for_adviser_review",
            "review_work_id": "iarw_001",
            "proposal_id": None,
            "terminal": False,
        },
        {
            "source_event_version": 2,
            "status": "PROPOSAL_LINKED",
            "reason_code": "advise_proposal_linked",
            "review_work_id": "iarw_001",
            "proposal_id": "proposal-001",
            "terminal": False,
        },
    ]
    if version == 3:
        outcomes.append(
            {
                "source_event_version": 3,
                "status": "ADVISORY_REJECTED",
                "reason_code": "advise_proposal_rejected",
                "review_work_id": "iarw_001",
                "proposal_id": "proposal-001",
                "terminal": True,
            }
        )
    return {
        "statusCode": 200,
        "body": {
            "intake_id": "ipi_001",
            "realization_id": "ipr_001",
            "review_work_id": "iarw_001",
            "review_work_status": "CLOSED" if version == 3 else "PROPOSAL_LINKED",
            "tenant_id": "tenant-private-bank-sg",
            "legal_entity_code": "SGPB",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "idea_candidate_id": "idea_candidate_001",
            "conversion_intent_id": "conversion_intent_001",
            "source_evidence_fingerprint": "sha256:" + "a" * 64,
            "current_status": "ADVISORY_REJECTED" if version == 3 else "PROPOSAL_LINKED",
            "current_source_event_version": version,
            "proposal_id": "proposal-001",
            "proposal_record_created": True,
            "suitability_authority_granted": False,
            "order_created": False,
            "client_publication_authorized": False,
            "outcomes": outcomes,
        },
    }
