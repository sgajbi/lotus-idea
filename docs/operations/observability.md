# Observability Baseline

This repository starts from the Lotus platform observability scaffold.

## Default Signals

- /health, /health/live, and /health/ready
- /metrics outside the OpenAPI schema
- correlation and trace response headers
- structured JSON application events
- product-safe error responses
- bounded idea operation events for certified internal API foundations

## Sensitive-Content Rule

Logs, metrics, traces, dashboards, and evidence artifacts must not include client names, portfolio
ids, holdings, raw entitlement failures, request bodies, response bodies, trace ids, or correlation
ids as metric labels.

## Idea Operation Events

RFC-0002 Slice 15 adds the first business-operation observability foundation.
`src/app/observability/logging.py` defines bounded operation, outcome, and supportability
vocabulary plus the `lotus_idea_operation_events_total` Prometheus counter.

Current instrumented operations:

| Operation | Current Scope | Source Authority Label | Current Supportability |
| --- | --- | --- | --- |
| `signal_evaluation` | Internal high-cash signal evaluation | `lotus-core` | `foundation_only` |
| `candidate_persistence` | Internal high-cash candidate persistence and replay | `lotus-core` | `foundation_only` |
| `lifecycle_transition` | Internal candidate lifecycle transition recording | `lotus-idea` | `foundation_only` |
| `review_queue_read` | Internal advisor review queue read projection | `lotus-idea` | `foundation_only` |
| `review_action` | Internal human review decision recording | `lotus-idea` | `foundation_only` |
| `feedback_record` | Internal advisor feedback recording | `lotus-idea` | `foundation_only` |
| `conversion_intent` | Internal review-gated conversion intent recording | `lotus-idea` | `foundation_only` |
| `conversion_outcome` | Internal downstream conversion outcome recording | `lotus-idea` | `foundation_only` |
| `report_evidence_pack` | Internal report evidence-pack request recording | `lotus-report` | `foundation_only` |

Metric labels are limited to:

1. `operation`,
2. `outcome`,
3. `supportability_status`,
4. `source_authority`,
5. `durable_storage_backed`,
6. `supported_feature_promoted`.

The operation helper rejects sensitive attributes such as client, portfolio, account, holding,
transaction, request body, response body, raw entitlement failure, trace id, or correlation id
fields. Do not add identifiers or payload fragments to operation labels.

## Operator Interpretation

1. `accepted` means the internal foundation recorded a new operation in the process-local
   repository.
2. `replayed` means the same idempotency key and payload returned an existing foundation record.
3. `conflict` means the idempotency key was reused with a different payload.
4. `not_found` means the referenced candidate, conversion intent, or related foundation record was
   not present.
5. `duplicate`, `suppressed`, and `not_eligible` describe deterministic signal or persistence
   outcomes that did not create a new candidate.
6. `permission_denied` means fail-closed capability policy blocked the caller.
7. `invalid_request` and `invalid_state` are product-safe failures; inspect API validation and
   lifecycle/review/conversion preconditions before retrying.

These signals are operational support evidence only. They do not certify a data product, durable
database state, Gateway/Workbench route, downstream Report/Render/Archive realization, or supported
business feature.
