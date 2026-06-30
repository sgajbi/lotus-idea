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

## Problem Details

Use `app.api.problem_details` for shared product-safe RFC-7807 response
metadata and common permission/request failures. Route modules should keep
route-specific error codes and descriptions, but the OpenAPI response shape
must remain consistent: `type`, `status`, `code`, `title`, and product-safe
`detail`. `make openapi-problem-details-example-gate` blocks public
ProblemDetails response metadata that lacks an OpenAPI example.

Signal routes use `app.api.signal_api_support` because their permission,
source-authority, operation-event, and 400/403 OpenAPI metadata are governed as
one caller-supplied signal contract. Workflow and operator routes should use
`app.api.problem_details` directly unless a more specific route-family support
module exists.
