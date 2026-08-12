# ruff: noqa: E402
from __future__ import annotations

import inspect
from collections.abc import Iterable
from dataclasses import fields
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.implementation_proof_artifact_registry import (
    IMPLEMENTATION_PROOF_ARTIFACT_SPECS,
    ImplementationProofArtifactSpec,
    ProofArtifactClassificationStatus,
)
from app.application.implementation_proof_readiness import (
    ImplementationProofReadinessProofInputs,
    build_implementation_proof_readiness_snapshot,
)

try:
    from scripts.generate_implementation_proof_readiness import _parser
except ModuleNotFoundError:
    from generate_implementation_proof_readiness import _parser  # type: ignore[import-not-found,no-redef]


INVENTORY_PATH = Path("docs/architecture/implementation-proof-evidence-classification.md")


def implementation_proof_artifact_registry_errors(*, root: Path) -> list[str]:
    errors: list[str] = []
    _append_registry_key_errors(errors)
    _append_cli_drift_errors(errors)
    _append_readiness_argument_errors(errors)
    _append_inventory_errors(errors, root=root)
    return errors


def _append_registry_key_errors(errors: list[str]) -> None:
    flags = [spec.cli_flag for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS]
    _append_duplicate_errors(errors, values=flags, field_name="flags")
    _append_duplicate_errors(
        errors,
        values=[
            spec.payload_argument
            for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS
            if spec.payload_argument is not None
        ],
        field_name="payload arguments",
    )
    _append_duplicate_errors(
        errors,
        values=[spec.ref_argument for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS],
        field_name="reference arguments",
    )


def _append_cli_drift_errors(errors: list[str]) -> None:
    parser_flags = _parser_proof_artifact_flags()
    registry_flags = {spec.cli_flag for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS}
    if parser_flags != registry_flags:
        errors.append(
            "implementation proof artifact registry/CLI drift: "
            f"missing={sorted(parser_flags - registry_flags)} "
            f"unexpected={sorted(registry_flags - parser_flags)}"
        )


def _parser_proof_artifact_flags() -> set[str]:
    return {
        option
        for action in _parser()._actions
        for option in action.option_strings
        if option.startswith("--")
        and (
            "proof" in option
            or "runtime-execution" in option
            or "test-execution" in option
            or "source-contract" in option
            or "deployment-evidence" in option
            or "evidence-pack" in option
        )
    }


def _append_readiness_argument_errors(errors: list[str]) -> None:
    readiness_parameters = _readiness_proof_parameters()
    for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS:
        if spec.payload_argument and spec.payload_argument not in readiness_parameters:
            errors.append(
                f"{spec.cli_flag}: missing readiness payload argument `{spec.payload_argument}`"
            )
        if spec.ref_argument not in readiness_parameters:
            errors.append(
                f"{spec.cli_flag}: missing readiness reference argument `{spec.ref_argument}`"
            )


def _readiness_proof_parameters() -> set[str]:
    return {
        *inspect.signature(build_implementation_proof_readiness_snapshot).parameters,
        *(field.name for field in fields(ImplementationProofReadinessProofInputs)),
    }


def _append_inventory_errors(errors: list[str], *, root: Path) -> None:
    inventory_path = root / INVENTORY_PATH
    if not inventory_path.is_file():
        return
    inventory = inventory_path.read_text(encoding="utf-8")
    for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS:
        row_prefix = f"| {spec.inventory_label} |"
        matching_rows = [line for line in inventory.splitlines() if line.startswith(row_prefix)]
        if len(matching_rows) != 1:
            errors.append(f"{INVENTORY_PATH.as_posix()}: expected one `{spec.inventory_label}` row")
            continue
        _append_inventory_row_errors(errors, spec=spec, row=matching_rows[0])


def _append_inventory_row_errors(
    errors: list[str],
    *,
    spec: ImplementationProofArtifactSpec,
    row: str,
) -> None:
    columns = [column.strip() for column in row.strip().strip("|").split("|")]
    classification = columns[1] if len(columns) > 1 else ""
    if f"#{spec.tracking_issue}" not in row:
        errors.append(
            f"{INVENTORY_PATH.as_posix()}: `{spec.inventory_label}` must track "
            f"#{spec.tracking_issue}"
        )
    if (
        spec.status is ProofArtifactClassificationStatus.PENDING_CORRECTION
        and "pending" not in row.lower()
    ):
        errors.append(f"{INVENTORY_PATH.as_posix()}: `{spec.inventory_label}` must remain pending")
    evidence_class = spec.evidence_class
    if (
        spec.status is ProofArtifactClassificationStatus.CLASSIFIED
        and evidence_class is not None
        and f"`{evidence_class.value}`" not in classification
    ):
        errors.append(
            f"{INVENTORY_PATH.as_posix()}: `{spec.inventory_label}` must name "
            f"`{evidence_class.value}`"
        )


def _append_duplicate_errors(
    errors: list[str],
    *,
    values: Iterable[str],
    field_name: str,
) -> None:
    values = list(values)
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        errors.append(
            f"implementation proof artifact registry has duplicate {field_name}: {duplicates}"
        )
