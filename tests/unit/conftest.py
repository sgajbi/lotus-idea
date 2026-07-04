from __future__ import annotations

import pytest
import scripts.generate_implementation_proof_readiness as proof_report

from tests.support.proof_provenance import bind_clean_aggregate_proof_provenance


@pytest.fixture(autouse=True)
def clean_generator_proof_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        proof_report,
        "bind_aggregate_proof_provenance",
        bind_clean_aggregate_proof_provenance,
    )
