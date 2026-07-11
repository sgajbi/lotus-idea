from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from app.ports.capacity_probe import CapacityProbeRequest, CapacityProbeResult
from app.application.capacity_evidence_qualification import (
    TRUSTED_REPOSITORY,
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

    assert plan.expected_source_failure_class == "source_unavailable"
    assert len(plan.requests) == 3
    assert plan.requests[0].expected_status_codes == frozenset({200, 502})
    assert plan.recovery_probe is not None
    assert plan.recovery_probe.expected_status_codes == frozenset({200})


def test_downstream_plan_uses_preseeded_route_and_unique_idempotency_keys() -> None:
    module = _load_script()
    path = "/api/v1/conversion-intents/capacity-synthetic-001/downstream-submissions"

    plan = module.build_workload_plans(
        scenarios=("downstream_submission",),
        request_count=3,
        concurrency=1,
        environment_profile="production-like",
        allow_mutating_workflows=True,
        allow_production_mutations=False,
        downstream_submission_path=path,
    )[0]

    assert plan.scenario == "downstream_submission"
    assert {request.path for request in plan.requests} == {path}
    assert all(request.expected_status_codes == frozenset({200}) for request in plan.requests)
    assert all(
        request.headers["X-Caller-Capabilities"] == "idea.downstream-realization.submit"
        for request in plan.requests
    )
    assert len({request.headers["Idempotency-Key"] for request in plan.requests}) == 3


@pytest.mark.parametrize(
    "path",
    [
        None,
        "https://idea.example/api/v1/conversion-intents/id/downstream-submissions",
        "/api/v1/idea-candidates/id/downstream-submissions",
        "/api/v1/conversion-intents/id/outcomes",
        "/api/v1/conversion-intents/client/id/downstream-submissions",
    ],
)
def test_downstream_plan_rejects_missing_or_ungoverned_resource_path(
    path: str | None,
) -> None:
    module = _load_script()

    with pytest.raises(ValueError, match="governed pre-seeded synthetic resource path"):
        module.build_workload_plans(
            scenarios=("downstream_submission",),
            request_count=1,
            concurrency=1,
            environment_profile="test",
            allow_mutating_workflows=True,
            allow_production_mutations=False,
            downstream_submission_path=path,
        )


def test_downstream_seed_manifest_requires_exact_synthetic_provenance() -> None:
    module = _load_script()
    path = "/api/v1/conversion-intents/capacity-conversion-abc/downstream-submissions"
    seed = {
        "schemaVersion": "lotus-idea.downstream-capacity-seed.v1",
        "proofScope": "synthetic_downstream_capacity_resource_seed",
        "claimPosture": "seed_only_not_capacity_evidence",
        "syntheticResource": True,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
        "commitSha": "abc123",
        "branch": "main",
        "downstreamSubmissionPath": path,
    }

    assert (
        module._downstream_submission_path(
            seed=seed,
            commit_sha="abc123",
            branch="main",
            environment_path=None,
        )
        == path
    )
    for key, invalid in (
        ("syntheticResource", False),
        ("productionCapacityCertified", True),
        ("supportedFeaturePromoted", True),
        ("commitSha", "different"),
        ("branch", "feature/capacity"),
    ):
        with pytest.raises(ValueError, match="provenance is invalid"):
            module._downstream_submission_path(
                seed={**seed, key: invalid},
                commit_sha="abc123",
                branch="main",
                environment_path=None,
            )


def test_downstream_seed_manifest_rejects_ungoverned_path() -> None:
    module = _load_script()
    seed = {
        "schemaVersion": "lotus-idea.downstream-capacity-seed.v1",
        "proofScope": "synthetic_downstream_capacity_resource_seed",
        "claimPosture": "seed_only_not_capacity_evidence",
        "syntheticResource": True,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
        "commitSha": "abc123",
        "branch": "main",
        "downstreamSubmissionPath": "/api/v1/idea-candidates/client/downstream-submissions",
    }

    with pytest.raises(ValueError, match="seed path is invalid"):
        module._downstream_submission_path(
            seed=seed,
            commit_sha="abc123",
            branch="main",
            environment_path=None,
        )


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
    assert "load_soak_attestation_missing" in artifact["certificationBlockers"]


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
        def __init__(self, *, signer_workflow: str) -> None:
            self.signer_workflow = signer_workflow

        def verify(self, **kwargs: object) -> VerifiedArtifactAttestation:
            return VerifiedArtifactAttestation(
                subject_sha256="b" * 64,
                repository=TRUSTED_REPOSITORY,
                signer_workflow=self.signer_workflow,
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


def test_cli_requires_dedicated_attestation_to_clear_dependency_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    output = tmp_path / "capacity.json"
    proof = tmp_path / "dependency-recovery.json"
    proof.write_text(
        json.dumps(
            {
                "schemaVersion": "lotus-idea.service-capacity-baseline.v1",
                "repository": "lotus-idea",
                "proofScope": "source_safe_service_capacity_baseline",
                "claimPosture": "report_only_baseline",
                "environmentProfile": "production-like",
                "commitSha": "abc123",
                "branch": "main",
                "runId": "dependency-proof-1",
                "scenarios": [
                    {
                        "scenario": "dependency_failure",
                        "sampleCount": 2,
                        "acceptedCount": 2,
                        "errorCount": 0,
                        "conflictCount": 0,
                        "recoverySampleCount": 1,
                        "recoverySuccessRate": 1.0,
                    }
                ],
                "supportedFeaturePromoted": False,
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

    class FakeVerifier:
        def __init__(self, *, signer_workflow: str) -> None:
            self.signer_workflow = signer_workflow

        def verify(self, **kwargs: object) -> VerifiedArtifactAttestation:
            return VerifiedArtifactAttestation(
                subject_sha256="c" * 64,
                repository=TRUSTED_REPOSITORY,
                signer_workflow=self.signer_workflow,
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
            "aggregate-1",
            "--dependency-recovery-proof",
            str(proof),
            "--verify-dependency-recovery-attestation",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    resource = artifact["resourceEvidence"]
    assert resource["dependencyRecoveryAttestationVerified"] is True
    assert resource["dependencyRecoveryProofRunId"] == "dependency-proof-1"
    assert "dependency_recovery_attestation_missing" not in artifact["certificationBlockers"]


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


def test_paced_load_soak_request_accepts_only_qualifying_steady_state_proof() -> None:
    module = _load_script()

    module.validate_paced_load_soak_request(
        scenarios=(
            "api",
            "source_ingestion",
            "outbox_delivery",
            "downstream_submission",
            "postgresql",
        ),
        environment_profile="production-like",
        request_count=1_000,
        minimum_observation_seconds=3_600.0,
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"scenarios": ("api", "postgresql")}, "all five steady-state"),
        ({"environment_profile": "test"}, "production-like environment"),
        ({"request_count": 999}, "minimum sample count"),
        ({"minimum_observation_seconds": 3_599.9}, "minimum observation window"),
    ],
)
def test_paced_load_soak_request_rejects_nonqualifying_evidence_shape(
    mutation: dict[str, object], message: str
) -> None:
    module = _load_script()
    values: dict[str, object] = {
        "scenarios": (
            "api",
            "source_ingestion",
            "outbox_delivery",
            "downstream_submission",
            "postgresql",
        ),
        "environment_profile": "production-like",
        "request_count": 1_000,
        "minimum_observation_seconds": 3_600.0,
    }
    values.update(mutation)

    with pytest.raises(ValueError, match=message):
        module.validate_paced_load_soak_request(**values)


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
