from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest

from app.application.drawdown_review_signal import (
    evaluate_and_persist_drawdown_review_signal_from_risk,
)
from app.application.high_volatility_runtime_evidence import (
    build_high_volatility_runtime_execution,
    high_volatility_runtime_execution_is_valid,
)
from app.application.high_volatility_signal import (
    evaluate_and_persist_high_volatility_signal_from_risk,
)
from app.application.risk_drawdown_runtime_evidence import (
    build_risk_drawdown_runtime_execution,
    risk_drawdown_runtime_execution_is_valid,
)
from app.ports.idea_repository import CandidatePersistenceRepository
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
    reset_idea_repository_for_tests,
)
from tests.integration.postgres_runtime_support import table_count
from tests.support.high_volatility_runtime_evidence import (
    GENERATED_AT as HIGH_VOLATILITY_GENERATED_AT,
    FixedRiskVolatilitySource,
    risk_evidence as high_volatility_risk_evidence,
    runtime_command as high_volatility_runtime_command,
)
from tests.support.risk_drawdown_runtime_evidence import (
    GENERATED_AT as RISK_DRAWDOWN_GENERATED_AT,
    FixedRiskDrawdownSource,
    risk_evidence as risk_drawdown_evidence,
    runtime_command as risk_drawdown_runtime_command,
)

_RUNTIME_TABLES = frozenset({"idea_candidate_record", "idea_idempotency_record"})


@pytest.mark.parametrize(
    "execute",
    (
        pytest.param(
            lambda repository: _high_volatility_execution(repository),
            id="high-volatility",
        ),
        pytest.param(
            lambda repository: _drawdown_execution(repository),
            id="risk-drawdown",
        ),
    ),
)
def test_risk_runtime_evidence_replays_after_postgres_repository_reload(
    postgres_database_url: str,
    execute: Callable[[CandidatePersistenceRepository], tuple[Mapping[str, Any], bool]],
) -> None:
    accepted_payload, accepted_valid = execute(get_idea_repository())

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_payload, replayed_valid = execute(get_idea_repository())

    assert accepted_payload["execution"]["persistenceReceipt"]["decision"] == "accepted"
    assert replayed_payload["execution"]["persistenceReceipt"]["decision"] == "replayed"
    assert accepted_valid is True
    assert replayed_valid is True
    assert (
        table_count(
            postgres_database_url,
            "idea_candidate_record",
            allowed_tables=_RUNTIME_TABLES,
        )
        == 1
    )
    assert (
        table_count(
            postgres_database_url,
            "idea_idempotency_record",
            allowed_tables=_RUNTIME_TABLES,
        )
        == 1
    )


def _high_volatility_execution(
    repository: CandidatePersistenceRepository,
) -> tuple[Mapping[str, Any], bool]:
    command = high_volatility_runtime_command()
    result = evaluate_and_persist_high_volatility_signal_from_risk(
        command,
        risk_source=FixedRiskVolatilitySource(high_volatility_risk_evidence()),
        repository=repository,
    )
    payload = build_high_volatility_runtime_execution(
        generated_at_utc=HIGH_VOLATILITY_GENERATED_AT,
        command=command,
        result=result,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )
    return payload, high_volatility_runtime_execution_is_valid(payload)


def _drawdown_execution(
    repository: CandidatePersistenceRepository,
) -> tuple[Mapping[str, Any], bool]:
    command = risk_drawdown_runtime_command()
    result = evaluate_and_persist_drawdown_review_signal_from_risk(
        command,
        risk_source=FixedRiskDrawdownSource(risk_drawdown_evidence()),
        repository=repository,
    )
    payload = build_risk_drawdown_runtime_execution(
        generated_at_utc=RISK_DRAWDOWN_GENERATED_AT,
        command=command,
        result=result,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )
    return payload, risk_drawdown_runtime_execution_is_valid(payload)
