from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import pytest

from app.application.source_ingestion_runtime_evidence import (
    SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_blocked_source_ingestion_runtime_execution,
    build_source_ingestion_runtime_execution,
    source_ingestion_runtime_execution_is_valid,
)
from app.application.source_ingestion import HighCashSourceIngestionBatchResult
from app.domain import CandidatePersistenceDecision, EvidenceFreshness, InMemoryIdeaRepository
from tests.support.source_ingestion_runtime_evidence import (
    EVALUATED_AT,
    GENERATED_AT,
    FixedCoreHighCashSource,
    core_high_cash_evidence,
    runtime_execution,
    runtime_plan,
    runtime_result,
)


ROOT = Path(__file__).resolve().parents[3]


def valid_runtime_execution(*, work_item_count: int = 1) -> dict[str, Any]:
    return runtime_execution(work_item_count=work_item_count)


def test_runtime_execution_binds_source_and_persistence_receipts() -> None:
    payload = valid_runtime_execution(work_item_count=2)

    assert payload["schemaVersion"] == SOURCE_INGESTION_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["evidenceClass"] == "runtime_execution"
    assert payload["aggregateBlockersSatisfied"] == [
        "opportunity_archetype_live_core_source_proof_missing"
    ]
    execution = payload["execution"]
    assert isinstance(execution, dict)
    assert execution["decisionCounts"]["accepted"] == 1
    assert execution["decisionCounts"]["replayed"] == 1
    assert execution["receiptCount"] == 2
    assert source_ingestion_runtime_execution_is_valid(payload) is True

    serialized = json.dumps(payload)
    for sensitive_value in (
        "PB_SG_GLOBAL_BAL_001",
        "tenant-runtime-proof",
        "signal-ingestion:high-cash:lotus-core",
    ):
        assert sensitive_value not in serialized


def test_runtime_execution_accepts_a_repository_replay_receipt() -> None:
    plan = runtime_plan()
    repository = InMemoryIdeaRepository()
    runtime_result(plan, repository=repository)
    replay = runtime_result(plan, repository=repository)

    payload = build_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        result=replay,
        durable_storage_backed=True,
    )

    assert payload["execution"]["decisionCounts"]["replayed"] == 1
    assert source_ingestion_runtime_execution_is_valid(payload) is True


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda payload: payload.__setitem__("unexpected", True), id="top-level"),
        pytest.param(
            lambda payload: payload["execution"].__setitem__("unexpected", True),
            id="execution",
        ),
        pytest.param(
            lambda payload: payload["execution"]["receipts"][0].__setitem__("unexpected", True),
            id="receipt",
        ),
        pytest.param(
            lambda payload: payload["execution"]["receipts"][0]["sourceRefs"][0].__setitem__(
                "unexpected", True
            ),
            id="source-ref",
        ),
    ],
)
def test_runtime_execution_rejects_unknown_contract_fields(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    payload = valid_runtime_execution()
    mutate(payload)

    assert source_ingestion_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("aggregateProofProvenance",), "not-a-mapping"),
        (("schemaVersion",), "lotus-idea.source-ingestion.runtime-execution.v1"),
        (("repository",), "lotus-core"),
        (("evidenceClass",), "source_contract"),
        (("proofFamily",), "portfolio_accounting"),
        (("proofType",), "self_asserted"),
        (("sourceAuthority",), "lotus-idea"),
        (("generatedAtUtc",), "2026-06-21T10:10:00"),
        (("worker",), []),
        (("execution",), []),
        (("nonProofClaims",), []),
        (("remainingCertificationBlockers",), []),
        (("evidenceRefs",), []),
        (("worker", "schemaVersion"), "unexpected"),
        (("aggregateBlockersSatisfied",), []),
        (("execution", "status"), "blocked"),
        (("execution", "durableStorageBacked"), False),
        (("execution", "qualificationBlockers"), ["runtime_receipt_missing"]),
        (("execution", "decisionCounts"), []),
        (("execution", "decisionCounts", "accepted"), -1),
        (("execution", "totalCount"), True),
        (("execution", "decisionCounts", "accepted"), 0),
        (("execution", "decisionCounts", "blocked"), 1),
        (("execution", "receipts"), ()),
        (("execution", "blockReasonCounts"), {"source_unavailable": 1}),
        (("execution", "totalCount"), 2),
        (("execution", "receiptCount"), 0),
        (("execution", "receipts", 0, "itemIndex"), True),
        (("execution", "receipts", 0, "decision"), "blocked"),
        (("execution", "receipts", 0, "asOfDate"), "not-a-date"),
        (("execution", "receipts", 0, "scopeFingerprint"), "not-a-digest"),
        (("execution", "receipts", 0, "sourceRefs"), []),
        (("execution", "receipts", 0, "persistedAtUtc"), "2026-06-22T10:10:00Z"),
        (("execution", "receipts", 0, "sourceRefs", 0), {}),
        (("execution", "receipts", 0, "sourceRefs", 0, "asOfDate"), "2026-06-20"),
        (("execution", "receipts", 0, "sourceRefs", 0, "productId"), ""),
        (
            ("execution", "receipts", 0, "sourceRefs", 0, "generatedAtUtc"),
            "2026-06-22T10:00:00Z",
        ),
        (("execution", "receipts", 0, "sourceRefs", 0, "productId"), "unexpected"),
        (("execution", "receipts", 0, "sourceEvidenceHash"), "sha256:" + "0" * 64),
        (("execution", "receipts", 0, "scopeFingerprint"), "sha256:" + "0" * 64),
        (("execution", "receipts", 0, "sourceRefs", 0, "freshness"), "stale"),
        (("execution", "receipts", 0, "sourceRefs", 0, "sourceSystem"), "lotus-idea"),
        (("nonProofClaims", "productionCertified"), True),
    ],
)
def test_runtime_execution_rejects_forged_or_inconsistent_receipts(
    path: tuple[str | int, ...],
    value: object,
) -> None:
    payload = deepcopy(valid_runtime_execution())
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert source_ingestion_runtime_execution_is_valid(payload) is False


def test_non_current_source_result_never_qualifies() -> None:
    plan = runtime_plan()
    result = runtime_result(
        plan,
        evidence=core_high_cash_evidence(freshness=EvidenceFreshness.STALE),
    )

    payload = build_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        result=result,
        durable_storage_backed=True,
    )

    assert payload["aggregateBlockersSatisfied"] == []
    assert "non_persisted_decisions_present" in payload["execution"]["qualificationBlockers"]
    assert source_ingestion_runtime_execution_is_valid(payload) is False


def test_empty_application_result_cannot_produce_runtime_receipts() -> None:
    plan = runtime_plan()

    payload = build_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        result=HighCashSourceIngestionBatchResult(item_results=()),
        durable_storage_backed=True,
    )

    assert payload["execution"]["receiptCount"] == 0
    assert payload["execution"]["qualificationBlockers"] == ["no_ingestion_results"]
    assert source_ingestion_runtime_execution_is_valid(payload) is False


@pytest.mark.parametrize(
    "persistence_mutator",
    [
        pytest.param(lambda _: None, id="missing-persistence"),
        pytest.param(
            lambda persistence: replace(
                persistence,
                decision=CandidatePersistenceDecision.REPLAYED,
            ),
            id="decision-mismatch",
        ),
        pytest.param(
            lambda persistence: replace(
                persistence,
                record=replace(persistence.record, evidence_hash="sha256:forged"),
            ),
            id="evidence-hash-mismatch",
        ),
        pytest.param(
            lambda persistence: replace(
                persistence,
                record=replace(
                    persistence.record,
                    candidate=replace(persistence.record.candidate, access_scope=None),
                ),
            ),
            id="missing-scope",
        ),
        pytest.param(
            lambda persistence: replace(
                persistence,
                record=replace(
                    persistence.record,
                    candidate=replace(
                        persistence.record.candidate,
                        access_scope=replace(
                            persistence.record.candidate.access_scope,
                            tenant_id="another-tenant",
                        ),
                    ),
                ),
            ),
            id="scope-mismatch",
        ),
    ],
)
def test_runtime_receipts_require_matching_persistence_results(
    persistence_mutator: Callable[[Any], Any],
) -> None:
    plan = runtime_plan()
    result = runtime_result(plan)
    item_result = result.item_results[0]
    persistence = item_result.signal_result.persistence
    assert persistence is not None
    assert persistence.record is not None
    assert persistence.record.candidate.access_scope is not None
    mismatched_result = replace(
        result,
        item_results=(
            replace(
                item_result,
                signal_result=replace(
                    item_result.signal_result,
                    persistence=persistence_mutator(persistence),
                ),
            ),
        ),
    )

    payload = build_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        result=mismatched_result,
        durable_storage_backed=True,
    )

    assert payload["execution"]["receiptCount"] == 0
    assert "runtime_receipt_missing" in payload["execution"]["qualificationBlockers"]
    assert source_ingestion_runtime_execution_is_valid(payload) is False


def test_in_memory_execution_is_evidence_but_not_certification_proof() -> None:
    plan = runtime_plan()
    payload = build_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=plan,
        result=runtime_result(plan),
        durable_storage_backed=False,
    )

    assert payload["aggregateBlockersSatisfied"] == []
    assert payload["execution"]["qualificationBlockers"] == ["durable_repository_not_configured"]
    assert source_ingestion_runtime_execution_is_valid(payload) is False


def test_blocked_execution_preserves_non_proof_boundaries() -> None:
    payload = build_blocked_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=runtime_plan(),
        error_code="core_source_unavailable",
        durable_storage_backed=True,
    )

    assert payload["execution"]["status"] == "blocked"
    assert payload["aggregateBlockersSatisfied"] == []
    assert payload["nonProofClaims"] == {
        "scheduledWorkerDeployed": False,
        "dataMeshRuntimeCertified": False,
        "gatewayWorkbenchRuntimeObserved": False,
        "productionCertified": False,
        "supportedFeaturePromoted": False,
    }
    assert source_ingestion_runtime_execution_is_valid(payload) is False


def test_blocked_in_memory_execution_preserves_storage_blocker() -> None:
    payload = build_blocked_source_ingestion_runtime_execution(
        generated_at_utc=GENERATED_AT,
        plan=runtime_plan(),
        error_code="",
        durable_storage_backed=False,
    )

    assert payload["execution"]["blockReasonCounts"] == {"core_source_unavailable": 1}
    assert "durable_repository_not_configured" in payload["execution"]["qualificationBlockers"]


def test_generation_time_must_be_timezone_aware() -> None:
    plan = runtime_plan()
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_source_ingestion_runtime_execution(
            generated_at_utc=datetime(2026, 6, 21, 10, 10),
            plan=plan,
            result=runtime_result(plan),
            durable_storage_backed=True,
        )


def test_generator_executes_application_use_case_and_writes_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_generator()
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "runtime-execution.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
                "evaluatedAtUtc": EVALUATED_AT.isoformat(),
                "tenantId": "tenant-runtime-proof",
                "workItems": [
                    {
                        "portfolioId": "PB_SG_GLOBAL_BAL_001",
                        "asOfDate": "2026-06-21",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    repository = InMemoryIdeaRepository()
    monkeypatch.setattr(module, "get_idea_repository", lambda: repository)
    monkeypatch.setattr(module, "idea_repository_durable_storage_backed", lambda _: True)
    monkeypatch.setattr(
        module,
        "LotusCoreHighCashSourceAdapter",
        lambda **_: FixedCoreHighCashSource(core_high_cash_evidence()),
    )

    result = module.main(
        [
            "--manifest",
            str(manifest),
            "--core-base-url",
            "http://localhost:8100",
            "--generated-at-utc",
            GENERATED_AT.isoformat(),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert source_ingestion_runtime_execution_is_valid(payload) is True
    assert len(repository.snapshot().candidate_records) == 1


def _load_generator() -> ModuleType:
    script_path = ROOT / "scripts" / "source_ingestion" / "generate_runtime_execution.py"
    spec = importlib.util.spec_from_file_location(
        "generate_source_ingestion_runtime_execution",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
