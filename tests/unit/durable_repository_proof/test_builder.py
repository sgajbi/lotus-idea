from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_BLOCKERS_CLEARED,
    DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
    REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS,
    build_durable_repository_proof_payload,
    durable_repository_proof_is_valid,
)
from app.domain.proof_evidence import EvidenceClass
from tests.support.durable_repository_proof import (
    SOURCE_COMMIT_SHA,
    valid_durable_repository_ci_execution_receipt,
)


ROOT = Path(__file__).resolve().parents[3]
GENERATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_builds_source_safe_ci_execution_bound_durable_repository_proof() -> None:
    proof = _valid_durable_repository_proof()

    assert proof["schemaVersion"] == DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["sourceCommitSha"] == SOURCE_COMMIT_SHA
    assert proof["proofType"] == "postgres_repository_ci_execution"
    assert proof["proofScope"] == "mainline_ci_execution_receipt"
    assert proof["evidenceClass"] == EvidenceClass.CI_EXECUTION.value
    assert proof["durableRepositoryProofValid"] is True
    assert proof["aggregateBlockersCleared"] == DURABLE_REPOSITORY_BLOCKERS_CLEARED
    assert proof["evidenceRefs"] == REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS
    assert proof["productionStorageCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert durable_repository_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "postgresql://" not in serialized


def test_source_contract_without_ci_receipt_cannot_clear_runtime_blockers() -> None:
    proof = build_durable_repository_proof_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        source_commit_sha=SOURCE_COMMIT_SHA,
    )

    assert proof["durableRepositoryProofValid"] is False
    assert proof["aggregateBlockersCleared"] == ()
    assert tuple(proof["remainingCertificationBlockers"][:2]) == (
        DURABLE_REPOSITORY_BLOCKERS_CLEARED
    )
    assert durable_repository_proof_is_valid(proof) is False


def test_missing_source_contract_or_naive_timestamp_fails_closed(tmp_path: Path) -> None:
    missing_source = build_durable_repository_proof_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=tmp_path,
        source_commit_sha=SOURCE_COMMIT_SHA,
        ci_execution_receipt=valid_durable_repository_ci_execution_receipt(),
    )
    naive_time = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
        source_commit_sha=SOURCE_COMMIT_SHA,
        ci_execution_receipt=valid_durable_repository_ci_execution_receipt(),
    )

    assert missing_source["durableRepositoryProofValid"] is False
    assert naive_time["durableRepositoryProofValid"] is False
    assert durable_repository_proof_is_valid(missing_source) is False
    assert durable_repository_proof_is_valid(naive_time) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("sourceCommitSha", "b" * 40),
        ("proofType", "runtime"),
        ("proofScope", "production"),
        ("evidenceClass", "source_contract"),
        ("requiredEvidenceClass", "runtime_execution"),
        ("durableRepositoryProofValid", False),
        ("productionStorageCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_invalid_top_level_fields(field_name: str, bad_value: object) -> None:
    proof = _valid_durable_repository_proof()
    proof[field_name] = bad_value

    assert durable_repository_proof_is_valid(proof) is False


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
def test_rejects_invalid_contract_fields(field_name: str, bad_value: object) -> None:
    proof = _valid_durable_repository_proof()
    proof[field_name] = bad_value

    assert durable_repository_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "sourceContractEvidencePresent",
        "ciExecutionReceiptPresent",
        "ciExecutionReceiptValid",
        "evidenceClassMatchesBlockers",
    ],
)
def test_rejects_invalid_proof_checks(check_name: str) -> None:
    proof = _valid_durable_repository_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert durable_repository_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("repository", "sgajbi/lotus-core"),
        ("workflow_path", ".github/workflows/pr-merge-gate.yml"),
        ("workflow_name", "Pull Request Merge Gate"),
        ("job_name", "PR Merge Gate / PostgreSQL Runtime Proof"),
        ("source_commit_sha", "b" * 40),
        ("source_ref", "refs/pull/401/merge"),
        ("conclusion", "failure"),
        ("artifact_name", "unrelated-artifact"),
        ("artifact_sha256", "sha256:invalid"),
        ("assertions", ("schema_migration_rollback_reapply_verified",)),
        ("completed_at_utc", "2026-06-21T10:11:00+00:00"),
    ],
)
def test_wrong_stale_or_failed_ci_evidence_cannot_clear_runtime_blockers(
    field_name: str,
    bad_value: object,
) -> None:
    receipt = cast(Any, replace)(
        valid_durable_repository_ci_execution_receipt(),
        **{field_name: bad_value},
    )
    proof = build_durable_repository_proof_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        source_commit_sha=SOURCE_COMMIT_SHA,
        ci_execution_receipt=receipt,
    )

    assert proof["durableRepositoryProofValid"] is False
    assert proof["aggregateBlockersCleared"] == ()
    assert durable_repository_proof_is_valid(proof) is False


def test_serialized_receipt_tamper_invalidates_enclosing_proof() -> None:
    proof = _valid_durable_repository_proof()
    receipt = dict(cast(Mapping[str, object], proof["ciExecutionReceipt"]))
    receipt["run_id"] = 999
    proof["ciExecutionReceipt"] = receipt

    assert durable_repository_proof_is_valid(proof) is False


def test_proof_cli_writes_valid_receipt_bound_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "durable-repository-proof.json"
    receipt_path = tmp_path / "proof" / "ci-execution-receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        json.dumps(asdict(valid_durable_repository_ci_execution_receipt())),
        encoding="utf-8",
    )

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-commit-sha",
            SOURCE_COMMIT_SHA,
            "--ci-execution-receipt",
            str(receipt_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert durable_repository_proof_is_valid(json.loads(output_path.read_text(encoding="utf-8")))


def test_proof_cli_writes_blocked_artifact_without_receipt(tmp_path: Path) -> None:
    output_path = tmp_path / "blocked.json"

    result = _load_generator_script().main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-commit-sha",
            SOURCE_COMMIT_SHA,
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert (
        json.loads(output_path.read_text(encoding="utf-8"))["durableRepositoryProofValid"] is False
    )


def test_proof_cli_rejects_invalid_receipt_json(tmp_path: Path) -> None:
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("[]", encoding="utf-8")

    result = _load_generator_script().main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-commit-sha",
            SOURCE_COMMIT_SHA,
            "--ci-execution-receipt",
            str(receipt_path),
        ]
    )

    assert result == 2


def test_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_durable_repository_proof() -> dict[str, object]:
    return build_durable_repository_proof_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=ROOT,
        source_commit_sha=SOURCE_COMMIT_SHA,
        ci_execution_receipt=valid_durable_repository_ci_execution_receipt(),
    )


def _load_generator_script() -> ModuleType:
    return _load_script(
        "generate_durable_repository_proof",
        ROOT / "scripts" / "persistence" / "generate_durable_repository_proof.py",
    )


def _load_contract_gate_script() -> ModuleType:
    return _load_script(
        "durable_repository_proof_contract_gate",
        ROOT / "scripts" / "persistence" / "durable_repository_proof_contract_gate.py",
    )


def _load_script(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
