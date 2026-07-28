from __future__ import annotations

import re


def validate_workbench_runtime_proof_timestamp(makefile: str) -> list[str]:
    errors: list[str] = []
    gateway_workbench_runtime_block = _target_block(
        makefile,
        "gateway-workbench-runtime-execution-proof",
    )
    if (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF_GENERATED_AT_UTC ?= "
        "$(BUILD_TIMESTAMP)"
    ) not in makefile:
        errors.append(
            "Makefile must default Gateway/Workbench runtime proof generation to "
            "`$(BUILD_TIMESTAMP)`"
        )
    if (
        "--generated-at-utc "
        "$(LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF_GENERATED_AT_UTC)"
    ) not in gateway_workbench_runtime_block:
        errors.append(
            "Makefile gateway-workbench-runtime-execution-proof target must use the "
            "fresh runtime proof timestamp variable"
        )
    if "--generated-at-utc $(IMPLEMENTATION_PROOF_EVALUATED_AT_UTC)" in (
        gateway_workbench_runtime_block
    ):
        errors.append(
            "Makefile gateway-workbench-runtime-execution-proof target must not use the "
            "static implementation proof timestamp"
        )
    return errors


def _target_block(makefile: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:.*?(?=^\S|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(makefile)
    return match.group(0) if match else ""
