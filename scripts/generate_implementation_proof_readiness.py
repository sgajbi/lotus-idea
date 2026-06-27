from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.application.ai_lineage_store_proof import AI_LINEAGE_STORE_PROOF_ENV
from app.application.ai_model_risk_operations_proof import (
    AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
)
from app.application.ai_workflow_pack_registration_proof import (
    AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
    AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
)
from app.application.durable_repository_proof import DURABLE_REPOSITORY_PROOF_ENV
from app.application.downstream_route_contract_proof import (
    ADVISE_PROPOSAL_ROUTE_PROOF_ENV,
    MANAGE_ACTION_ROUTE_PROOF_ENV,
)
from app.application.implementation_proof_readiness import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
    build_implementation_proof_readiness_snapshot,
)
from app.application.mesh_policy_proof import MESH_POLICY_PROOF_ENV
from app.application.outbox_broker_proof import OUTBOX_BROKER_PROOF_ENV
from app.application.outbox_consumer_runtime_proof import (
    OUTBOX_CONSUMER_RUNTIME_PROOF_ENV,
)
from app.application.platform_mesh_onboarding_proof import (
    PLATFORM_MESH_ONBOARDING_PROOF_ENV,
)
from app.application.report_intake_route_proof import REPORT_INTAKE_ROUTE_PROOF_ENV
from app.application.report_materialization_proof import REPORT_MATERIALIZATION_PROOF_ENV
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.application.runtime_trust_telemetry_proof import RUNTIME_TRUST_TELEMETRY_PROOF_ENV
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.workbench_read_path_proof import WORKBENCH_READ_PATH_PROOF_ENV


@dataclass(frozen=True)
class ProofArtifactInput:
    payload: dict[str, Any] | None
    path: Path | None
    ref_name: str


@dataclass(frozen=True)
class ProofArtifactInputs:
    durable_repository: ProofArtifactInput
    runtime_trust_telemetry: ProofArtifactInput
    ai_lineage_store: ProofArtifactInput
    ai_model_risk_operations: ProofArtifactInput
    ai_workflow_pack_registration: ProofArtifactInput
    ai_workflow_pack_runtime_execution: ProofArtifactInput
    advise_proposal_route: ProofArtifactInput
    manage_action_route: ProofArtifactInput
    report_intake_route: ProofArtifactInput
    report_materialization: ProofArtifactInput
    mesh_policy: ProofArtifactInput
    workbench_read_path: ProofArtifactInput
    outbox_broker: ProofArtifactInput
    outbox_consumer_runtime: ProofArtifactInput
    platform_mesh_onboarding: ProofArtifactInput


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        evaluated_at_utc = _parse_evaluated_at_utc(args.evaluated_at_utc)
        with _temporary_environment(_readiness_environment_overrides(args)):
            repository = get_idea_repository()
            proof_artifacts = _proof_artifact_inputs(args)
            snapshot = build_implementation_proof_readiness_snapshot(
                evaluated_at_utc=evaluated_at_utc,
                repository=repository,
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
                source_ingestion_live_proof_ref=_source_safe_artifact_ref(
                    _resolve_optional_path(args.source_ingestion_live_proof),
                    artifact_name="source ingestion live proof artifact",
                ),
                source_ingestion_scheduled_worker_proof_ref=_source_safe_artifact_ref(
                    _resolve_optional_path(args.source_ingestion_scheduled_worker_proof),
                    artifact_name="source ingestion scheduled-worker proof artifact",
                ),
                **_proof_payload_kwargs(proof_artifacts),
            )
        payload = implementation_proof_readiness_payload(snapshot)
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"{rendered}\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"implementation proof readiness error: {exc}", file=sys.stderr)
        return 2


def implementation_proof_readiness_payload(
    snapshot: ImplementationProofReadinessSnapshot,
) -> dict[str, Any]:
    return {
        "repository": snapshot.repository,
        "evaluatedAtUtc": _format_utc(snapshot.evaluated_at_utc),
        "readinessStatus": snapshot.readiness_status,
        "supportabilityStatus": snapshot.supportability_status,
        "certificationReady": snapshot.certification_ready,
        "capabilityCount": snapshot.capability_count,
        "certificationReadyCapabilityCount": snapshot.certification_ready_capability_count,
        "blockedCapabilityCount": snapshot.blocked_capability_count,
        "supportedFeatureCount": snapshot.supported_feature_count,
        "supportedFeaturesPromoted": snapshot.supported_features_promoted,
        "overallBlockers": list(snapshot.overall_blockers),
        "sourceOfTruth": dict(snapshot.source_of_truth),
        "capabilities": [_capability_payload(capability) for capability in snapshot.capabilities],
        "supportedFeaturePromoted": False,
    }


def _capability_payload(
    capability: ImplementationProofCapabilityReadiness,
) -> dict[str, Any]:
    return {
        "capabilityId": capability.capability_id,
        "name": capability.name,
        "readinessStatus": capability.readiness_status,
        "supportabilityStatus": capability.supportability_status,
        "certificationReady": capability.certification_ready,
        "evidenceRefs": list(capability.evidence_refs),
        "blockers": list(capability.blockers),
        "supportedFeaturePromoted": capability.supported_feature_promoted,
    }


def _proof_payload_kwargs(input_: ProofArtifactInputs) -> dict[str, Any]:
    proof_fields = (
        "durable_repository",
        "runtime_trust_telemetry",
        "ai_lineage_store",
        "ai_model_risk_operations",
        "ai_workflow_pack_registration",
        "ai_workflow_pack_runtime_execution",
        "advise_proposal_route",
        "manage_action_route",
        "report_intake_route",
        "report_materialization",
        "mesh_policy",
        "outbox_broker",
        "outbox_consumer_runtime",
        "platform_mesh_onboarding",
        "workbench_read_path",
    )
    kwargs: dict[str, Any] = {}
    for field_name in proof_fields:
        artifact = getattr(input_, field_name)
        kwargs[f"{field_name}_proof"] = artifact.payload
        kwargs[f"{field_name}_proof_ref"] = _proof_ref(artifact)
    return kwargs


def _proof_artifact_input(
    path_value: str | None,
    *,
    artifact_name: str,
    ref_name: str,
) -> ProofArtifactInput:
    path = _resolve_optional_path(path_value)
    return ProofArtifactInput(
        payload=_read_optional_json_object(path, artifact_name=artifact_name),
        path=path,
        ref_name=ref_name,
    )


def _proof_ref(input_: ProofArtifactInput) -> str | None:
    return _source_safe_artifact_ref(input_.path, artifact_name=input_.ref_name)


def _proof_artifact_inputs(args: argparse.Namespace) -> ProofArtifactInputs:
    return ProofArtifactInputs(
        durable_repository=_proof_artifact_input(
            args.durable_repository_proof,
            artifact_name="durable repository proof",
            ref_name="durable repository proof artifact",
        ),
        runtime_trust_telemetry=_proof_artifact_input(
            args.runtime_trust_telemetry_proof,
            artifact_name="runtime trust telemetry proof",
            ref_name="runtime trust telemetry proof artifact",
        ),
        ai_lineage_store=_proof_artifact_input(
            args.ai_lineage_store_proof,
            artifact_name="AI lineage store proof",
            ref_name="AI lineage store proof artifact",
        ),
        ai_model_risk_operations=_proof_artifact_input(
            args.ai_model_risk_operations_proof,
            artifact_name="AI model-risk operations proof",
            ref_name="AI model-risk operations proof artifact",
        ),
        ai_workflow_pack_registration=_proof_artifact_input(
            args.ai_workflow_pack_registration_proof,
            artifact_name="AI workflow-pack registration proof",
            ref_name="AI workflow-pack registration proof artifact",
        ),
        ai_workflow_pack_runtime_execution=_proof_artifact_input(
            args.ai_workflow_pack_runtime_execution_proof,
            artifact_name="AI workflow-pack runtime execution proof",
            ref_name="AI workflow-pack runtime execution proof artifact",
        ),
        advise_proposal_route=_proof_artifact_input(
            args.advise_proposal_route_proof,
            artifact_name="Advise proposal route proof",
            ref_name="Advise proposal route proof artifact",
        ),
        manage_action_route=_proof_artifact_input(
            args.manage_action_route_proof,
            artifact_name="Manage action route proof",
            ref_name="Manage action route proof artifact",
        ),
        report_intake_route=_proof_artifact_input(
            args.report_intake_route_proof,
            artifact_name="report intake route proof",
            ref_name="report intake route proof artifact",
        ),
        report_materialization=_proof_artifact_input(
            args.report_materialization_proof,
            artifact_name="report materialization proof",
            ref_name="report materialization proof artifact",
        ),
        mesh_policy=_proof_artifact_input(
            args.mesh_policy_proof,
            artifact_name="mesh policy proof",
            ref_name="mesh policy proof artifact",
        ),
        workbench_read_path=_proof_artifact_input(
            args.workbench_read_path_proof,
            artifact_name="workbench read-path proof",
            ref_name="workbench read-path proof artifact",
        ),
        outbox_broker=_proof_artifact_input(
            args.outbox_broker_proof,
            artifact_name="outbox broker proof",
            ref_name="outbox broker proof artifact",
        ),
        outbox_consumer_runtime=_proof_artifact_input(
            args.outbox_consumer_runtime_proof,
            artifact_name="outbox consumer runtime proof",
            ref_name="outbox consumer runtime proof artifact",
        ),
        platform_mesh_onboarding=_proof_artifact_input(
            args.platform_mesh_onboarding_proof,
            artifact_name="platform mesh onboarding proof",
            ref_name="platform mesh onboarding proof artifact",
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate lotus-idea RFC-0002 proof readiness JSON."
    )
    parser.add_argument(
        "--evaluated-at-utc",
        required=True,
        help="Timezone-aware evaluation instant, for example 2026-06-21T10:10:00Z.",
    )
    parser.add_argument("--output", help="Optional JSON output path.")
    _add_runtime_context_args(parser)
    _add_proof_artifact_args(parser)
    return parser


def _add_runtime_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source-ingestion-manifest",
        help=(
            f"Optional manifest path to expose to readiness as {MANIFEST_ENV}. "
            "Useful for deterministic CI proof snapshots."
        ),
    )
    parser.add_argument(
        "--core-base-url",
        help=(
            f"Optional compatibility Core base URL to expose to readiness as {CORE_BASE_URL_ENV}. "
            "Prefer the split query and query-control-plane URL arguments for live Core proof."
        ),
    )
    parser.add_argument(
        "--core-query-base-url",
        help=f"Optional Core query-service base URL to expose as {CORE_QUERY_BASE_URL_ENV}.",
    )
    parser.add_argument(
        "--core-query-control-plane-base-url",
        help=(
            "Optional Core query-control-plane base URL to expose as "
            f"{CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV}."
        ),
    )
    parser.add_argument(
        "--source-ingestion-live-proof",
        help=f"Optional live Core proof artifact path to expose as {LIVE_PROOF_ENV}.",
    )
    parser.add_argument(
        "--source-ingestion-scheduled-worker-proof",
        help=(
            "Optional scheduled source-ingestion worker proof artifact path to expose as "
            f"{SCHEDULED_WORKER_PROOF_ENV}."
        ),
    )


def _add_proof_artifact_args(parser: argparse.ArgumentParser) -> None:
    proof_args = (
        (
            "--durable-repository-proof",
            DURABLE_REPOSITORY_PROOF_ENV,
            "Optional durable PostgreSQL repository proof artifact path.",
        ),
        (
            "--runtime-trust-telemetry-proof",
            RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
            "Optional runtime trust telemetry candidate snapshot proof artifact path.",
        ),
        (
            "--ai-lineage-store-proof",
            AI_LINEAGE_STORE_PROOF_ENV,
            "Optional durable AI explanation lineage store proof artifact path.",
        ),
        (
            "--ai-model-risk-operations-proof",
            AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
            "Optional AI model-risk operations dashboard and alert proof artifact path.",
        ),
        (
            "--ai-workflow-pack-registration-proof",
            AI_WORKFLOW_PACK_REGISTRATION_PROOF_ENV,
            "Optional lotus-ai idea workflow-pack registration proof artifact path.",
        ),
        (
            "--ai-workflow-pack-runtime-execution-proof",
            AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_ENV,
            "Optional lotus-ai idea workflow-pack runtime execution proof artifact path.",
        ),
        (
            "--advise-proposal-route-proof",
            ADVISE_PROPOSAL_ROUTE_PROOF_ENV,
            "Optional lotus-advise idea proposal route proof artifact path.",
        ),
        (
            "--manage-action-route-proof",
            MANAGE_ACTION_ROUTE_PROOF_ENV,
            "Optional lotus-manage idea action route proof artifact path.",
        ),
        (
            "--report-intake-route-proof",
            REPORT_INTAKE_ROUTE_PROOF_ENV,
            "Optional lotus-report idea evidence intake route proof artifact path.",
        ),
        (
            "--report-materialization-proof",
            REPORT_MATERIALIZATION_PROOF_ENV,
            "Optional lotus-report idea evidence materialization proof artifact path.",
        ),
        (
            "--mesh-policy-proof",
            MESH_POLICY_PROOF_ENV,
            "Optional repo-owned mesh SLO, access, and evidence policy proof artifact path.",
        ),
        (
            "--workbench-read-path-proof",
            WORKBENCH_READ_PATH_PROOF_ENV,
            "Optional bounded Workbench read-path proof artifact path.",
        ),
        (
            "--outbox-broker-proof",
            OUTBOX_BROKER_PROOF_ENV,
            "Optional bounded outbox broker runtime proof artifact path.",
        ),
        (
            "--outbox-consumer-runtime-proof",
            OUTBOX_CONSUMER_RUNTIME_PROOF_ENV,
            "Optional bounded outbox downstream consumer runtime proof artifact path.",
        ),
        (
            "--platform-mesh-onboarding-proof",
            PLATFORM_MESH_ONBOARDING_PROOF_ENV,
            "Optional platform source-manifest and catalog onboarding proof artifact path.",
        ),
    )
    for flag, env_name, description in proof_args:
        parser.add_argument(
            flag,
            default=os.getenv(env_name),
            help=f"{description} Defaults to {env_name} when set.",
        )


def _parse_evaluated_at_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evaluated-at-utc must be timezone-aware")
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _readiness_environment_overrides(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        MANIFEST_ENV: args.source_ingestion_manifest,
        CORE_BASE_URL_ENV: args.core_base_url,
        CORE_QUERY_BASE_URL_ENV: args.core_query_base_url,
        CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV: args.core_query_control_plane_base_url,
        LIVE_PROOF_ENV: args.source_ingestion_live_proof,
        SCHEDULED_WORKER_PROOF_ENV: args.source_ingestion_scheduled_worker_proof,
    }


def _resolve_optional_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return Path(path_value)


def _read_optional_json_object(
    path: Path | None,
    *,
    artifact_name: str,
) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact_name} must be a JSON object")
    return payload


def _source_safe_artifact_ref(
    path: Path | None,
    *,
    artifact_name: str,
) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return artifact_name


@contextmanager
def _temporary_environment(overrides: dict[str, str | None]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is not None:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    sys.exit(main())
