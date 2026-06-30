from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from app.api.signal_api_support import (
    operation_outcome_from_signal_evaluation,
    source_authority_from_refs,
)
from app.observability import OperationOutcome


def test_source_authority_falls_back_for_mixed_source_refs() -> None:
    source_refs = (
        SimpleNamespace(source_system=SimpleNamespace(value="lotus-core")),
        SimpleNamespace(source_system=SimpleNamespace(value="lotus-risk")),
    )

    assert source_authority_from_refs(source_refs) == "source-owned"


def test_signal_outcome_maps_suppressed_to_operation_outcome() -> None:
    result = cast(Any, SimpleNamespace(outcome=SimpleNamespace(value="suppressed")))

    assert operation_outcome_from_signal_evaluation(result) == OperationOutcome.SUPPRESSED
