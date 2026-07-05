from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CALLER_CONTEXT_SECURITY_SCHEME = "LotusCallerContext"
TRUSTED_CALLER_CONTEXT_SECURITY_SCHEME = "LotusTrustedCallerContext"
CALLER_CONTEXT_EXTENSION = "x-lotus-caller-context"


@dataclass(frozen=True)
class CallerContextOpenApiRequirement:
    method: str
    path: str
    required_capabilities: tuple[str, ...]
    required_roles: tuple[str, ...] = ()
    alternative_roles: tuple[str, ...] = ()
    entitlement_scope: str = (
        "Caller entitlement-scope headers are optional unless the operation or request "
        "targets tenant, book, portfolio, or client scope; scoped requests fail closed "
        "when they exceed caller entitlements."
    )


_SIGNAL_REQUIREMENT_PATHS = (
    "/api/v1/idea-signals/high-cash/evaluate",
    "/api/v1/idea-signals/high-cash/evaluate-from-source",
    "/api/v1/idea-signals/allocation-drift/evaluate",
    "/api/v1/idea-signals/low-income/evaluate",
    "/api/v1/idea-signals/low-income/evaluate-from-source",
    "/api/v1/idea-signals/underperformance/evaluate",
    "/api/v1/idea-signals/underperformance/evaluate-from-source",
    "/api/v1/idea-signals/bond-maturity/evaluate",
    "/api/v1/idea-signals/bond-maturity/evaluate-from-source",
    "/api/v1/idea-signals/concentration-risk/evaluate",
    "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
    "/api/v1/idea-signals/drawdown-review/evaluate",
    "/api/v1/idea-signals/drawdown-review/evaluate-from-source",
    "/api/v1/idea-signals/high-volatility/evaluate",
    "/api/v1/idea-signals/high-volatility/evaluate-from-source",
    "/api/v1/idea-signals/mandate-restriction/evaluate",
    "/api/v1/idea-signals/missing-risk-profile/evaluate",
    "/api/v1/idea-signals/missing-benchmark/evaluate",
    "/api/v1/idea-signals/missing-benchmark/evaluate-from-source",
    "/api/v1/idea-signals/missing-suitability/evaluate",
)


def _signal_requirement(path: str) -> CallerContextOpenApiRequirement:
    return CallerContextOpenApiRequirement(
        method="POST",
        path=path,
        required_capabilities=("idea.signal.evaluate",),
        required_roles=("advisor",),
    )


def _operator_requirement(
    method: str, path: str, capability: str
) -> CallerContextOpenApiRequirement:
    return CallerContextOpenApiRequirement(
        method=method,
        path=path,
        required_capabilities=(capability,),
        required_roles=("operator",),
    )


PROTECTED_OPERATION_REQUIREMENTS = (
    *(_signal_requirement(path) for path in _SIGNAL_REQUIREMENT_PATHS),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-signals/high-cash/evaluate-and-persist",
        required_capabilities=("idea.candidate.persist",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-candidates/{candidateId}/lifecycle-transitions",
        required_capabilities=("idea.candidate.lifecycle.transition",),
    ),
    CallerContextOpenApiRequirement(
        method="GET",
        path="/api/v1/idea-candidates/{candidateId}",
        required_capabilities=("idea.candidate.detail.read",),
        required_roles=("advisor", "operator"),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-candidates/{candidateId}/evidence-replay",
        required_capabilities=("idea.candidate.evidence.replay",),
        required_roles=("operator",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
        required_capabilities=("idea.ai-explanation.evaluate",),
        required_roles=("advisor",),
    ),
    _operator_requirement(
        "GET", "/api/v1/ai-explanations/readiness", "idea.ai-explanation.readiness.read"
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-candidates/{candidateId}/review-actions",
        required_capabilities=("idea.review.record",),
        required_roles=("advisor",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-candidates/{candidateId}/feedback",
        required_capabilities=("idea.feedback.record",),
        required_roles=("advisor",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/idea-candidates/{candidateId}/conversion-intents",
        required_capabilities=("idea.conversion.intent.record",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
        required_capabilities=("idea.downstream-realization.submit",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/conversion-intents/{conversionIntentId}/outcomes",
        required_capabilities=("idea.conversion.outcome.record",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        required_capabilities=("idea.report-evidence-pack.request",),
    ),
    CallerContextOpenApiRequirement(
        method="POST",
        path="/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
        required_capabilities=("idea.downstream-realization.submit",),
    ),
    CallerContextOpenApiRequirement(
        method="GET",
        path="/api/v1/review-queues/advisor",
        required_capabilities=("idea.review.queue.read",),
        required_roles=("advisor",),
    ),
    _operator_requirement(
        "GET", "/api/v1/review-queues/advisor/readiness", "idea.review.queue.readiness.read"
    ),
    _operator_requirement(
        "GET", "/api/v1/source-ingestion/readiness", "idea.source-ingestion.readiness.read"
    ),
    _operator_requirement("POST", "/api/v1/source-ingestion/run-once", "idea.source-ingestion.run"),
    _operator_requirement(
        "GET", "/api/v1/outbox-delivery/readiness", "idea.outbox-delivery.readiness.read"
    ),
    _operator_requirement("POST", "/api/v1/outbox-delivery/run-once", "idea.outbox-delivery.run"),
    _operator_requirement("GET", "/api/v1/data-mesh/readiness", "idea.mesh.readiness.read"),
    _operator_requirement(
        "GET",
        "/api/v1/data-mesh/trust-telemetry/runtime-preview",
        "idea.mesh.trust-telemetry.preview.read",
    ),
    _operator_requirement(
        "GET",
        "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
        "idea.mesh.trust-telemetry.snapshot.read",
    ),
    _operator_requirement(
        "GET",
        "/api/v1/downstream-realization/readiness",
        "idea.downstream-realization.readiness.read",
    ),
    _operator_requirement(
        "GET",
        "/api/v1/implementation-proof/readiness",
        "idea.implementation-proof.readiness.read",
    ),
)


_REQUIREMENTS_BY_OPERATION = {
    (requirement.method, requirement.path): requirement
    for requirement in PROTECTED_OPERATION_REQUIREMENTS
}

_HEADER_DESCRIPTIONS = {
    "X-Caller-Subject": "Governed caller subject propagated by trusted Lotus ingress.",
    "X-Caller-Roles": (
        "Comma-separated Lotus caller roles used for route authorization where a role is "
        "required or accepted by policy."
    ),
    "X-Caller-Capabilities": (
        "Comma-separated Lotus operation capabilities. Protected operations document the "
        "required idea.* capability in x-lotus-caller-context."
    ),
    "X-Caller-Tenant-Ids": "Comma-separated tenant entitlement scope for scoped operations.",
    "X-Caller-Book-Ids": "Comma-separated book entitlement scope for scoped operations.",
    "X-Caller-Portfolio-Ids": (
        "Comma-separated portfolio entitlement scope for scoped operations."
    ),
    "X-Caller-Client-Ids": "Comma-separated client entitlement scope for scoped operations.",
    "X-Lotus-Trusted-Caller-Context": (
        "Production-like profiles require this trusted-ingress provenance marker when "
        "privileged X-Caller-* headers are present; the value must match the configured "
        "LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN."
    ),
}


def apply_caller_context_openapi_contract(schema: dict[str, Any]) -> dict[str, Any]:
    components = schema.setdefault("components", {})
    if isinstance(components, dict):
        security_schemes = components.setdefault("securitySchemes", {})
        if isinstance(security_schemes, dict):
            security_schemes.setdefault(
                CALLER_CONTEXT_SECURITY_SCHEME,
                {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Caller-Capabilities",
                    "description": (
                        "Lotus caller-context capabilities propagated by trusted ingress. "
                        "Each protected operation publishes its required capability in "
                        "x-lotus-caller-context."
                    ),
                },
            )
            security_schemes.setdefault(
                TRUSTED_CALLER_CONTEXT_SECURITY_SCHEME,
                {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Lotus-Trusted-Caller-Context",
                    "description": (
                        "Trusted-ingress provenance marker required in demo, staging, and "
                        "production profiles when privileged X-Caller-* headers are present."
                    ),
                },
            )

    paths = schema.get("paths")
    if not isinstance(paths, dict):
        return schema

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            requirement = _REQUIREMENTS_BY_OPERATION.get((method.upper(), path))
            if requirement is None:
                continue
            _apply_operation_requirement(operation, requirement)

    return schema


def _apply_operation_requirement(
    operation: dict[str, Any], requirement: CallerContextOpenApiRequirement
) -> None:
    operation["security"] = [{CALLER_CONTEXT_SECURITY_SCHEME: []}]
    extension: dict[str, Any] = {
        "requiredCapabilities": list(requirement.required_capabilities),
        "trustedCallerContextProvenance": (
            "In demo, staging, and production profiles, privileged X-Caller-* headers "
            "are accepted only with X-Lotus-Trusted-Caller-Context matching "
            "LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN."
        ),
        "entitlementScope": requirement.entitlement_scope,
        "permissionDenied": "Authorization failures return product-safe 403 ProblemDetails.",
    }
    if requirement.required_roles:
        extension["requiredRoles"] = list(requirement.required_roles)
    if requirement.alternative_roles:
        extension["alternativeRoles"] = list(requirement.alternative_roles)
    operation[CALLER_CONTEXT_EXTENSION] = extension
    _describe_caller_context_headers(operation)


def _describe_caller_context_headers(operation: dict[str, Any]) -> None:
    parameters = operation.get("parameters")
    if not isinstance(parameters, list):
        return
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        if parameter.get("in") != "header":
            continue
        name = parameter.get("name")
        if isinstance(name, str) and name in _HEADER_DESCRIPTIONS:
            parameter["description"] = _HEADER_DESCRIPTIONS[name]
