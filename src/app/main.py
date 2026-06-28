from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.ai_governance import register_ai_governance_routes
from app.api.candidate_detail import register_candidate_detail_routes
from app.api.candidate_evidence_replay import register_candidate_evidence_replay_routes
from app.api.candidate_lifecycle import register_candidate_lifecycle_routes
from app.api.conversion_governance import register_conversion_governance_routes
from app.api.data_mesh_readiness import register_data_mesh_readiness_routes
from app.api.downstream_realization import register_downstream_realization_routes
from app.api.downstream_realization_readiness import (
    register_downstream_realization_readiness_routes,
)
from app.api.idea_signals import register_idea_signal_routes
from app.api.implementation_proof_readiness import register_implementation_proof_readiness_routes
from app.api.missing_risk_profile_signals import register_missing_risk_profile_signal_routes
from app.api.missing_suitability_signals import register_missing_suitability_signal_routes
from app.api.outbox_delivery_readiness import register_outbox_delivery_readiness_routes
from app.api.report_evidence import register_report_evidence_routes
from app.api.review_queues import register_review_queue_routes
from app.api.review_workflow import register_review_workflow_routes
from app.api.runtime_trust_telemetry import register_runtime_trust_telemetry_routes
from app.api.source_ingestion_readiness import register_source_ingestion_readiness_routes
from app.errors import problem_response
from app.middleware.correlation import CorrelationIdMiddleware
from app.observability import configure_logging, emit_request_diagnostic_event

SERVICE_NAME = "lotus-idea"
SERVICE_VERSION = "0.1.0"
ROUNDING_POLICY_VERSION = "v1"


def create_app() -> FastAPI:
    application = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)
    application.add_middleware(CorrelationIdMiddleware, service_name=SERVICE_NAME)
    _register_exception_handlers(application)
    _register_product_routes(application)
    _register_platform_routes(application)
    Instrumentator().instrument(application).expose(application, include_in_schema=False)
    configure_logging()
    return application


def _register_product_routes(application: FastAPI) -> None:
    register_idea_signal_routes(application)
    register_missing_risk_profile_signal_routes(application)
    register_missing_suitability_signal_routes(application)
    register_candidate_lifecycle_routes(application)
    register_candidate_detail_routes(application)
    register_candidate_evidence_replay_routes(application)
    register_ai_governance_routes(application)
    register_review_queue_routes(application)
    register_review_workflow_routes(application)
    register_conversion_governance_routes(application)
    register_report_evidence_routes(application)
    register_downstream_realization_routes(application)
    register_downstream_realization_readiness_routes(application)
    register_data_mesh_readiness_routes(application)
    register_runtime_trust_telemetry_routes(application)
    register_source_ingestion_readiness_routes(application)
    register_outbox_delivery_readiness_routes(application)
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
        description="Returns readiness status and reports draining state with a 503 response.",
        responses={
            200: {
                "description": "Service is ready to receive traffic.",
                "content": {"application/json": {"example": {"status": "ready"}}},
            },
            503: {
                "description": "Service is intentionally draining and should not receive new traffic.",
                "content": {"application/json": {"example": {"status": "draining"}}},
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
                        }
                    }
                },
            }
        },
    )(metadata)


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path.startswith("/") else "/unknown"


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    emit_request_diagnostic_event(
        "request.validation_failed",
        route=_route_template(request),
        method=request.method,
        error_category="validation",
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
    emit_request_diagnostic_event(
        "request.http_error",
        route=_route_template(request),
        method=request.method,
        status_code=exc.status_code,
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


async def health_ready(request: Request, response: Response) -> dict[str, str]:
    if bool(getattr(request.app.state, "is_draining", False)):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "draining"}
    return {"status": "ready"}


async def metadata() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "roundingPolicyVersion": ROUNDING_POLICY_VERSION,
    }


app = create_app()
