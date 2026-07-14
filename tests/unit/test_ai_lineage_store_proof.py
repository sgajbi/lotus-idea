from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Mapping, cast

import pytest

from app.application.ai_lineage_store_proof import (
    AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION,
    REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS,
    ai_lineage_store_proof_is_valid,
    build_ai_lineage_store_proof_payload,
)
from app.domain.proof_evidence import EvidenceClass
from tests.support.ai_lineage_store_proof import valid_ai_lineage_ci_execution_receipt


ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_ai_lineage_store_proof() -> None:
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
    )

    assert proof["schemaVersion"] == AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "postgres_ai_lineage_ci_execution"
    assert proof["proofScope"] == "mainline_ci_execution_receipt"
    assert proof["evidenceClass"] == EvidenceClass.CI_EXECUTION.value
    assert proof["aiLineageStoreProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == ("certified_ai_lineage_store_missing",)
    assert tuple(proof["evidenceRefs"]) == REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS
    assert proof["durableAiLineageStoreBacked"] is True
    assert proof["lotusAiRuntimeExecuted"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert ai_lineage_store_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "candidateId" not in serialized
    assert "postgresql://" not in serialized


def test_rejects_ai_lineage_store_proof_when_evidence_is_missing(tmp_path: Path) -> None:
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=tmp_path,
        ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
    )

    assert proof["aiLineageStoreProofValid"] is False
    assert ai_lineage_store_proof_is_valid(proof) is False


def test_rejects_ai_lineage_store_proof_with_naive_timestamp() -> None:
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
        ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
    )

    assert proof["aiLineageStoreProofValid"] is False
    assert ai_lineage_store_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("evidenceClass", "source_contract"),
        ("requiredEvidenceClass", "runtime_execution"),
        ("aiLineageStoreProofValid", False),
        ("durableAiLineageStoreBacked", False),
        ("lotusAiRuntimeExecuted", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_ai_lineage_store_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_ai_lineage_store_proof()
    proof[field_name] = bad_value

    assert ai_lineage_store_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
        ("ciExecutionReceipt", []),
        ("ciExecutionReceiptSha256", "sha256:invalid"),
    ],
)
def test_rejects_ai_lineage_store_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_ai_lineage_store_proof()
    proof[field_name] = bad_value

    assert ai_lineage_store_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "sourceContractEvidencePresent",
        "ciExecutionReceiptPresent",
        "ciExecutionReceiptValid",
        "evidenceClassMatchesBlocker",
    ],
)
def test_rejects_ai_lineage_store_proof_with_invalid_proof_checks(check_name: str) -> None:
    proof = _valid_ai_lineage_store_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert ai_lineage_store_proof_is_valid(proof) is False


def test_ai_lineage_store_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "ai-lineage-store-proof.json"
    receipt_path = tmp_path / "proof" / "ci-execution-receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        json.dumps(asdict(valid_ai_lineage_ci_execution_receipt())),
        encoding="utf-8",
    )

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--ci-execution-receipt",
            str(receipt_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert ai_lineage_store_proof_is_valid(proof) is True


def test_source_contract_without_ci_receipt_cannot_clear_certification_blocker() -> None:
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    assert proof["aiLineageStoreProofValid"] is False
    assert proof["aggregateBlockersCleared"] == ()
    assert "certified_ai_lineage_store_missing" in proof["remainingCertificationBlockers"]
    assert proof["durableAiLineageStoreBacked"] is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("repository", "sgajbi/lotus-core"),
        ("workflow_path", ".github/workflows/pr-merge-gate.yml"),
        ("workflow_name", "PR Merge Gate"),
        ("job_name", "PR Merge Gate / PostgreSQL Runtime Proof"),
        ("source_ref", "refs/pull/396/merge"),
        ("conclusion", "failure"),
        ("artifact_name", "unrelated-artifact"),
        ("artifact_sha256", "sha256:invalid"),
        ("assertions", ("ai_lineage_schema_applied",)),
    ],
)
def test_wrong_or_failed_ci_evidence_cannot_clear_lineage_certification(
    field_name: str,
    bad_value: object,
) -> None:
    receipt = replace(valid_ai_lineage_ci_execution_receipt(), **{field_name: bad_value})
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        ci_execution_receipt=receipt,
    )

    assert proof["aiLineageStoreProofValid"] is False
    assert proof["aggregateBlockersCleared"] == ()
    assert ai_lineage_store_proof_is_valid(proof) is False


def test_serialized_receipt_tamper_invalidates_enclosing_proof() -> None:
    proof = _valid_ai_lineage_store_proof()
    receipt = dict(cast(Mapping[str, object], proof["ciExecutionReceipt"]))
    receipt["run_id"] = 999
    proof["ciExecutionReceipt"] = receipt

    assert ai_lineage_store_proof_is_valid(proof) is False


def test_ai_lineage_store_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_ai_lineage_store_proof() -> dict[str, object]:
    return build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
    )


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_ai_lineage_store_proof.py"
    spec = importlib.util.spec_from_file_location("generate_ai_lineage_store_proof", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "ai_lineage_store_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "ai_lineage_store_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
