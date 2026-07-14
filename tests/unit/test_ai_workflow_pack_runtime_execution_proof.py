from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from app.application.ai_runtime_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED,
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION,
    REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS,
    InvalidAIRuntimeExecutionReceipt,
    ai_workflow_pack_runtime_execution_proof_is_valid,
    build_ai_workflow_pack_runtime_execution_proof_payload,
    build_unavailable_ai_workflow_pack_runtime_execution_proof_payload,
    execute_ai_workflow_pack_runtime_proof,
)
from tests.support.ai_runtime_proof import (
    ai_runtime_execution_receipt,
    lotus_ai_runtime_execution_response,
)

ROOT = Path(__file__).resolve().parents[2]


class RecordingRuntime:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.requests: list[tuple[Mapping[str, object], str]] = []

    def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]:
        self.requests.append((request, caller_app))
        return self.response


def test_builds_source_safe_proof_from_actual_execution_receipt() -> None:
    proof = _valid_proof()

    assert proof["schemaVersion"] == AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_SCHEMA_VERSION
    assert proof["proofScope"] == "actual_deterministic_stub_runtime_execution"
    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (
        AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS_CLEARED
    )
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_BLOCKERS
    )
    assert proof["lotusAiRuntimeExecuted"] is True
    assert proof["deterministicStubExecution"] is True
    assert proof["liveProviderExecuted"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    for forbidden in (
        "PB_SG_GLOBAL_BAL_001",
        "portfolioId",
        "candidateId",
        "requestBody",
        "responseBody",
        "runtime-proof-candidate",
    ):
        assert forbidden not in serialized


def test_executes_governed_runtime_and_maps_only_bounded_receipt() -> None:
    runtime = RecordingRuntime(lotus_ai_runtime_execution_response())

    proof = execute_ai_workflow_pack_runtime_proof(
        runtime=runtime,
        generated_at_utc=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
    )

    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is True
    request, caller_app = runtime.requests[0]
    assert caller_app == "lotus-idea"
    assert request["pack_id"] == "idea_explanation.pack"
    assert request["version"] == "v1"
    assert request["workflow_surface"] == "idea-explanation-evidence"
    receipt = cast(Mapping[str, object], proof["runtimeReceipt"])
    assert receipt["run_id"] == "wpr_runtime_proof_001"
    assert "result" not in receipt
    assert "output_preview" not in receipt


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("workflow_pack_id", "other.pack"),
        ("workflow_pack_version", "v2"),
        ("caller_app", "lotus-gateway"),
        ("runtime_state", "FAILED"),
        ("review_state", "ACCEPTED"),
        ("review_required", False),
        ("stubbed", False),
        ("human_review_required", False),
        ("client_ready_publication", "ALLOWED"),
        ("downstream_authority", "ALLOWED"),
        ("completed_at_utc", "not-a-timestamp"),
    ],
)
def test_rejects_receipt_that_does_not_prove_guarded_stub_execution(
    field_name: str,
    bad_value: object,
) -> None:
    receipt = replace(ai_runtime_execution_receipt(), **{field_name: bad_value})
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
        receipt=receipt,
    )

    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("eligibility", "allowed"), False),
        (("eligibility", "caller_app"), "other-app"),
        (("execution", "audit", "workflow_pack_run_id"), "wrong-run"),
        (("execution", "result", "structured_output", "evidence_content_hash"), "sha256:bad"),
        (("workflow_pack_run", "pack_version"), "v2"),
    ],
)
def test_rejects_tampered_runtime_response(path: tuple[str, ...], bad_value: object) -> None:
    response = lotus_ai_runtime_execution_response()
    target: dict[str, object] = response
    for key in path[:-1]:
        target = cast(dict[str, object], target[key])
    target[path[-1]] = bad_value

    with pytest.raises(InvalidAIRuntimeExecutionReceipt):
        execute_ai_workflow_pack_runtime_proof(
            runtime=RecordingRuntime(response),
            generated_at_utc=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
        )


def test_rejects_naive_generation_timestamp() -> None:
    proof = build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 7, 14, 0, 0),
        receipt=ai_runtime_execution_receipt(),
    )

    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


def test_unavailable_runtime_artifact_cannot_clear_blocker() -> None:
    proof = build_unavailable_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    )

    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert proof["aggregateBlockersCleared"] == ()
    assert proof["lotusAiRuntimeExecuted"] is False
    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


def test_rejects_receipt_digest_tamper() -> None:
    proof = _valid_proof()
    proof["runtimeReceiptSha256"] = "sha256:" + "0" * 64

    assert ai_workflow_pack_runtime_execution_proof_is_valid(proof) is False


def test_runtime_proof_contract_gate_passes_without_sibling_source_scan() -> None:
    module = _load_contract_gate_script()

    assert module.validate_ai_workflow_pack_runtime_execution_proof_contract() == []


def test_runtime_proof_contract_gate_scans_nested_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content({"receipt": {"portfolio_id": "secret"}}, errors)

    assert errors == ["$.receipt.portfolio_id: forbidden source-sensitive key is present"]


def test_runtime_proof_cli_invokes_configured_runtime_and_writes_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    runtime = RecordingRuntime(lotus_ai_runtime_execution_response())
    monkeypatch.setattr(module, "HttpLotusAIWorkflowRuntime", lambda **_: runtime)
    output_path = tmp_path / "runtime-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-07-14T00:00:00Z",
            "--lotus-ai-base-url",
            "http://lotus-ai.internal:8140",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert ai_workflow_pack_runtime_execution_proof_is_valid(
        json.loads(output_path.read_text(encoding="utf-8"))
    )
    assert len(runtime.requests) == 1


def test_runtime_proof_cli_writes_invalid_non_proof_when_runtime_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    monkeypatch.setattr(
        module,
        "execute_ai_workflow_pack_runtime_proof",
        lambda **_: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    output_path = tmp_path / "runtime-unavailable.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-07-14T00:00:00Z",
            "--lotus-ai-base-url",
            "http://lotus-ai.internal:8140",
            "--output",
            str(output_path),
            "--allow-runtime-unavailable",
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["aiWorkflowPackRuntimeExecutionProofValid"] is False
    assert proof["aggregateBlockersCleared"] == []


def _valid_proof() -> dict[str, object]:
    return build_ai_workflow_pack_runtime_execution_proof_payload(
        generated_at_utc=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
        receipt=ai_runtime_execution_receipt(),
    )


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "ai_workflow_pack_runtime_execution_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "ai_workflow_pack_runtime_execution_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_ai_workflow_pack_runtime_execution_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_ai_workflow_pack_runtime_execution_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
