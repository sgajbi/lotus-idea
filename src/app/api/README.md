# API Layer

Keep routes thin. Route modules should validate HTTP input, call application services, and map
application results into response DTOs. Do not put business rules or downstream clients here.

## Problem Details

Use `app.api.problem_details` for shared product-safe RFC-7807 response
metadata and common permission/request failures. Route modules should keep
route-specific error codes and descriptions, but the OpenAPI response shape
must remain consistent: `type`, `status`, `code`, `title`, and product-safe
`detail`.

Signal routes use `app.api.signal_api_support` because their permission,
source-authority, operation-event, and 400/403 OpenAPI metadata are governed as
one caller-supplied signal contract. Workflow and operator routes should use
`app.api.problem_details` directly unless a more specific route-family support
module exists.
