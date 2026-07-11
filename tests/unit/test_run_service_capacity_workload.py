from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.ports.capacity_probe import CapacityProbeRequest, CapacityProbeResult
from app.application.capacity_evidence_qualification import (
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
    VerifiedArtifactAttestation,
)


ROOT = Path(__file__).resolve().parents[2]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "run_service_capacity_workload.py"
    spec = importlib.util.spec_from_file_location("run_service_capacity_workload", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builds_declared_limit_workflow_requests_without_source_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    monkeypatch.setenv("LOTUS_IDEA_CAPACITY_AUTHORIZATION", "Bearer transient")

    plans = module.build_workload_plans(
        scenarios=("api", "source_ingestion", "outbox_delivery"),
        request_count=2,
        concurrency=1,
        environment_profile="production-like",
        allow_mutating_workflows=True,
        allow_production_mutations=False,
    )

    assert [plan.scenario for plan in plans] == ["api", "source_ingestion", "outbox_delivery"]
    assert plans[0].requests[0].path == "/health/ready"
    assert plans[1].item_count_field == "totalCount"
    assert plans[2].item_count_field == "attemptedCount"
    assert "limit=100&maxRetryCount=3" in plans[2].requests[0].path
    assert plans[2].requests[0].headers["Authorization"] == "Bearer transient"
    assert len({request.headers["Idempotency-Key"] for request in plans[2].requests}) == 2


def test_dependency_plan_has_explicit_fault_and_recovery_probes() -> None:
    module = _load_script()

    plan = module.build_workload_plans(
        scenarios=("dependency_failure",),
        request_count=3,
        concurrency=1,
        environment_profile="test",
        allow_mutating_workflows=True,
        allow_production_mutations=False,
    )[0]

    assert plan.dependency_failure_expected is True
    assert len(plan.requests) == 3
    assert plan.requests[0].expected_status_codes == frozenset({200, 502, 503})
    assert plan.recovery_probe is not None
    assert plan.recovery_probe.expected_status_codes == frozenset({200})


def test_cli_writes_source_safe_report_only_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    output = tmp_path / "capacity.json"

    class FakeProbe:
        closed = False

        def __init__(self, **kwargs: object) -> None:
            pass

        def execute(self, request: CapacityProbeRequest) -> CapacityProbeResult:
            return CapacityProbeResult(0.01, 200, "accepted", {})

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "HttpCapacityProbe", FakeProbe)

    exit_code = module.main(
        [
            "--base-url",
            "https://idea.example",
            "--environment-profile",
            "test",
            "--scenario",
            "api",
            "--request-count",
            "2",
            "--commit-sha",
            "abc123",
            "--branch",
            "feature/capacity",
            "--run-id",
            "local-1",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["claimPosture"] == "report_only_baseline"
    assert artifact["scenarios"][0]["sampleCount"] == 2
    assert artifact["certificationReady"] is False
    assert "scenario_coverage_incomplete" in artifact["certificationBlockers"]


def test_cli_links_validated_threshold_proof_without_clearing_test_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    output = tmp_path / "capacity.json"
    proof = tmp_path / "threshold.json"
    proof.write_text(
        json.dumps(
            {
                "branch": "feature/capacity",
                "claimPosture": "controlled_test_evidence_only",
                "commitSha": "abc123",
                "environmentProfile": "test",
                "generatedAtUtc": "2026-07-11T06:00:00Z",
                "initial": {
                    "collectionSucceeded": True,
                    "connectionUtilizationFraction": 0.2,
                    "posture": "normal",
                },
                "productionCapacityCertified": False,
                "proofScope": "source_safe_postgres_capacity_threshold_and_recovery",
                "recovered": {
                    "collectionSucceeded": True,
                    "connectionUtilizationFraction": 0.2,
                    "posture": "normal",
                },
                "repository": "lotus-idea",
                "runId": "threshold-1",
                "schemaVersion": "lotus-idea.postgres-capacity-threshold-proof.v1",
                "supportedFeaturePromoted": False,
                "threshold": {
                    "collectionSucceeded": True,
                    "connectionUtilizationFraction": 0.9,
                    "posture": "shed",
                    "heldConnectionCount": 12,
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeProbe:
        def __init__(self, **kwargs: object) -> None:
            pass

        def execute(self, request: CapacityProbeRequest) -> CapacityProbeResult:
            return CapacityProbeResult(0.01, 200, "accepted", {})

        def close(self) -> None:
            pass

    monkeypatch.setattr(module, "HttpCapacityProbe", FakeProbe)

    exit_code = module.main(
        [
            "--base-url",
            "https://idea.example",
            "--environment-profile",
            "test",
            "--scenario",
            "api",
            "--commit-sha",
            "abc123",
            "--branch",
            "feature/capacity",
            "--run-id",
            "local-1",
            "--postgres-threshold-proof",
            str(proof),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    resource = json.loads(output.read_text(encoding="utf-8"))["resourceEvidence"]
    assert resource["postgresThresholdProofValidated"] is True
    assert resource["postgresSaturationMeasured"] is False


def test_cli_requires_verified_mainline_attestation_to_clear_saturation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    output = tmp_path / "capacity.json"
    proof = tmp_path / "threshold.json"
    payload = {
        "branch": "main",
        "claimPosture": "controlled_test_evidence_only",
        "commitSha": "abc123",
        "environmentProfile": "test",
        "generatedAtUtc": "2026-07-11T06:00:00Z",
        "initial": {
            "collectionSucceeded": True,
            "connectionUtilizationFraction": 0.2,
            "posture": "normal",
        },
        "productionCapacityCertified": False,
        "proofScope": "source_safe_postgres_capacity_threshold_and_recovery",
        "recovered": {
            "collectionSucceeded": True,
            "connectionUtilizationFraction": 0.2,
            "posture": "normal",
        },
        "repository": "lotus-idea",
        "runId": "threshold-1",
        "schemaVersion": "lotus-idea.postgres-capacity-threshold-proof.v1",
        "supportedFeaturePromoted": False,
        "threshold": {
            "collectionSucceeded": True,
            "connectionUtilizationFraction": 0.9,
            "posture": "shed",
            "heldConnectionCount": 12,
        },
    }
    proof.write_text(json.dumps(payload), encoding="utf-8")

    class FakeProbe:
        def __init__(self, **kwargs: object) -> None:
            pass

        def execute(self, request: CapacityProbeRequest) -> CapacityProbeResult:
            return CapacityProbeResult(0.01, 200, "accepted", {})

        def close(self) -> None:
            pass

    class FakeVerifier:
        def verify(self, **kwargs: object) -> VerifiedArtifactAttestation:
            return VerifiedArtifactAttestation(
                subject_sha256="b" * 64,
                repository=TRUSTED_REPOSITORY,
                signer_workflow=TRUSTED_SIGNER_WORKFLOW,
                source_ref=TRUSTED_SOURCE_REF,
                source_commit_sha="abc123",
            )

    monkeypatch.setattr(module, "HttpCapacityProbe", FakeProbe)
    monkeypatch.setattr(module, "GitHubCapacityAttestationVerifier", FakeVerifier)

    exit_code = module.main(
        [
            "--base-url",
            "https://idea.example",
            "--environment-profile",
            "production-like",
            "--scenario",
            "api",
            "--commit-sha",
            "abc123",
            "--branch",
            "main",
            "--run-id",
            "baseline-1",
            "--postgres-threshold-proof",
            str(proof),
            "--verify-postgres-threshold-attestation",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    resource = json.loads(output.read_text(encoding="utf-8"))["resourceEvidence"]
    assert resource["postgresThresholdAttestationVerified"] is True
    assert resource["postgresSaturationMeasured"] is True


def test_resource_baseline_reader_requires_json_object(tmp_path: Path) -> None:
    module = _load_script()
    valid = tmp_path / "resource.json"
    valid.write_text('{"schemaVersion":"resource-v1"}', encoding="utf-8")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")

    assert module._read_optional_resource_baseline(valid) == {"schemaVersion": "resource-v1"}
    assert module._read_optional_resource_baseline(None) is None
    with pytest.raises(ValueError, match="resource baseline must be a JSON object"):
        module._read_optional_resource_baseline(invalid)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"scenarios": ()}, "at least one scenario"),
        ({"scenarios": ("api", "api")}, "must not contain duplicates"),
        ({"request_count": 0}, "request_count must be between"),
        ({"request_count": 10_001}, "request_count must be between"),
        ({"concurrency": 0}, "concurrency must be between"),
        ({"concurrency": 101, "request_count": 101}, "concurrency must be between"),
        (
            {"scenarios": ("source_ingestion",), "allow_mutating_workflows": False},
            "require --allow-mutating-workflows",
        ),
        (
            {
                "scenarios": ("outbox_delivery",),
                "environment_profile": "production",
                "allow_production_mutations": False,
            },
            "production mutations require",
        ),
    ],
)
def test_workload_plan_fails_closed(kwargs: dict[str, object], message: str) -> None:
    module = _load_script()
    values: dict[str, object] = {
        "scenarios": ("api",),
        "request_count": 10,
        "concurrency": 1,
        "environment_profile": "test",
        "allow_mutating_workflows": True,
        "allow_production_mutations": False,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        module.build_workload_plans(**values)
