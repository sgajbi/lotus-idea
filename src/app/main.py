import os

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.ai_governance import register_ai_governance_routes
from app.api.allocation_drift_signals import register_allocation_drift_signal_routes
from app.api.bond_maturity_signals import register_bond_maturity_signal_routes
from app.api.candidate_detail import register_candidate_detail_routes
from app.api.candidate_evidence_replay import register_candidate_evidence_replay_routes
from app.api.candidate_lifecycle import register_candidate_lifecycle_routes
from app.api.concentration_risk_signals import register_concentration_risk_signal_routes
from app.api.conversion_governance import register_conversion_governance_routes
from app.api.data_mesh_readiness import register_data_mesh_readiness_routes
from app.api.data_lifecycle import register_data_lifecycle_routes
from app.api.drawdown_review_signals import register_drawdown_review_signal_routes
from app.api.downstream_realization import register_downstream_realization_routes
from app.api.downstream_submission_reconciliation import (
    register_downstream_submission_reconciliation_routes,
)
from app.api.downstream_realization_readiness import (
    register_downstream_realization_readiness_routes,
)
from app.api.high_volatility_signals import register_high_volatility_signal_routes
from app.api.idea_signals import register_idea_signal_routes
from app.api.implementation_proof_readiness import register_implementation_proof_readiness_routes
from app.api.low_income_signals import register_low_income_signal_routes
from app.api.missing_benchmark_signals import register_missing_benchmark_signal_routes
from app.api.missing_risk_profile_signals import register_missing_risk_profile_signal_routes
from app.api.missing_suitability_signals import register_missing_suitability_signal_routes
from app.api.outbox.delivery import register_outbox_delivery_readiness_routes
from app.api.outbox.recovery import register_outbox_recovery_routes
from app.api.report_evidence import register_report_evidence_routes
from app.api.review_queues import register_review_queue_routes
from app.api.review_workflow import register_review_workflow_routes
from app.api.runtime_trust_telemetry import register_runtime_trust_telemetry_routes
from app.api.source_ingestion_readiness import register_source_ingestion_readiness_routes
from app.api.underperformance_signals import register_underperformance_signal_routes
from app.api.caller_context_openapi import apply_caller_context_openapi_contract
from app.api.durable_write_guard import durable_write_readiness_payload
from app.api.idempotency import mark_required_idempotency_openapi_headers
from app.api.problem_details import (
    ProblemDetailsHTTPException,
    problem_details_response as problem_response,
)
from app.api.runtime_dependencies import (
    close_lifecycle_authority_dependencies,
    close_lotus_ai_attestation_dependencies,
    get_idea_repository,
    idea_repository_durable_storage_backed,
    idea_repository_runtime_posture,
)
from app.application.outbox.readiness import (
    OutboxDeliveryReadinessSnapshot,
    build_outbox_delivery_readiness_snapshot,
)
from app.application.capacity_posture import read_postgres_capacity_posture
from app.domain.capacity_posture import PostgresCapacityPosture
from app.domain.recovery_posture import ServiceRecoveryPosture, evaluate_recovery_readiness
from app.runtime.downstream_realization_state import close_downstream_realization_clients
from app.runtime.recovery_posture import load_recovery_runtime_state
from app.runtime.release_identity import (
    release_identity_configuration_blockers,
    release_identity_metadata,
)
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.http_boundary import configure_http_boundary
from app.observability import (
    configure_logging,
    configure_outbox_supportability_metrics,
    configure_postgres_capacity_metrics,
    emit_request_diagnostic_event,
)

SERVICE_NAME = "lotus-idea"
SERVICE_VERSION = os.getenv("LOTUS_SERVICE_VERSION", "0.1.0")
ROUNDING_POLICY_VERSION = "v1"
BUILD_METADATA = release_identity_metadata(os.environ)


def create_app() -> FastAPI:
    application = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)
    configure_http_boundary(application)
    application.add_middleware(CorrelationIdMiddleware, service_name=SERVICE_NAME)
    _register_exception_handlers(application)
    _register_product_routes(application)
    _register_platform_routes(application)
    Instrumentator().instrument(application).expose(application, include_in_schema=False)
    configure_outbox_supportability_metrics(_runtime_outbox_delivery_readiness)
    configure_postgres_capacity_metrics(_runtime_postgres_capacity_posture)
    _configure_openapi_contract_overrides(application)
    application.router.add_event_handler("shutdown", close_downstream_realization_clients)
    application.router.add_event_handler("shutdown", close_lotus_ai_attestation_dependencies)
    application.router.add_event_handler("shutdown", close_lifecycle_authority_dependencies)
    configure_logging()
    return application


def _runtime_outbox_delivery_readiness() -> OutboxDeliveryReadinessSnapshot:
    return build_outbox_delivery_readiness_snapshot(
        repository=get_idea_repository(),
        durable_storage_backed=idea_repository_durable_storage_backed(),
    )


def _runtime_postgres_capacity_posture() -> PostgresCapacityPosture:
    return read_postgres_capacity_posture(get_idea_repository())


def _register_product_routes(application: FastAPI) -> None:
    register_idea_signal_routes(application)
    register_allocation_drift_signal_routes(application)
    register_bond_maturity_signal_routes(application)
    register_concentration_risk_signal_routes(application)
    register_drawdown_review_signal_routes(application)
    register_high_volatility_signal_routes(application)
    register_low_income_signal_routes(application)
    register_missing_benchmark_signal_routes(application)
    register_missing_risk_profile_signal_routes(application)
    register_missing_suitability_signal_routes(application)
    register_underperformance_signal_routes(application)
    register_candidate_lifecycle_routes(application)
    register_candidate_detail_routes(application)
    register_candidate_evidence_replay_routes(application)
    register_ai_governance_routes(application)
    register_review_queue_routes(application)
    register_review_workflow_routes(application)
    register_conversion_governance_routes(application)
    register_report_evidence_routes(application)
    register_downstream_realization_routes(application)
    register_downstream_submission_reconciliation_routes(application)
    register_downstream_realization_readiness_routes(application)
    register_data_mesh_readiness_routes(application)
    register_data_lifecycle_routes(application)
    register_runtime_trust_telemetry_routes(application)
    register_source_ingestion_readiness_routes(application)
    register_outbox_delivery_readiness_routes(application)
    register_outbox_recovery_routes(application)
    register_implementation_proof_readiness_routes(application)


def _register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(RequestValidationError, validation_exception_handler_adapter)
    application.add_exception_handler(HTTPException, http_exception_handler_adapter)
    application.add_exception_handler(Exception, unhandled_exception_handler)


def _register_platform_routes(application: FastAPI) -> None:
    application.get(
        "/health",
        tags=["Health"],
        summary="Get service health",
        description="Returns a lightweight service health response for diagnostics and platform smoke checks.",
        responses={
            200: {
                "description": "Service health response.",
                "content": {
                    "application/json": {"example": {"status": "ok", "service": SERVICE_NAME}}
                },
            }
        },
    )(health)
    application.get(
        "/health/live",
        tags=["Health"],
        summary="Get liveness",
        description="Returns liveness status when the process is running.",
        responses={
            200: {
                "description": "Process is live.",
                "content": {"application/json": {"example": {"status": "live"}}},
            }
        },
    )(health_live)
    application.get(
        "/health/ready",
        tags=["Health"],
        summary="Get readiness",
        description=(
            "Returns readiness status, draining state, and durable write repository posture."
        ),
        responses={
            200: {
                "description": "Service is ready to receive traffic.",
                "content": {
                    "application/json": {
                        "example": {
                            "status": "ready",
                            "recoveryPosture": "normal",
                            "runtimeProfile": "local",
                            "durableRepositoryConfigured": False,
                            "durableStorageBacked": False,
                            "processLocalRepositoryAllowed": True,
                            "durableWriteRepositoryRequired": False,
                            "configurationBlockers": [],
                        }
                    }
                },
            },
            503: {
                "description": (
                    "Service is intentionally draining or missing required durable write "
                    "configuration."
                ),
                "content": {
                    "application/json": {
                        "example": {
                            "status": "degraded",
                            "runtimeProfile": "production",
                            "durableRepositoryConfigured": False,
                            "durableStorageBacked": False,
                            "processLocalRepositoryAllowed": False,
                            "durableWriteRepositoryRequired": True,
                            "configurationBlockers": ["durable_repository_not_configured"],
                        }
                    }
                },
            },
        },
    )(health_ready)
    application.get(
        "/metadata",
        tags=["Metadata"],
        summary="Get service metadata",
        description="Returns service identity and policy-version metadata for operators and validators.",
        responses={
            200: {
                "description": "Service metadata response.",
                "content": {
                    "application/json": {
                        "example": {
                            "service": SERVICE_NAME,
                            "version": SERVICE_VERSION,
                            "roundingPolicyVersion": ROUNDING_POLICY_VERSION,
                            "build": BUILD_METADATA,
                        }
                    }
                },
            }
        },
    )(metadata)
    application.get(
        "/version",
        tags=["Metadata"],
        summary="Get service version metadata",
        description=(
            "Returns service identity and build provenance metadata for operators, "
            "validators, and image provenance checks."
        ),
        responses={
            200: {
                "description": "Service version metadata response.",
                "content": {
                    "application/json": {
                        "example": {
                            "service": SERVICE_NAME,
                            "version": SERVICE_VERSION,
                            "roundingPolicyVersion": ROUNDING_POLICY_VERSION,
                            "build": BUILD_METADATA,
                        }
                    }
                },
            }
        },
    )(metadata)


def _configure_openapi_contract_overrides(application: FastAPI) -> None:
    def governed_openapi() -> dict[str, object]:
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            routes=application.routes,
        )
        schema = mark_required_idempotency_openapi_headers(schema)
        application.openapi_schema = apply_caller_context_openapi_contract(schema)
        return application.openapi_schema

    application.openapi = governed_openapi  # type: ignore[method-assign]


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path.startswith("/") else "/unknown"


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    emit_request_diagnostic_event(
        "request.validation_failed",
        route=_route_template(request),
        method=request.method,
        error_category="validation",
        correlation_id=_request_correlation_id(request),
        trace_id=_request_trace_id(request),
    )
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="Request validation failed. Correct the request fields and retry.",
    )


async def validation_exception_handler_adapter(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_exception_handler(request, exc)
    return await validation_exception_handler(request, exc)


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    error_category = (
        exc.error_category
        if isinstance(exc, ProblemDetailsHTTPException)
        else "generic_http_exception"
    )
    emit_request_diagnostic_event(
        "request.http_error",
        route=_route_template(request),
        method=request.method,
        status_code=exc.status_code,
        error_category=error_category,
        correlation_id=_request_correlation_id(request),
        trace_id=_request_trace_id(request),
    )
    if isinstance(exc, ProblemDetailsHTTPException):
        return problem_response(
            status_code=exc.status_code,
            code=exc.code,
            title=exc.title,
            detail=str(exc.detail),
        )
    return problem_response(
        status_code=exc.status_code,
        code="request_rejected",
        title="Request rejected",
        detail="The service rejected the request. Correct the request or contact support with the correlation id.",
    )


async def http_exception_handler_adapter(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, HTTPException):
        return await unhandled_exception_handler(request, exc)
    return await http_exception_handler(request, exc)


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    emit_request_diagnostic_event(
        "request.unhandled_error",
        level="ERROR",
        route=_route_template(request),
        method=request.method,
        error_category=exc.__class__.__name__,
        correlation_id=_request_correlation_id(request),
        trace_id=_request_trace_id(request),
    )
    return problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        title="Internal service error",
        detail="The service could not complete the request. Retry later or contact support with the correlation id.",
    )


async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


async def health_live() -> dict[str, str]:
    return {"status": "live"}


async def health_ready(request: Request, response: Response) -> dict[str, object]:
    recovery_decision = load_recovery_runtime_state().decision
    if bool(getattr(request.app.state, "is_draining", False)):
        recovery_decision = evaluate_recovery_readiness(ServiceRecoveryPosture.DRAINING)
    posture = idea_repository_runtime_posture()
    payload = durable_write_readiness_payload(posture)
    payload["recoveryPosture"] = recovery_decision.posture.value
    identity_blockers = release_identity_configuration_blockers(os.environ)
    if identity_blockers:
        configured_blockers = payload.get("configurationBlockers")
        blockers = list(configured_blockers) if isinstance(configured_blockers, list) else []
        blockers.extend(blocker for blocker in identity_blockers if blocker not in blockers)
        payload["configurationBlockers"] = blockers
        payload["status"] = "degraded"
    if not recovery_decision.write_ready:
        payload["status"] = recovery_decision.readiness_status
        configured_blockers = payload.get("configurationBlockers")
        blockers = (
            list(configured_blockers)
            if isinstance(configured_blockers, list)
            and all(isinstance(blocker, str) for blocker in configured_blockers)
            else []
        )
        if recovery_decision.blocker not in blockers:
            blockers.append(recovery_decision.blocker)
        payload["configurationBlockers"] = blockers
    if not posture.write_ready or not recovery_decision.write_ready or identity_blockers:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload


async def metadata() -> dict[str, object]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "roundingPolicyVersion": ROUNDING_POLICY_VERSION,
        "build": release_identity_metadata(os.environ),
    }


app = create_app()
