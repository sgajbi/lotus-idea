from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_CLASSIFICATION_INVENTORY_PATH = Path(
    "docs/architecture/implementation-proof-evidence-classification.md"
)
ISSUE_CLOSURE_MATRIX_PATH = Path("docs/architecture/GITHUB-ISSUE-CLOSURE-MATRIX.md")


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "documentation_contract_gate.py"
    spec = importlib.util.spec_from_file_location("documentation_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_documentation_contract_gate_passes_current_repository_truth() -> None:
    module = _load_gate()

    assert module.validate_documentation_contract() == []


def test_documentation_contract_gate_blocks_missing_campaign_inventory_occurrence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    architecture = tmp_path / "docs" / "architecture"
    architecture.mkdir(parents=True)
    inventory_source = ROOT / EVIDENCE_CLASSIFICATION_INVENTORY_PATH
    matrix_source = ROOT / ISSUE_CLOSURE_MATRIX_PATH
    inventory = inventory_source.read_text(encoding="utf-8").replace("#428", "issue 428")
    (tmp_path / EVIDENCE_CLASSIFICATION_INVENTORY_PATH).write_text(
        inventory,
        encoding="utf-8",
    )
    (tmp_path / ISSUE_CLOSURE_MATRIX_PATH).write_text(
        matrix_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    errors = module.evidence_inventory.evidence_classification_inventory_errors(root=tmp_path)

    assert errors == [
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "missing completed campaign occurrences: #428"
    ]


def test_documentation_contract_gate_requires_explicit_governance_exclusion(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    architecture = tmp_path / "docs" / "architecture"
    architecture.mkdir(parents=True)
    inventory_source = ROOT / EVIDENCE_CLASSIFICATION_INVENTORY_PATH
    matrix_source = ROOT / ISSUE_CLOSURE_MATRIX_PATH
    (tmp_path / EVIDENCE_CLASSIFICATION_INVENTORY_PATH).write_text(
        inventory_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    matrix = matrix_source.read_text(encoding="utf-8").replace(
        "Campaign occurrence: no;",
        "Campaign relation: governance;",
    )
    (tmp_path / ISSUE_CLOSURE_MATRIX_PATH).write_text(matrix, encoding="utf-8")

    errors = module.evidence_inventory.evidence_classification_inventory_errors(root=tmp_path)

    assert errors == [
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "missing completed campaign occurrences: #431, #473, #489"
    ]


def test_documentation_contract_gate_blocks_stale_completed_occurrence_posture(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    architecture = tmp_path / "docs" / "architecture"
    architecture.mkdir(parents=True)
    inventory_source = ROOT / EVIDENCE_CLASSIFICATION_INVENTORY_PATH
    matrix_source = ROOT / ISSUE_CLOSURE_MATRIX_PATH
    inventory = inventory_source.read_text(encoding="utf-8").replace(
        "#469 hardened on exact main by PR #472",
        "#469, next separately bounded occurrence",
    )
    (tmp_path / EVIDENCE_CLASSIFICATION_INVENTORY_PATH).write_text(
        inventory,
        encoding="utf-8",
    )
    (tmp_path / ISSUE_CLOSURE_MATRIX_PATH).write_text(
        matrix_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    errors = module.evidence_inventory.evidence_classification_inventory_errors(root=tmp_path)

    assert errors == [
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "completed campaign occurrences retain pending posture: #469"
    ]


def test_documentation_contract_gate_blocks_unregistered_completed_occurrence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    architecture = tmp_path / "docs" / "architecture"
    architecture.mkdir(parents=True)
    inventory_source = ROOT / EVIDENCE_CLASSIFICATION_INVENTORY_PATH
    matrix_source = ROOT / ISSUE_CLOSURE_MATRIX_PATH
    (tmp_path / EVIDENCE_CLASSIFICATION_INVENTORY_PATH).write_text(
        inventory_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    matrix_lines = []
    for line in matrix_source.read_text(encoding="utf-8").splitlines():
        if "[#469]" in line:
            line = line.replace(
                "The evidence-classification campaign #393 same-pattern",
                "The same-pattern",
            ).replace("campaign #393", "campaign 393")
        matrix_lines.append(line)
    (tmp_path / ISSUE_CLOSURE_MATRIX_PATH).write_text(
        "\n".join(matrix_lines),
        encoding="utf-8",
    )

    errors = module.evidence_inventory.evidence_classification_inventory_errors(root=tmp_path)

    assert errors == [
        "docs/architecture/implementation-proof-evidence-classification.md: "
        "completed inventory occurrences lack campaign registration: #469"
    ]


def test_documentation_contract_gate_blocks_missing_surface(tmp_path: Path) -> None:
    module = _load_gate()
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: required documentation surface is missing"]


def test_documentation_contract_gate_blocks_thin_surface(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text("# Service\nProduct Boundary\n", encoding="utf-8")
    surface = module.DocumentationSurface(
        "README.md",
        3,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: has 2 non-empty lines; minimum is 3"]


def test_documentation_contract_gate_blocks_bloated_surface(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text(
        "\n".join(("# Service", "Product Boundary", "Quick Start", "Extra line")),
        encoding="utf-8",
    )
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
        3,
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: has 4 non-empty lines; maximum is 3"]


def test_documentation_contract_gate_blocks_missing_anchor(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text("# Service\nBoundary\n", encoding="utf-8")
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: missing required fragment `Product Boundary`"]


def test_documentation_contract_gate_blocks_placeholder_text(tmp_path: Path) -> None:
    module = _load_gate()
    readme = tmp_path / "README.md"
    readme.write_text("# Service\nProduct Boundary\nTODO: fill later\n", encoding="utf-8")
    surface = module.DocumentationSurface(
        "README.md",
        1,
        ("Product Boundary",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == ["README.md: contains placeholder text `TODO`"]


def test_documentation_contract_gate_blocks_stale_maturity_summary_claim(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "docs" / "operations" / "api-certification.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# API Certification\n\n"
        "Core publishes explicit maturity summary facts before this endpoint is current.\n",
        encoding="utf-8",
    )
    surface = module.DocumentationSurface(
        "docs/operations/api-certification.md",
        1,
        ("API Certification",),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == [
        "docs/operations/api-certification.md: bond-maturity API certification must "
        "describe current PortfolioMaturitySummary:v1 consumption, not the superseded "
        "Core #686 blocker"
    ]


def test_documentation_contract_gate_blocks_superseded_current_issue_posture(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "wiki" / "Validation-and-CI.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Validation and CI\n\n"
        "Current governed posture remains 93 label-backed RFC-0002 issues, "
        "56 closed, and 37 open.\n",
        encoding="utf-8",
    )

    errors = module.rfc0002_issue_posture_snapshot_errors(root=tmp_path)

    assert errors == [
        "wiki/Validation-and-CI.md: paragraph 2 describes a superseded "
        "RFC-0002 issue-count snapshot as current/live posture; use `then-current` "
        "or update the count from `make rfc0002-cross-repo-issue-posture`"
    ]


def test_documentation_contract_gate_allows_then_current_issue_posture_snapshot(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "wiki" / "Validation-and-CI.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Validation and CI\n\n"
        "The then-current governed posture was 93 label-backed RFC-0002 issues, "
        "56 closed, and 37 open.\n",
        encoding="utf-8",
    )

    errors = module.rfc0002_issue_posture_snapshot_errors(root=tmp_path)

    assert errors == []


def test_documentation_contract_gate_blocks_non_contract_current_issue_posture(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "wiki" / "RFC-Index.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# RFC Index\n\n"
        "Current summary: RFC-0002 has 127 label-backed RFC-0002 issues across "
        "13 repositories: 89 closed and 38 open. Open status is "
        "25 `status/blocked`, 1 `status/in-progress`, 1 `status/merged-main`, "
        "2 `status/merged-to-main`, and 8 `status/tracker`; blocked actionability "
        "remains 0 app-actionable blocked issues.\n",
        encoding="utf-8",
    )

    errors = module.rfc0002_issue_posture_snapshot_errors(root=tmp_path)

    assert errors == [
        "wiki/RFC-Index.md: paragraph 2 describes current/live RFC-0002 issue posture "
        "without contract-backed crossRepo fragment(s): "
        "`183 label-backed RFC-0002 issues`, `146 closed and 37 open`, "
        "`25 `status/blocked`, 1 `status/in-progress`, 1 `status/merged-main`, 2 `status/merged-to-main`, 0 `status/pr-open`, 8 `status/tracker``"
    ]


def test_documentation_contract_gate_allows_contract_current_issue_posture(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    contract_path = (
        tmp_path / "contracts" / "implementation-proof" / "rfc0002-issue-posture-snapshot.v1.json"
    )
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        json.dumps(
            {
                "schemaVersion": "lotus-idea:rfc0002-issue-posture-snapshot:v1",
                "expectedCurrentFragments": {
                    "ideaLedger": [
                        "59 tracked RFC-0002 issues",
                        "34 closed and 25 open",
                        "#681",
                    ],
                    "crossRepo": [
                        "128 label-backed RFC-0002 issues",
                        "91 closed and 37 open",
                        "25 `status/blocked`, 1 `status/in-progress`",
                        "0 app-actionable blocked",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    doc = tmp_path / "REPOSITORY-ENGINEERING-CONTEXT.md"
    doc.write_text(
        "# Repository Engineering Context\n\n"
        "Current Idea ledger posture has 59 tracked RFC-0002 issues, "
        "34 closed and 25 open; #681 is the in-progress Slice 18 "
        "tracker. Current governed cross-repo RFC-0002 posture has "
        "128 label-backed RFC-0002 issues across 13 repositories: 91 closed "
        "and 37 open. The open split is 25 `status/blocked`, "
        "1 `status/in-progress`, 1 `status/merged-main`, "
        "2 `status/merged-to-main`, and 8 `status/tracker`; "
        "blocked actionability remains 0 app-actionable blocked issues.\n",
        encoding="utf-8",
    )

    errors = module.rfc0002_issue_posture_snapshot_errors(root=tmp_path)

    assert errors == []


def test_documentation_contract_gate_blocks_stale_review_ledger_closure_truth(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    ledger_path = tmp_path / "docs" / "architecture" / "CODEBASE-REVIEW-LEDGER.md"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        "# Codebase Review Ledger\n\n"
        "| Review ID | Scope / Pattern | Status | Finding | Action Taken | Evidence | Follow-up |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| `LI-CR-0115` | Drawdown-review signal evaluation | "
        "`Closed on main` | Issue `#661` | PR `#665` merged | "
        "`6b562ac87ca61575c13fefc63b8c688c915da3fc`; "
        "Main Releasability `29671128884` | Issue `#661` is closed. |\n"
        "| `LI-CR-0116` | Live Core receipt observation | "
        "`Closed on main` | Issue `#657` | PR `#660` merged | "
        "`7aa14e0174b2584110d1d217e31f06c24b1bd153`; "
        "Main Releasability `29667502188` | Issue `#657` is closed. |\n"
        "| `LI-CR-0117` | Proof import guard | "
        "`Closed on main` | Issue `#664` | PR `#665` merged | "
        "`6b562ac87ca61575c13fefc63b8c688c915da3fc`; "
        "Main Releasability `29671128884` | Issue `#664` is closed. |\n"
        "| `LI-CR-0120` | High-volatility signal evaluation | "
        "`Fixed locally; PR/main validation pending` | Issue `#862` | "
        "PR `#863` merged | Main Releasability pending | "
        "Complete PR checks before closure. |\n",
        encoding="utf-8",
    )

    errors = module.review_ledger.codebase_review_ledger_closure_errors(root=tmp_path)

    assert errors == [
        "docs/architecture/CODEBASE-REVIEW-LEDGER.md: "
        "`LI-CR-0120` retains stale local/pending posture after merged-main closure",
        "docs/architecture/CODEBASE-REVIEW-LEDGER.md: "
        "`LI-CR-0120` must be marked closed or hardened on main",
        "docs/architecture/CODEBASE-REVIEW-LEDGER.md: "
        "`LI-CR-0120` missing merged-main evidence fragment "
        "``7ab7bec457f7da1982d91f5238217914d96bb583``",
        "docs/architecture/CODEBASE-REVIEW-LEDGER.md: "
        "`LI-CR-0120` missing merged-main evidence fragment "
        "`Main Releasability `31303468026``",
        "docs/architecture/CODEBASE-REVIEW-LEDGER.md: "
        "`LI-CR-0120` missing merged-main evidence fragment "
        "`Issue `#862` is closed with `status/merged-main``",
    ]


def test_documentation_contract_gate_blocks_unpolished_operator_doc(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "docs" / "operations" / "implementation-proof-readiness.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Implementation Proof Readiness\n\n"
        "This endpoint reports readiness.\n\n"
        "## Evidence\n\n"
        "Run the tests.\n",
        encoding="utf-8",
    )
    surface = module.PolishedDocumentationSurface(
        "docs/operations/implementation-proof-readiness.md",
        ("## What It Proves", "## Evidence"),
        1,
        1,
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(surface,),
    )

    assert errors == [
        "docs/operations/implementation-proof-readiness.md: missing polished heading `## What It Proves`",
        "docs/operations/implementation-proof-readiness.md: has 0 markdown tables; minimum is 1",
        "docs/operations/implementation-proof-readiness.md: has 0 code fences; minimum is 1",
    ]


def test_documentation_contract_gate_requires_downstream_outcome_mainline_evidence(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "docs" / "operations" / "downstream-realization-readiness.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Downstream Realization Readiness\n\n"
        "## Downstream Outcome Certification Aggregate Proof\n\n"
        "The proof exists but this stale doc omits exact PR, mainline run, and "
        "keep-open evidence.\n",
        encoding="utf-8",
    )
    surface = module.DocumentationSurface(
        "docs/operations/downstream-realization-readiness.md",
        1,
        (
            "Downstream Outcome Certification Aggregate Proof",
            "PR #742 merged this aggregate proof to `main`",
            "`30323405962` passed for that exact SHA",
            "issue #379 remains open in `status/blocked`",
            "supporting proof only",
        ),
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(surface,),
        polished_surfaces=(),
    )

    assert errors == [
        "docs/operations/downstream-realization-readiness.md: missing required fragment "
        "`PR #742 merged this aggregate proof to `main``",
        "docs/operations/downstream-realization-readiness.md: missing required fragment "
        "``30323405962` passed for that exact SHA`",
        "docs/operations/downstream-realization-readiness.md: missing required fragment "
        "`issue #379 remains open in `status/blocked``",
        "docs/operations/downstream-realization-readiness.md: missing required fragment "
        "`supporting proof only`",
    ]


def test_documentation_contract_gate_blocks_missing_required_diagram(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "wiki" / "Architecture.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Architecture\n\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| Source Authority | lotus-core |\n\n"
        "## Source Authority\n\n"
        "Source ownership summary.\n",
        encoding="utf-8",
    )
    surface = module.PolishedDocumentationSurface(
        "wiki/Architecture.md",
        ("## Source Authority",),
        1,
        0,
        1,
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(surface,),
    )

    assert errors == ["wiki/Architecture.md: has 0 Mermaid diagrams; minimum is 1"]


def test_documentation_contract_gate_blocks_same_wiki_markdown_suffix_links(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "Home.md").write_text("[Overview](Overview.md)\n", encoding="utf-8")
    (wiki / "Overview.md").write_text("# Overview\n", encoding="utf-8")

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(),
    )

    assert errors == [
        "wiki/Home.md: same-wiki link `Overview.md` must omit `.md` for GitHub wiki navigation"
    ]


def test_documentation_contract_gate_allows_deep_document_markdown_links(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    wiki = tmp_path / "wiki"
    docs = tmp_path / "docs" / "demo"
    wiki.mkdir()
    docs.mkdir(parents=True)
    (wiki / "Demo-Readiness.md").write_text(
        "[Demo guide](../docs/demo/README.md)\n",
        encoding="utf-8",
    )
    (docs / "README.md").write_text("# Demo\n", encoding="utf-8")

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(),
    )

    assert errors == []


def test_documentation_contract_gate_accepts_polished_operator_doc(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    doc = tmp_path / "docs" / "operations" / "implementation-proof-readiness.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "# Implementation Proof Readiness\n\n"
        "| Field | Current Truth |\n"
        "| --- | --- |\n"
        "| Status | Certified internal diagnostic |\n\n"
        "## What It Proves\n\n"
        "It proves the aggregate readiness posture.\n\n"
        "## Evidence\n\n"
        "```powershell\n"
        "make implementation-proof-readiness-check\n"
        "```\n",
        encoding="utf-8",
    )
    surface = module.PolishedDocumentationSurface(
        "docs/operations/implementation-proof-readiness.md",
        ("## What It Proves", "## Evidence"),
        1,
        1,
    )

    errors = module.validate_documentation_contract(
        root=tmp_path,
        surfaces=(),
        polished_surfaces=(surface,),
    )

    assert errors == []
