from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_closure_matrix_gate.py"
    spec = importlib.util.spec_from_file_location("github_issue_closure_matrix_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_github_issue_closure_matrix_gate_passes_current_matrix() -> None:
    module = _load_gate()

    assert module.validate_issue_closure_matrix() == []


def test_github_issue_closure_matrix_gate_blocks_missing_issue(tmp_path: Path) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    matrix.write_text(
        "# Matrix\n\n"
        "| Issue | Status | Implementation Evidence | Test And Gate Evidence | Same-Pattern Scan | Docs/Wiki/Context | PR Close Intent |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| #301 | `locally_fixed` | `src/app/api/signal_api_support.py` | `tests/unit/test_signal_api_support.py` | same-pattern scan done | `REPOSITORY-ENGINEERING-CONTEXT.md` | Closes #301 |\n",
        encoding="utf-8",
    )

    errors = module.validate_issue_closure_matrix(matrix)

    assert any("Missing actionable issue rows: #302" in error for error in errors)


def test_github_issue_closure_matrix_gate_blocks_weak_evidence(tmp_path: Path) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    rows = []
    for issue in sorted(module.ACTIONABLE_ISSUES):
        implementation = "`src/app/api/example.py`"
        tests = "`tests/unit/test_example.py`"
        scan = "same-pattern scan done"
        docs = "`REPOSITORY-ENGINEERING-CONTEXT.md`"
        close = f"Closes #{issue}"
        if issue == 302:
            implementation = "not recorded"
            tests = "not recorded"
            scan = "not recorded"
            docs = "not recorded"
            close = "close later"
        rows.append(
            f"| #{issue} | `locally_fixed` | {implementation} | {tests} | {scan} | {docs} | {close} |"
        )
    matrix.write_text(
        "# Matrix\n\n"
        "| Issue | Status | Implementation Evidence | Test And Gate Evidence | Same-Pattern Scan | Docs/Wiki/Context | PR Close Intent |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#302: implementation evidence must cite code or contract paths" in errors
    assert (
        "#302: test and gate evidence must cite tests, make targets, or an executed workflow "
        "dispatch" in errors
    )
    assert "#302: same-pattern scan evidence is required" in errors
    assert "#302: docs/wiki/context evidence or decision is required" in errors
    assert "#302: locally fixed intent must contain `Closes #302`" in errors


def test_github_issue_closure_matrix_gate_rejects_partial_status_with_close_intent(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace("Keep #343 open", "Closes #343")
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert (
        "#343: partially fixed intent must contain `Keep #343 open` or `Keeps #343 open`" in errors
    )


def test_github_issue_closure_matrix_gate_rejects_unproven_merged_main_status(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = (
        content.replace(
            "PR `#362` merged by rebase and Main Releasability `29235051710` plus CodeQL `29235047521` passed on `eba19925`.",
            "PR merged and checks passed.",
        )
        .replace(
            "Wiki publication commit `5534db5` has zero source drift.",
            "Wiki checked.",
        )
        .replace(
            "Closed on merged `main`; local and remote feature branches were deleted.",
            "Implementation complete.",
        )
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#357: merged main evidence must cite Main Releasability and CodeQL" in errors
    assert "#357: merged main evidence must cite wiki publication" in errors
    assert "#357: merged main intent must record closed issue and branch cleanup" in errors


def test_github_issue_closure_matrix_gate_rejects_merged_main_status_regression(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "| [#357](https://github.com/sgajbi/lotus-idea/issues/357) "
        "Introduce governed feature-bounded packages within Idea runtime layers | `merged_main` |",
        "| [#357](https://github.com/sgajbi/lotus-idea/issues/357) "
        "Introduce governed feature-bounded packages within Idea runtime layers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#357: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_lifecycle_serialization_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Serialize lifecycle erasure against concurrent downstream claims | `merged_main` |",
        "Serialize lifecycle erasure against concurrent downstream claims | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#414: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_platform_mesh_proof_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop static mesh declarations from clearing event publication proof | `merged_main` |",
        "Stop static mesh declarations from clearing event publication proof | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#422: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_outbox_broker_proof_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop fake publisher source scans from clearing broker runtime proof | `merged_main` |",
        "Stop fake publisher source scans from clearing broker runtime proof | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#419: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_closure_guard_fix(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Freeze merged-main closure status for issue #419 in the matrix gate | `merged_main` |",
        "Freeze merged-main closure status for issue #419 in the matrix gate | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#424: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_ai_registration_proof_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Classify AI workflow-pack registration as source-contract evidence | `merged_main` |",
        "Classify AI workflow-pack registration as source-contract evidence | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#428: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_evidence_inventory_guard_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Keep evidence-classification inventory synchronized with closed occurrences | `merged_main` |",
        "Keep evidence-classification inventory synchronized with closed occurrences | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#431: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_workbench_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop static Workbench read-path declarations from clearing runtime consumption proof | `merged_main` |",
        "Stop static Workbench read-path declarations from clearing runtime consumption proof | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#434: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_report_intake_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop static Report route declarations from clearing live intake proof | `merged_main` |",
        "Stop static Report route declarations from clearing live intake proof | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#437: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_report_materialization_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop static Report contracts from claiming rendered and archived outputs | `merged_main` |",
        "Stop static Report contracts from claiming rendered and archived outputs | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#438: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_platform_catalog_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Classify platform catalog inclusion as digest-bound source-contract evidence | `merged_main` |",
        "Classify platform catalog inclusion as digest-bound source-contract evidence | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#443: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_mesh_policy_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop static mesh policies from clearing certification blockers | `merged_main` |",
        "Stop static mesh policies from clearing certification blockers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#444: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_downstream_route_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop static Advise and Manage route declarations from clearing live-contract blockers | `merged_main` |",
        "Stop static Advise and Manage route declarations from clearing live-contract blockers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#449: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_runtime_telemetry_test_evidence_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Stop in-memory trust telemetry tests from clearing runtime snapshot proof | `merged_main` |",
        "Stop in-memory trust telemetry tests from clearing runtime snapshot proof | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#452: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_source_ingestion_runtime_evidence_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Bind source-ingestion live proof to runtime and persistence receipts | `merged_main` |",
        "Bind source-ingestion live proof to runtime and persistence receipts | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#456: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_ai_attestation_source_contract_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Classify signed AI attestation declarations as closed source-contract evidence | `merged_main` |",
        "Classify signed AI attestation declarations as closed source-contract evidence | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#459: merged-main issue cannot regress to `locally_fixed`" in errors
