# API Layer

Keep routes thin. Route modules should validate HTTP input, call application services, and map
application results into response DTOs. Do not put business rules or downstream clients here.

## Runtime Dependencies

Use `app.api.runtime_dependencies` as the only API-layer facade for runtime composition helpers.
Route modules must not import `app.runtime` directly. This keeps repository providers, source
workers, outbox publishers, proof-artifact paths, and downstream realization clients behind one
reviewable API dependency boundary while preserving in-process design modularity.

## Route Metadata

Use `app.api.route_metadata.RouteMetadata` for route-registration metadata dictionaries. Route
modules should not define local `RouteMetadata` or `SignalRouteMetadata` clones; `make
api-route-metadata-gate` blocks duplicate metadata types so OpenAPI route declarations stay on one
reviewable API contract.

## Idempotency

Use `app.api.idempotency.validate_idempotency_key` when mutating workflow
routes require `Idempotency-Key`. Route modules should not define local
idempotency validator clones; `make api-idempotency-boundary-gate` blocks
duplicates so blank-key request handling stays consistent across lifecycle,
review, feedback, conversion, report-evidence, and downstream realization
routes.

## DTO Base Models

Use `app.api.base_model.CamelModel` for API request and response DTOs that need
camel-case aliases. Route modules should not define local `CamelModel` or local
`ConfigDict(populate_by_name=True)` clones; `make
api-camel-model-boundary-gate` blocks duplicates so alias handling remains
consistent without creating a runtime service split.

## Signal DTOs

Use `app.api.signal_models` for signal-family DTOs that are shared across
multiple route modules, such as source refs, review access scope, and candidate
summary responses. Route modules should not import those DTOs from
`app.api.idea_signals`; `make api-signal-model-boundary-gate` blocks that
route-to-route coupling so caller-supplied signal APIs keep one reviewable model
boundary without creating a separately deployable signal service.

## Caller Context

Use `app.api.caller_headers.CallerContextHeaders` when caller-supplied signal
routes need standard `X-Caller-Subject`, `X-Caller-Roles`, and
`X-Caller-Capabilities` binding. Signal route modules should not bind those
headers locally; `make signal-api-contract-gate` blocks route-local caller
header clones so permission behavior stays behind the shared caller-context
facade without creating a separately deployable signal service.

## Temporal Validation

Use `app.api.temporal_validation` for API timestamp awareness and UTC checks.
Route modules should not inspect `tzinfo` or call `utcoffset()` directly; `make
api-temporal-validation-boundary-gate` blocks route-local clones so request DTOs
and query parameters keep consistent timestamp semantics without moving domain
time invariants into the API layer.

## Problem Details

Use `app.api.problem_details` for shared product-safe RFC-7807 response
metadata and runtime response helpers. Route modules and `app.main` exception
handlers should keep route- or handler-specific error codes and descriptions,
but the OpenAPI and runtime response shape must remain consistent: `type`,
`status`, `code`, `title`, and product-safe `detail`. `make
api-problem-details-boundary-gate` blocks direct API route or app-entrypoint
imports from `app.errors`, and `make openapi-problem-details-example-gate`
blocks public ProblemDetails response metadata that lacks an OpenAPI example.

Signal routes use `app.api.signal_api_support` because their permission,
source-authority, operation-event, and 400/403 OpenAPI metadata are governed as
one caller-supplied signal contract. Workflow and operator routes should use
`app.api.problem_details` directly unless a more specific route-family support
module exists.
