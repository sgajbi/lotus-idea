from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

import scripts.generate_implementation_proof_readiness as proof_report
from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.proof_provenance import aggregate_proof_artifact_is_current
from app.application.proof_provenance import current_source_revision
from app.application.proof_provenance import SOURCE_REVISION_ENV
from app.application.proof_provenance import SOURCE_REVISION_UNAVAILABLE
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[2]


def test_implementation_proof_readiness_preserves_blocker_without_aggregate_provenance() -> None:
    raw_proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        durable_repository_proof=raw_proof,
        durable_repository_proof_ref="durable repository proof artifact",
    )

    assert "durable_repository_not_configured" in snapshot.overall_blockers


def test_implementation_proof_readiness_preserves_blocker_for_stale_proof(
    tmp_path: Path,
) -> None:
    stale_proof = tmp_path / "durable-repository-proof.json"
    stale_proof.write_text(
        json.dumps(
            build_durable_repository_proof_payload(
                generated_at_utc=datetime(2026, 6, 20, 9, 0, tzinfo=UTC),
                repository_root=ROOT,
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--durable-repository-proof",
            str(stale_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "durable_repository_not_configured" in payload["overallBlockers"]


def test_implementation_proof_readiness_preserves_blocker_for_source_revision_mismatch(
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "durable-repository-proof.json"
    raw_proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof_path.write_text(json.dumps(raw_proof), encoding="utf-8")
    bound_proof = bind_aggregate_proof_provenance(
        raw_proof,
        artifact_path=proof_path,
        proof_ref="durable repository proof artifact",
        repository_root=ROOT,
    )
    bound_proof["aggregateProofProvenance"]["sourceRevision"] = "different-source-revision"

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        durable_repository_proof=bound_proof,
        durable_repository_proof_ref="durable repository proof artifact",
    )

    assert "durable_repository_not_configured" in snapshot.overall_blockers


def test_current_source_revision_prefers_configured_ci_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SOURCE_REVISION_ENV, "ci-validated-revision")

    assert current_source_revision(ROOT) == "ci-validated-revision"


def _valid_provenance(
    *,
    repository: str = "lotus-idea",
    proof_ref: str = "durable repository proof artifact",
    proof_generated_at_utc: str = "2026-06-21T10:00:00Z",
    artifact_sha256: str = "a" * 64,
    source_revision: str = "expected-source-revision",
) -> dict[str, object]:
    return {
        "repository": repository,
        "proofRef": proof_ref,
        "proofGeneratedAtUtc": proof_generated_at_utc,
        "artifactSha256": artifact_sha256,
        "sourceRevision": source_revision,
        "sourceTreeDirty": False,
    }


@pytest.mark.parametrize(
    ("payload", "proof_ref", "evaluated_at_utc"),
    [
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0),
            id="naive-evaluation-time",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(),
            },
            None,
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="missing-proof-ref",
        ),
        pytest.param(
            {
                "generatedAtUtc": "not-a-timestamp",
                "aggregateProofProvenance": _valid_provenance(),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="malformed-generated-at",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00",
                "aggregateProofProvenance": _valid_provenance(),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="timezone-missing-generated-at",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T11:00:00Z",
                "aggregateProofProvenance": _valid_provenance(
                    proof_generated_at_utc="2026-06-21T11:00:00Z"
                ),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="future-generated-at",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-20T09:00:00Z",
                "aggregateProofProvenance": _valid_provenance(
                    proof_generated_at_utc="2026-06-20T09:00:00Z"
                ),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="stale-generated-at",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(repository="lotus-report"),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="wrong-repository",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(proof_ref="different proof"),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="proof-ref-mismatch",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(
                    proof_generated_at_utc="2026-06-21T10:01:00Z"
                ),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="generated-at-provenance-mismatch",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(artifact_sha256="not-sha256"),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="invalid-artifact-hash",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(source_revision=" "),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="blank-source-revision",
        ),
        pytest.param(
            {
                "generatedAtUtc": "2026-06-21T10:00:00Z",
                "aggregateProofProvenance": _valid_provenance(
                    source_revision=SOURCE_REVISION_UNAVAILABLE
                ),
            },
            "durable repository proof artifact",
            datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            id="unavailable-source-revision",
        ),
    ],
)
def test_aggregate_proof_artifact_rejects_untrusted_or_stale_provenance(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    proof_ref: str | None,
    evaluated_at_utc: datetime,
) -> None:
    monkeypatch.setenv(SOURCE_REVISION_ENV, "expected-source-revision")

    assert (
        aggregate_proof_artifact_is_current(
            payload,
            evaluated_at_utc=evaluated_at_utc,
            proof_ref=proof_ref,
            repository_root=ROOT,
        )
        is False
    )
