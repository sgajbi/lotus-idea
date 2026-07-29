from __future__ import annotations

from ci_contract_gate_expectations import (
    GENERATED_READINESS_ARTIFACTS,
    PASSED_READINESS_ARTIFACTS,
    REQUIRED_READINESS_WIRING,
)

READINESS_TARGET = "Makefile implementation-proof-readiness-check target"
READINESS_DEFAULT_OUTPUT = (
    "LOTUS_IDEA_IMPLEMENTATION_PROOF_READINESS_OUTPUT ?= "
    "output/implementation-proof/readiness-current.json"
)


def validate_implementation_proof_readiness_target(makefile: str, target_block: str) -> list[str]:
    errors: list[str] = []
    if READINESS_DEFAULT_OUTPUT not in makefile:
        errors.append(
            f"{READINESS_TARGET} must define the default aggregate implementation proof "
            "readiness output artifact"
        )
    for marker, description in GENERATED_READINESS_ARTIFACTS:
        if marker not in target_block:
            errors.append(f"{READINESS_TARGET} must generate {description}")
    for marker, description in PASSED_READINESS_ARTIFACTS:
        if marker not in target_block:
            errors.append(
                f"{READINESS_TARGET} must pass the {description} into readiness generation"
            )
    for marker, requirement in REQUIRED_READINESS_WIRING:
        if marker not in target_block:
            errors.append(f"{READINESS_TARGET} must {requirement}")
    if target_block.count("--allow-missing-evidence") < 6:
        errors.append(
            f"{READINESS_TARGET} must keep all cross-repo proof generators CI-stable when "
            "sibling evidence is absent"
        )
    return errors
