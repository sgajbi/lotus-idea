from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.runtime_trust_telemetry.test_execution_contract import (
    REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS,
    REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS,
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION,
    build_runtime_trust_telemetry_test_execution_payload,
    runtime_trust_telemetry_test_execution_is_valid,
)
from app.domain.proof_evidence import EvidenceClass

ROOT = Path(__file__).resolve().parents[3]


def test_builds_truthful_in_memory_test_execution_contract() -> None:
    contract = _valid_contract()

    assert contract["schemaVersion"] == RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_SCHEMA_VERSION
    assert contract["repository"] == "lotus-idea"
    assert contract["proofType"] == "runtime_trust_telemetry_test_execution"
    assert contract["proofScope"] == "deterministic_in_memory_contract_exercise"
    assert contract["evidenceClass"] == EvidenceClass.TEST_EXECUTION.value
    assert contract["testExecutionValid"] is True
    assert contract["aggregateBlockersSatisfied"] == ()
    assert contract["repositoryAdapter"] == "in_memory"
    assert contract["candidateSnapshotCount"] == 1
    assert contract["currentSourceRefCount"] == 4
    assert contract["staleOrUnavailableSourceRefCount"] == 0
    assert contract["inMemoryLineageMaterialized"] is True
    assert contract["productCoverage"] == {
        "coverageStatus": "incomplete",
        "productCoverageComplete": False,
        "declaredProductCount": 9,
        "runtimeBackedProductCount": 8,
        "blockedProductCount": 9,
        "coverageBlockers": (
            "runtime_product_materialization_missing",
            "durable_repository_not_configured",
            "platform_source_manifest_inclusion_missing",
            "platform_mesh_certification_missing",
            "gateway_workbench_discovery_proof_missing",
            "supported_feature_promotion_missing",
            "runtime_product_records_missing",
        ),
    }
    assert tuple(contract["evidenceRefs"]) == (REQUIRED_RUNTIME_TRUST_TELEMETRY_TEST_EVIDENCE_REFS)
    assert tuple(contract["remainingCertificationBlockers"]) == (
        REMAINING_RUNTIME_TRUST_TELEMETRY_BLOCKERS
    )
    assert runtime_trust_telemetry_test_execution_is_valid(contract) is True


def test_test_execution_contract_never_claims_runtime_or_certification_authority() -> None:
    contract = _valid_contract()

    for field_name in (
        "durableStorageObserved",
        "serviceRuntimeObserved",
        "apiRequestObserved",
        "authorizationObserved",
        "tenantIsolationObserved",
        "deploymentObserved",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    ):
        assert contract[field_name] is False
    assert "runtime_candidate_snapshot_missing" in contract["remainingCertificationBlockers"]
    assert "durable_repository_not_configured" in contract["productCoverage"]["coverageBlockers"]


def test_test_execution_contract_is_source_safe() -> None:
    serialized = json.dumps(_valid_contract())

    for forbidden in (
        "PB_SG_GLOBAL_BAL_001",
        "portfolioId",
        "candidateId",
        "contentHash",
        "content_hash",
    ):
        assert forbidden not in serialized


def test_rejects_test_execution_when_governed_source_evidence_is_missing(
    tmp_path: Path,
) -> None:
    contract = build_runtime_trust_telemetry_test_execution_payload(
        generated_at_utc=_generated_at(),
        repository_root=tmp_path,
    )

    assert contract["testExecutionValid"] is False
    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


def test_rejects_test_execution_with_naive_timestamp() -> None:
    contract = build_runtime_trust_telemetry_test_execution_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10),
        repository_root=ROOT,
    )

    assert contract["testExecutionValid"] is False
    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-platform"),
        ("proofType", "runtime_trust_telemetry_runtime_execution"),
        ("proofScope", "production_certification"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("testExecutionValid", False),
        ("repositoryAdapter", "postgresql"),
        ("candidateSnapshotCount", 0),
        ("currentSourceRefCount", 0),
        ("staleOrUnavailableSourceRefCount", 1),
        ("inMemoryLineageMaterialized", False),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_invalid_identity_and_observation_fields(
    field_name: str,
    bad_value: object,
) -> None:
    contract = _valid_contract()
    contract[field_name] = bad_value

    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


@pytest.mark.parametrize(
    "field_name",
    [
        "durableStorageObserved",
        "serviceRuntimeObserved",
        "apiRequestObserved",
        "authorizationObserved",
        "tenantIsolationObserved",
        "deploymentObserved",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    ],
)
def test_rejects_claim_inflation(field_name: str) -> None:
    contract = _valid_contract()
    contract[field_name] = True

    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


def test_rejects_unknown_top_level_claims() -> None:
    contract = _valid_contract()
    contract["runtimeCertified"] = True

    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersSatisfied", ("runtime_candidate_snapshot_missing",)),
        ("remainingCertificationBlockers", ()),
        ("evidenceRefs", ()),
        ("productCoverage", {}),
        ("proofChecks", {}),
    ],
)
def test_rejects_contract_boundary_mutation(field_name: str, bad_value: object) -> None:
    contract = _valid_contract()
    contract[field_name] = bad_value

    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "makeTargetEvidencePresent",
        "deterministicInMemoryExerciseObserved",
        "nonDurableRepositoryPosturePreserved",
    ],
)
def test_rejects_failed_test_execution_checks(check_name: str) -> None:
    contract = _valid_contract()
    proof_checks = dict(cast(Mapping[str, object], contract["proofChecks"]))
    proof_checks[check_name] = False
    contract["proofChecks"] = proof_checks

    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


def test_rejects_unknown_test_execution_check() -> None:
    contract = _valid_contract()
    proof_checks = dict(cast(Mapping[str, object], contract["proofChecks"]))
    proof_checks["runtimeObserved"] = True
    contract["proofChecks"] = proof_checks

    assert runtime_trust_telemetry_test_execution_is_valid(contract) is False


def test_generator_writes_valid_test_execution_contract(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "test-execution" / "runtime-trust-telemetry.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    contract = json.loads(output_path.read_text(encoding="utf-8"))
    assert runtime_trust_telemetry_test_execution_is_valid(contract) is True


def test_generator_rejects_naive_timestamp() -> None:
    module = _load_generator_script()

    assert module.main(["--generated-at-utc", "2026-06-21T10:10:00"]) == 2


def test_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def _valid_contract() -> dict[str, Any]:
    return build_runtime_trust_telemetry_test_execution_payload(
        generated_at_utc=_generated_at(),
        repository_root=ROOT,
    )


def _generated_at() -> datetime:
    return datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def _load_generator_script() -> ModuleType:
    return _load_script(
        ROOT / "scripts" / "runtime_trust_telemetry" / "generate_test_execution_contract.py",
        "generate_runtime_trust_telemetry_test_execution_contract",
    )


def _load_contract_gate_script() -> ModuleType:
    return _load_script(
        ROOT / "scripts" / "runtime_trust_telemetry" / "test_execution_contract_gate.py",
        "runtime_trust_telemetry_test_execution_contract_gate",
    )


def _load_script(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
