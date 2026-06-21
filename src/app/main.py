from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.idea_signals import register_idea_signal_routes
from app.errors import problem_response
from app.middleware.correlation import CorrelationIdMiddleware
from app.observability import configure_logging, log_event

SERVICE_NAME = "lotus-idea"
SERVICE_VERSION = "0.1.0"
ROUNDING_POLICY_VERSION = "v1"

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)
app.add_middleware(CorrelationIdMiddleware, service_name=SERVICE_NAME)
register_idea_signal_routes(app)
Instrumentator().instrument(app).expose(app, include_in_schema=False)
configure_logging()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    log_event(
        "request.validation_failed",
        service=SERVICE_NAME,
        path=str(request.url.path),
        method=request.method,
        error_category="validation",
    )
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="Request validation failed. Correct the request fields and retry.",
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    log_event(
        "request.http_error",
        service=SERVICE_NAME,
        path=str(request.url.path),
        method=request.method,
        status_code=exc.status_code,
    )
    return problem_response(
        status_code=exc.status_code,
        code="request_rejected",
        title="Request rejected",
        detail="The service rejected the request. Correct the request or contact support with the correlation id.",
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    log_event(
        "request.unhandled_error",
        service=SERVICE_NAME,
        level="ERROR",
        path=str(request.url.path),
        method=request.method,
        error_category=exc.__class__.__name__,
    )
    return problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        title="Internal service error",
        detail="The service could not complete the request. Retry later or contact support with the correlation id.",
    )


@app.get(
    "/health",
    tags=["Health"],
    summary="Get service health",
    description="Returns a lightweight service health response for diagnostics and platform smoke checks.",
    responses={
        200: {
            "description": "Service health response.",
            "content": {"application/json": {"example": {"status": "ok", "service": SERVICE_NAME}}},
        }
    },
)
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get(
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
)
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@app.get(
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
)
async def health_ready(response: Response) -> dict[str, str]:
    if bool(getattr(app.state, "is_draining", False)):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "draining"}
    return {"status": "ready"}


@app.get(
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
)
async def metadata() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "roundingPolicyVersion": ROUNDING_POLICY_VERSION,
    }
