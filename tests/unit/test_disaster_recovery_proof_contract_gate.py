from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def test_disaster_recovery_proof_gate_accepts_real_restore_evidence(tmp_path: Path) -> None:
    module = load_gate()
    restore_path, resume_path = write_valid_evidence(module, tmp_path)

    assert (
        module.validate_disaster_recovery_proof(
            restore_evidence_path=restore_path,
            resume_evidence_path=resume_path,
        )
        == []
    )


def test_disaster_recovery_proof_gate_rejects_false_passing_and_mutation(
    tmp_path: Path,
) -> None:
    module = load_gate()
    restore, resume = valid_evidence(module)
    restore["pitr_proof"] = False
    restore["backup_format"] = "physical-base-plus-wal"
    restore["actual_rpo_seconds"] = 3600
    restore["restored_table_row_counts"]["idea_outbox_recovery_audit"] = 0
    resume["table_content_sha256_after"]["idea_outbox_event"] = "f" * 64
    resume["candidate_replay_decision"] = "accepted"
    restore_path = tmp_path / "restore.json"
    resume_path = tmp_path / "resume.json"
    restore_path.write_text(json.dumps(restore), encoding="utf-8")
    resume_path.write_text(json.dumps(resume), encoding="utf-8")

    errors = module.validate_disaster_recovery_proof(
        restore_evidence_path=restore_path,
        resume_evidence_path=resume_path,
    )

    assert "non-PITR restore evidence must identify the logical backup format" in errors
    assert "disaster recovery restore evidence breached RPO" in errors
    assert "disaster recovery representative table is empty: idea_outbox_recovery_audit" in errors
    assert (
        "disaster recovery resume evidence candidate_replay_decision must be 'replayed'" in errors
    )
    assert "disaster recovery resume mutated restored state" in errors


def write_valid_evidence(module: ModuleType, tmp_path: Path) -> tuple[Path, Path]:
    restore, resume = valid_evidence(module)
    restore_path = tmp_path / "restore.json"
    resume_path = tmp_path / "resume.json"
    restore_path.write_text(json.dumps(restore), encoding="utf-8")
    resume_path.write_text(json.dumps(resume), encoding="utf-8")
    return restore_path, resume_path


def valid_evidence(module: ModuleType) -> tuple[dict[str, object], dict[str, object]]:
    contract = json.loads(module.CONTRACT_PATH.read_text(encoding="utf-8"))
    tables = contract["restore_verification"]["owned_tables"]
    hashes = {table: "a" * 64 for table in tables}
    restore: dict[str, object] = {
        "evidence_version": "1.0.0",
        "validation_mode": "real_restore_validation",
        "status": "passed",
        "real_restored_backup": True,
        "synthetic_smoke": False,
        "source_safe": True,
        "supported_feature_promoted": False,
        "certification_status": "not_certified",
        "failed_checks": [],
        "backup_artifact_sha256": "b" * 64,
        "database_identity_sha256": "c" * 64,
        "migration_bundle_sha256": "d" * 64,
        "pitr_proof": False,
        "backup_format": "postgres-custom-logical",
        "actual_rpo_seconds": 60,
        "actual_rto_seconds": 300,
        "backup_created_at_utc": "2026-07-11T01:00:00+00:00",
        "recovery_point_utc": "2026-07-11T01:10:00+00:00",
        "incident_cutoff_utc": "2026-07-11T01:11:00+00:00",
        "restore_started_at_utc": "2026-07-11T01:12:00+00:00",
        "restore_completed_at_utc": "2026-07-11T01:14:00+00:00",
        "service_ready_at_utc": "2026-07-11T01:17:00+00:00",
        "restored_table_row_counts": {table: 1 for table in tables},
        "restored_table_content_sha256": hashes,
    }
    resume: dict[str, object] = {
        "evidence_version": "1.0.0",
        "status": "passed",
        "candidate_replay_decision": "replayed",
        "outbox_recovery_replay_decision": "replayed",
        "stale_lease_finalize_decision": "lease_conflict",
        "no_duplicate_or_mutation": True,
        "source_safe": True,
        "supported_feature_promoted": False,
        "certification_status": "not_certified",
        "downstream_claim_decisions": {
            "conversion_intent": "reconciliation_required",
            "report_evidence_pack": "reconciliation_required",
        },
        "table_content_sha256_before": dict(hashes),
        "table_content_sha256_after": dict(hashes),
    }
    return restore, resume


def load_gate() -> ModuleType:
    path = ROOT / "scripts/disaster_recovery_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location("disaster_recovery_proof_contract_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
