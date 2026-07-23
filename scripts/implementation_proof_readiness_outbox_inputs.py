from __future__ import annotations

import argparse
from typing import Any


def outbox_proof_artifact_inputs(
    args: argparse.Namespace,
    proof_artifact_input: Any,
) -> dict[str, Any]:
    return {
        "outbox_broker_source_contract": proof_artifact_input(
            args.outbox_broker_source_contract_proof,
            artifact_name="outbox broker source-contract proof",
            ref_name="outbox broker source-contract proof artifact",
        ),
        "outbox_broker_runtime_execution": proof_artifact_input(
            args.outbox_broker_runtime_execution_proof,
            artifact_name="outbox broker runtime execution proof",
            ref_name="outbox broker runtime execution proof artifact",
        ),
        "outbox_consumer_contract": proof_artifact_input(
            args.outbox_consumer_contract_proof,
            artifact_name="outbox consumer contract proof",
            ref_name="outbox consumer contract proof artifact",
        ),
        "outbox_consumer_runtime_execution": proof_artifact_input(
            args.outbox_consumer_runtime_execution_proof,
            artifact_name="outbox consumer runtime execution proof",
            ref_name="outbox consumer runtime execution proof artifact",
        ),
        "outbox_platform_mesh_event_source_contract": proof_artifact_input(
            args.outbox_platform_mesh_event_source_contract_proof,
            artifact_name="outbox platform-mesh event source-contract proof",
            ref_name="outbox platform-mesh event source-contract proof artifact",
        ),
    }
