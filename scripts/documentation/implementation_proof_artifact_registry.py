from __future__ import annotations

import inspect
from pathlib import Path

from app.application.implementation_proof_artifact_registry import (
    IMPLEMENTATION_PROOF_ARTIFACT_SPECS,
    ProofArtifactClassificationStatus,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)

try:
    from scripts.generate_implementation_proof_readiness import _parser
except ModuleNotFoundError:
    from generate_implementation_proof_readiness import _parser  # type: ignore[import-not-found,no-redef]


INVENTORY_PATH = Path("docs/architecture/implementation-proof-evidence-classification.md")


def implementation_proof_artifact_registry_errors(*, root: Path) -> list[str]:
    errors: list[str] = []
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

    parser_flags = {
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
        )
    }
    registry_flags = set(flags)
    if parser_flags != registry_flags:
        errors.append(
            "implementation proof artifact registry/CLI drift: "
            f"missing={sorted(parser_flags - registry_flags)} "
            f"unexpected={sorted(registry_flags - parser_flags)}"
        )

    readiness_parameters = inspect.signature(
        build_implementation_proof_readiness_snapshot
    ).parameters
    for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS:
        if spec.payload_argument and spec.payload_argument not in readiness_parameters:
            errors.append(
                f"{spec.cli_flag}: missing readiness payload argument `{spec.payload_argument}`"
            )
        if spec.ref_argument not in readiness_parameters:
            errors.append(
                f"{spec.cli_flag}: missing readiness reference argument `{spec.ref_argument}`"
            )

    inventory_path = root / INVENTORY_PATH
    if not inventory_path.is_file():
        return errors
    inventory = inventory_path.read_text(encoding="utf-8")
    for spec in IMPLEMENTATION_PROOF_ARTIFACT_SPECS:
        row_prefix = f"| {spec.inventory_label} |"
        matching_rows = [line for line in inventory.splitlines() if line.startswith(row_prefix)]
        if len(matching_rows) != 1:
            errors.append(f"{INVENTORY_PATH.as_posix()}: expected one `{spec.inventory_label}` row")
            continue
        row = matching_rows[0]
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
            errors.append(
                f"{INVENTORY_PATH.as_posix()}: `{spec.inventory_label}` must remain pending"
            )
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
    return errors


def _append_duplicate_errors(
    errors: list[str],
    *,
    values: list[str],
    field_name: str,
) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        errors.append(
            f"implementation proof artifact registry has duplicate {field_name}: {duplicates}"
        )
