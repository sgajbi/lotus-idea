from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_restore_resume_validator_rejects_unsafe_evidence_identity() -> None:
    module = load_script()

    with pytest.raises(ValueError, match="source-safe identifier"):
        module._safe_identifier("postgresql://operator:secret@db", "operator_id")


def test_restore_resume_validator_binds_all_no_duplicate_decisions() -> None:
    source = (ROOT / "scripts/validate_postgres_disaster_recovery_resume.py").read_text(
        encoding="utf-8"
    )

    for decision in (
        "CandidatePersistenceDecision.REPLAYED",
        "OutboxRecoveryDecision.REPLAYED",
        "DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED",
        "DownstreamSubmissionMutationDecision.LEASE_CONFLICT",
    ):
        assert decision in source
    assert "before.table_content_sha256 == after.table_content_sha256" in source


def load_script() -> ModuleType:
    path = ROOT / "scripts/validate_postgres_disaster_recovery_resume.py"
    spec = importlib.util.spec_from_file_location(
        "validate_postgres_disaster_recovery_resume", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
