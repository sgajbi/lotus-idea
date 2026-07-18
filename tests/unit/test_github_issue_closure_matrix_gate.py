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


def test_github_issue_closure_matrix_gate_requires_current_scheduler_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if not line.startswith("| [#508]"))
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #508" in errors


def test_github_issue_closure_matrix_gate_requires_current_volatility_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#465]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #465" in errors


def test_github_issue_closure_matrix_gate_requires_current_drawdown_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#466]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #466" in errors


def test_github_issue_closure_matrix_gate_requires_current_underperformance_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#469]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #469" in errors


def test_github_issue_closure_matrix_gate_requires_postgres_fake_dispatcher_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#618]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #618" in errors


def test_github_issue_closure_matrix_gate_requires_postgres_row_builder_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#620]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #620" in errors


def test_github_issue_closure_matrix_gate_requires_ai_workflow_pack_fixture_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#623]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #623" in errors


def test_github_issue_closure_matrix_gate_requires_concentration_risk_domain_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#625]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #625" in errors


def test_github_issue_closure_matrix_gate_requires_high_cash_persist_api_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#630]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #630" in errors


def test_github_issue_closure_matrix_gate_requires_bond_maturity_core_adapter_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#633]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #633" in errors


def test_github_issue_closure_matrix_gate_requires_core_portfolio_state_validator_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#636]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #636" in errors


def test_github_issue_closure_matrix_gate_requires_ai_explanation_route_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#638]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #638" in errors


def test_github_issue_closure_matrix_gate_requires_bond_maturity_runtime_validator_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#640]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #640" in errors


def test_github_issue_closure_matrix_gate_requires_runtime_trust_telemetry_loader_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#642]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #642" in errors


def test_github_issue_closure_matrix_gate_requires_postgres_workflow_test_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#645]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #645" in errors


def test_github_issue_closure_matrix_gate_requires_postgres_runtime_workflow_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#648]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #648" in errors


def test_github_issue_closure_matrix_gate_requires_postgres_snapshot_writes_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#612]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #612" in errors


def test_github_issue_closure_matrix_gate_requires_quality_baseline_stub_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#614]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #614" in errors


def test_github_issue_closure_matrix_gate_requires_inventory_closure_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = "\n".join(line for line in content.splitlines() if "[#473]" not in line)
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "Missing actionable issue rows: #473" in errors


def test_github_issue_closure_matrix_gate_freezes_underperformance_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/469) Bind underperformance proof to authoritative Performance runtime and "
        "durable persistence | `merged_main` |",
        "issues/469) Bind underperformance proof to authoritative Performance runtime and "
        "durable persistence | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#469: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_core_benchmark_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/476) Bind Core benchmark-assignment proof to authoritative runtime evidence "
        "| `merged_main` |",
        "issues/476) Bind Core benchmark-assignment proof to authoritative runtime evidence "
        "| `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#476: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_bond_maturity_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/482) Bind bond-maturity proof to authoritative Core runtime evidence "
        "| `merged_main` |",
        "issues/482) Bind bond-maturity proof to authoritative Core runtime evidence "
        "| `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#482: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_low_income_cashflow_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/485) Bind low-income cashflow proof to authoritative Core runtime evidence "
        "| `merged_main` |",
        "issues/485) Bind low-income cashflow proof to authoritative Core runtime evidence "
        "| `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#485: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_scheduler_evidence_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/508) Stop static scheduled-worker declarations from clearing deployment proof "
        "| `merged_main` |",
        "issues/508) Stop static scheduled-worker declarations from clearing deployment proof "
        "| `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#508: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_postgres_fake_dispatcher_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/618) Refactor PostgreSQL fake SQL dispatcher into capability-owned "
        "handlers | `merged_main` |",
        "issues/618) Refactor PostgreSQL fake SQL dispatcher into capability-owned "
        "handlers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#618: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_postgres_row_builder_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/620) Refactor PostgreSQL fake row construction into table-owned "
        "builders | `merged_main` |",
        "issues/620) Refactor PostgreSQL fake row construction into table-owned "
        "builders | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#620: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_ai_workflow_pack_fixture_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/623) Refactor AI workflow-pack fixture writers into capability-owned "
        "helpers | `merged_main` |",
        "issues/623) Refactor AI workflow-pack fixture writers into capability-owned "
        "helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#623: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_concentration_risk_domain_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/625) Refactor concentration-risk signal evaluator into "
        "domain-owned helpers | `merged_main` |",
        "issues/625) Refactor concentration-risk signal evaluator into "
        "domain-owned helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#625: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_high_cash_persistence_api_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/630) Refactor high-cash persist API handler into "
        "API-boundary helpers | `merged_main` |",
        "issues/630) Refactor high-cash persist API handler into "
        "API-boundary helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#630: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_bond_maturity_core_adapter_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/633) Refactor bond-maturity Core adapter into source-owned "
        "helpers | `merged_main` |",
        "issues/633) Refactor bond-maturity Core adapter into source-owned "
        "helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#633: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_core_portfolio_state_validator_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/636) Refactor Core portfolio-state runtime validator into "
        "proof-owned helpers | `merged_main` |",
        "issues/636) Refactor Core portfolio-state runtime validator into "
        "proof-owned helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#636: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_ai_explanation_route_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/638) Refactor AI explanation evaluation route into "
        "API-boundary helpers | `merged_main` |",
        "issues/638) Refactor AI explanation evaluation route into "
        "API-boundary helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#638: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_bond_maturity_runtime_validator_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/640) Refactor bond-maturity runtime proof validator into "
        "contract helpers | `merged_main` |",
        "issues/640) Refactor bond-maturity runtime proof validator into "
        "contract helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#640: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_runtime_trust_telemetry_loader_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/642) Refactor PostgreSQL runtime trust telemetry summary loader | `merged_main` |",
        "issues/642) Refactor PostgreSQL runtime trust telemetry summary loader | "
        "`locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#642: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_postgres_workflow_test_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/645) Refactor PostgreSQL mutating workflow round-trip test into "
        "focused helpers | `merged_main` |",
        "issues/645) Refactor PostgreSQL mutating workflow round-trip test into "
        "focused helpers | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#645: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_postgres_snapshot_writes_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/612) Extract PostgreSQL snapshot detail write helpers from main "
        "repository | `merged_main` |",
        "issues/612) Extract PostgreSQL snapshot detail write helpers from main "
        "repository | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#612: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_quality_baseline_stub_main_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8").replace(
        "issues/614) Exclude non-implementation stubs from quality baseline "
        "generation | `merged_main` |",
        "issues/614) Exclude non-implementation stubs from quality baseline "
        "generation | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#614: merged-main issue cannot regress to `locally_fixed`" in errors


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


def test_github_issue_closure_matrix_gate_freezes_volatility_runtime_evidence_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Bind high-volatility proof to authoritative Risk runtime and durable persistence | `merged_main` |",
        "Bind high-volatility proof to authoritative Risk runtime and durable persistence | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#465: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_drawdown_runtime_evidence_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Bind drawdown-review proof to authoritative Risk runtime and durable persistence | `merged_main` |",
        "Bind drawdown-review proof to authoritative Risk runtime and durable persistence | `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#466: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_service_capacity_builder_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Refactor service capacity baseline builder below Slice 19 maintainability threshold |"
        " `merged_main` |",
        "Refactor service capacity baseline builder below Slice 19 maintainability threshold |"
        " `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#601: merged-main issue cannot regress to `locally_fixed`" in errors


def test_github_issue_closure_matrix_gate_freezes_outbox_delivery_run_closure(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    matrix = tmp_path / "matrix.md"
    content = module.MATRIX_PATH.read_text(encoding="utf-8")
    content = content.replace(
        "Refactor outbox delivery run-once API handler below Slice 19 maintainability threshold |"
        " `merged_main` |",
        "Refactor outbox delivery run-once API handler below Slice 19 maintainability threshold |"
        " `locally_fixed` |",
    )
    matrix.write_text(content, encoding="utf-8")

    errors = module.validate_issue_closure_matrix(matrix)

    assert "#603: merged-main issue cannot regress to `locally_fixed`" in errors
