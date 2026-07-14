from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.application.implementation_proof_cli_contract import PROOF_ARTIFACT_ARGS
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    CORE_QUERY_BASE_URL_ENV,
    CORE_QUERY_CONTROL_PLANE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.runtime.repository_state import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.runtime.proof_artifact_files import read_optional_json_object

try:
    from scripts.proof_generator_io import write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import write_json_payload  # type: ignore[import-not-found,no-redef]


@dataclass(frozen=True)
class ProofArtifactInput:
    payload: dict[str, Any] | None
    path: Path | None
    proof_ref: str | None
    ref_name: str


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        evaluated_at_utc = _parse_evaluated_at_utc(args.evaluated_at_utc)
        with _temporary_environment(_readiness_environment_overrides(args)):
            repository = get_idea_repository()
            source_ingestion_live_proof = _proof_artifact_input(
                args.source_ingestion_live_proof,
                artifact_name="source ingestion live proof",
                ref_name="source ingestion live proof artifact",
            )
            proof_artifacts = _proof_artifact_inputs(args)
            snapshot = build_implementation_proof_readiness_snapshot(
                evaluated_at_utc=evaluated_at_utc,
                repository=repository,
                durable_storage_backed=idea_repository_durable_storage_backed(repository),
                source_ingestion_live_proof=source_ingestion_live_proof.payload,
                source_ingestion_live_proof_ref=source_ingestion_live_proof.proof_ref,
                source_ingestion_scheduled_worker_proof_ref=_source_safe_artifact_ref(
                    _resolve_optional_path(args.source_ingestion_scheduled_worker_proof),
                    artifact_name="source ingestion scheduled-worker proof artifact",
                ),
                **_proof_payload_kwargs(proof_artifacts),
            )
        payload = implementation_proof_readiness_payload(snapshot)
        write_json_payload(payload, output=args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"implementation proof readiness error: {exc}", file=sys.stderr)
        return 2


def implementation_proof_readiness_payload(
    snapshot: ImplementationProofReadinessSnapshot,
) -> dict[str, Any]:
    return {
        "repository": snapshot.repository,
        "generatedAtUtc": _format_utc(snapshot.evaluated_at_utc),
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
        "supportedFeaturePromoted": snapshot.supported_features_promoted,
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


def _proof_payload_kwargs(input_: Mapping[str, ProofArtifactInput]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for field_name, artifact in input_.items():
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
    proof_ref = _source_safe_artifact_ref(path, artifact_name=ref_name)
    payload = read_optional_json_object(path, artifact_name=artifact_name)
    if payload is not None and path is not None and proof_ref is not None:
        payload = bind_aggregate_proof_provenance(
            payload,
            artifact_path=path,
            proof_ref=proof_ref,
            repository_root=Path.cwd(),
        )
    return ProofArtifactInput(
        payload=payload,
        path=path,
        proof_ref=proof_ref,
        ref_name=ref_name,
    )


def _proof_ref(input_: ProofArtifactInput) -> str | None:
    return input_.proof_ref


def _opportunity_archetype_proof_artifact_inputs(
    args: argparse.Namespace,
) -> dict[str, ProofArtifactInput]:
    return {
        "risk_concentration_live": _proof_artifact_input(
            args.risk_concentration_live_proof,
            artifact_name="Risk concentration live proof",
            ref_name="Risk concentration live proof artifact",
        ),
        "high_volatility_live": _proof_artifact_input(
            args.high_volatility_live_proof,
            artifact_name="High volatility live proof",
            ref_name="High volatility live proof artifact",
        ),
        "risk_drawdown_live": _proof_artifact_input(
            args.risk_drawdown_live_proof,
            artifact_name="Risk drawdown live proof",
            ref_name="Risk drawdown live proof artifact",
        ),
        "performance_underperformance_live": _proof_artifact_input(
            args.performance_underperformance_live_proof,
            artifact_name="Performance underperformance live proof",
            ref_name="Performance underperformance live proof artifact",
        ),
        "core_benchmark_assignment_live": _proof_artifact_input(
            args.core_benchmark_assignment_live_proof,
            artifact_name="Core benchmark assignment live proof",
            ref_name="Core benchmark assignment live proof artifact",
        ),
        "core_portfolio_state_live": _proof_artifact_input(
            args.core_portfolio_state_live_proof,
            artifact_name="Core portfolio-state live proof",
            ref_name="Core portfolio-state live proof artifact",
        ),
        "bond_maturity_live": _proof_artifact_input(
            args.bond_maturity_live_proof,
            artifact_name="Bond maturity live proof",
            ref_name="Bond maturity live proof artifact",
        ),
        "low_income_core_cashflow_live": _proof_artifact_input(
            args.low_income_core_cashflow_live_proof,
            artifact_name="Low-income Core cashflow live proof",
            ref_name="Low-income Core cashflow live proof artifact",
        ),
        "manage_mandate_live": _proof_artifact_input(
            args.manage_mandate_live_proof,
            artifact_name="Manage mandate live proof",
            ref_name="Manage mandate live proof artifact",
        ),
        "mandate_restriction_live": _proof_artifact_input(
            args.mandate_restriction_live_proof,
            artifact_name="Mandate/restriction live proof",
            ref_name="Mandate/restriction live proof artifact",
        ),
        "mandate_restriction_source_product": _proof_artifact_input(
            args.mandate_restriction_source_product_proof,
            artifact_name="Mandate/restriction source-product proof",
            ref_name="Mandate/restriction source-product proof artifact",
        ),
        "missing_suitability_live": _proof_artifact_input(
            args.missing_suitability_live_proof,
            artifact_name="Missing suitability live proof",
            ref_name="Missing suitability live proof artifact",
        ),
        "missing_risk_profile_live": _proof_artifact_input(
            args.missing_risk_profile_live_proof,
            artifact_name="Missing risk-profile live proof",
            ref_name="Missing risk-profile live proof artifact",
        ),
        "missing_risk_profile_source_product": _proof_artifact_input(
            args.missing_risk_profile_source_product_proof,
            artifact_name="Missing risk-profile source-product proof",
            ref_name="Missing risk-profile source-product proof artifact",
        ),
        "missing_benchmark_live": _proof_artifact_input(
            args.missing_benchmark_live_proof,
            artifact_name="Missing benchmark live proof",
            ref_name="Missing benchmark live proof artifact",
        ),
        "missing_benchmark_performance_readiness": _proof_artifact_input(
            args.missing_benchmark_performance_readiness_proof,
            artifact_name="Missing benchmark Performance readiness proof",
            ref_name="Missing benchmark Performance readiness proof artifact",
        ),
    }


def _proof_artifact_inputs(args: argparse.Namespace) -> dict[str, ProofArtifactInput]:
    return {
        "durable_repository": _proof_artifact_input(
            args.durable_repository_proof,
            artifact_name="durable repository proof",
            ref_name="durable repository proof artifact",
        ),
        "runtime_trust_telemetry": _proof_artifact_input(
            args.runtime_trust_telemetry_proof,
            artifact_name="runtime trust telemetry proof",
            ref_name="runtime trust telemetry proof artifact",
        ),
        "ai_lineage_store": _proof_artifact_input(
            args.ai_lineage_store_proof,
            artifact_name="AI lineage store proof",
            ref_name="AI lineage store proof artifact",
        ),
        "ai_model_risk_operations": _proof_artifact_input(
            args.ai_model_risk_operations_proof,
            artifact_name="AI model-risk operations proof",
            ref_name="AI model-risk operations proof artifact",
        ),
        "operator_workflows_operations": _proof_artifact_input(
            args.operator_workflows_operations_proof,
            artifact_name="operator workflows operations proof",
            ref_name="operator workflows operations proof artifact",
        ),
        "ai_workflow_pack_registration": _proof_artifact_input(
            args.ai_workflow_pack_registration_proof,
            artifact_name="AI workflow-pack registration source-contract proof",
            ref_name="AI workflow-pack registration source-contract proof artifact",
        ),
        "ai_workflow_pack_runtime_execution": _proof_artifact_input(
            args.ai_workflow_pack_runtime_execution_proof,
            artifact_name="AI workflow-pack runtime execution proof",
            ref_name="AI workflow-pack runtime execution proof artifact",
        ),
        "advise_proposal_route": _proof_artifact_input(
            args.advise_proposal_route_proof,
            artifact_name="Advise proposal route proof",
            ref_name="Advise proposal route proof artifact",
        ),
        "manage_action_route": _proof_artifact_input(
            args.manage_action_route_proof,
            artifact_name="Manage action route proof",
            ref_name="Manage action route proof artifact",
        ),
        "report_intake_route_source_contract": _proof_artifact_input(
            args.report_intake_route_source_contract_proof,
            artifact_name="Report intake-route source-contract proof",
            ref_name="Report intake-route source-contract proof artifact",
        ),
        "report_materialization_source_contract": _proof_artifact_input(
            args.report_materialization_source_contract_proof,
            artifact_name="report materialization source contract",
            ref_name="report materialization source contract artifact",
        ),
        "mesh_policy": _proof_artifact_input(
            args.mesh_policy_proof,
            artifact_name="mesh policy proof",
            ref_name="mesh policy proof artifact",
        ),
        "workbench_read_path_source_contract": _proof_artifact_input(
            args.workbench_read_path_source_contract_proof,
            artifact_name="Workbench read-path source-contract proof",
            ref_name="Workbench read-path source-contract proof artifact",
        ),
        "gateway_workbench_contract": _proof_artifact_input(
            args.gateway_workbench_contract_proof,
            artifact_name="Gateway/Workbench contract proof",
            ref_name="Gateway/Workbench contract proof artifact",
        ),
        "gateway_workbench_discovery_contract": _proof_artifact_input(
            args.gateway_workbench_discovery_contract_proof,
            artifact_name="Gateway/Workbench discovery contract proof",
            ref_name="Gateway/Workbench discovery contract proof artifact",
        ),
        "outbox_broker_source_contract": _proof_artifact_input(
            args.outbox_broker_source_contract_proof,
            artifact_name="outbox broker source-contract proof",
            ref_name="outbox broker source-contract proof artifact",
        ),
        "outbox_consumer_contract": _proof_artifact_input(
            args.outbox_consumer_contract_proof,
            artifact_name="outbox consumer contract proof",
            ref_name="outbox consumer contract proof artifact",
        ),
        "outbox_platform_mesh_event_source_contract": _proof_artifact_input(
            args.outbox_platform_mesh_event_source_contract_proof,
            artifact_name="outbox platform-mesh event source-contract proof",
            ref_name="outbox platform-mesh event source-contract proof artifact",
        ),
        "platform_mesh_onboarding": _proof_artifact_input(
            args.platform_mesh_onboarding_proof,
            artifact_name="platform mesh onboarding proof",
            ref_name="platform mesh onboarding proof artifact",
        ),
        **_opportunity_archetype_proof_artifact_inputs(args),
    }


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
    for flag, env_name, description in PROOF_ARTIFACT_ARGS:
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
