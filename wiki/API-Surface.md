# API Surface

This page is the first-stop map for `lotus-idea` API readers. It summarizes
the implemented route families and routes deeper review to the certified
endpoint ledger, OpenAPI gate, and operation runbooks. It is not a supported
business-feature catalogue.

Current API posture: internal foundation and operator diagnostics only. Bounded
read-only Gateway publication exists for advisor queue and candidate detail,
but full Workbench proof, data-product certification, client-ready publication,
and supported-feature promotion remain blocked until their own evidence gates
pass.

## Route Families

| Family | Routes | Current use | Boundary |
| --- | --- | --- | --- |
| Health and metadata | `GET /health`, `GET /health/live`, `GET /health/ready`, `GET /metadata` | Platform smoke checks, readiness probes, service inventory. | No business capability, source quality, or portfolio supportability proof. |
| Caller-supplied opportunity signals | `POST /api/v1/idea-signals/*/evaluate` | Deterministic candidate posture over source-owned evidence supplied by authorized callers. | No upstream source fetch, official calculation ownership, Gateway/Workbench support, or supported-feature promotion. |
| Candidate persistence and lifecycle | `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`, `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions`, `GET /api/v1/idea-candidates/{candidateId}`, `POST /api/v1/idea-candidates/{candidateId}/evidence-replay` | Internal persisted candidate, idempotency, lifecycle, detail, and evidence-replay foundations. Durable PostgreSQL providers use repository-side candidate-detail projection instead of whole-store snapshot hydration for ordinary detail reads. | `local`/`test` may use process-local writes; production-like profiles require PostgreSQL and fail closed when absent. No downstream authority or client-ready publication. |
| Review workflow | `GET /api/v1/review-queues/advisor`, `GET /api/v1/review-queues/advisor/readiness`, `POST /api/v1/idea-candidates/{candidateId}/review-actions`, `POST /api/v1/idea-candidates/{candidateId}/feedback` | Source-safe advisor queue projection, readiness diagnostics, review decisions, and feedback capture. Advisor queue reads use bounded `limit`/`offset` paging with default 25 and max 100; durable PostgreSQL providers use repository-side candidate projection instead of whole-store snapshot hydration. Review and feedback workflow prechecks reuse bounded candidate lookup when available. | Advisor queue/detail have bounded read-only Gateway publication; Workbench proof, data-product certification, and supported review-product promotion remain blocked. |
| AI explanation governance | `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`, `GET /api/v1/ai-explanations/readiness` | Deterministic fallback/verifier evaluation and model-risk readiness diagnostics. Candidate lookup before evaluation uses the bounded candidate projection when available; lineage writes remain on the repository mutation path. | No provider call, no autonomous advice, no `lotus-ai` runtime proof, and no client-ready explanation claim. |
| Conversion and report evidence | `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`, `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`, `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs` | Internal review-gated intent, outcome posture, and report evidence-pack request recording. Conversion-intent candidate prechecks reuse bounded candidate lookup when available. | No suitability approval, rebalance/execution authority, report rendering, archive record, or client publication. |
| Downstream realization | `GET /api/v1/downstream-realization/readiness`, `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`, `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions` | Planned-contract readiness and source-safe submission posture through configured adapters, with local idempotency replay/conflict/not-configured persistence before adapter calls. Durable PostgreSQL providers use bounded conversion-intent and report evidence-pack lookups before adapter calls. | No authoritative downstream outcome, route-existence proof by default, suitability, execution, materialization, or support promotion. |
| Source ingestion and outbox operations | `GET /api/v1/source-ingestion/readiness`, `POST /api/v1/source-ingestion/run-once`, `GET /api/v1/outbox-delivery/readiness`, `POST /api/v1/outbox-delivery/run-once` | Operator diagnostics and bounded run-once actions over configured internal foundations. Outbox run-once requires `Idempotency-Key`, returns a source-safe `operatorRunReference`, replays same-key/same-request calls without mutation, and rejects same-key/different-request reuse. | No long-running scheduler certification, live broker certification, downstream delivery proof, or supported ingestion/event product. |
| Data mesh and implementation proof | `GET /api/v1/data-mesh/readiness`, `GET /api/v1/data-mesh/trust-telemetry/runtime-preview`, `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`, `GET /api/v1/implementation-proof/readiness` | Source-safe readiness, telemetry, and aggregate proof-blocker diagnostics. | Diagnostics only; no mesh certification, Gateway/Workbench discovery, live implementation proof, or supported-feature promotion. |

## Request And Error Model

| Control | Current expectation |
| --- | --- |
| Authorization | API routes fail closed through platform caller-context roles and `idea.*` capabilities. |
| Runtime composition | API routes use `app.api.runtime_dependencies` as the only facade for repository providers, source-ingestion runtime, outbox publisher wiring, proof-artifact configuration, and downstream realization clients. Direct route imports from `app.runtime` are blocked by `make architecture-boundary-gate`. |
| Route metadata | API routes use the shared `app.api.route_metadata.RouteMetadata` contract for route-registration metadata. Local route metadata clones are blocked by `make api-route-metadata-gate`. |
| Idempotency | Mutating workflow routes require `Idempotency-Key`, validate blank keys through shared `app.api.idempotency`, and return replay or conflict posture instead of duplicating state. `make api-idempotency-boundary-gate` blocks route-local validator clones. |
| DTO alias handling | API DTOs that need camel-case aliases use `app.api.base_model.CamelModel`. `make api-camel-model-boundary-gate` blocks route-local `CamelModel` or `ConfigDict(populate_by_name=True)` clones. |
| Signal DTO ownership | Shared signal-family DTOs for source refs, review access scope, source-ref responses, and candidate summaries live in `app.api.signal_models`. `make api-signal-model-boundary-gate` blocks route-to-route imports from `app.api.idea_signals`. |
| Signal caller context | Caller-supplied signal routes bind standard identity, capability, and entitlement-scope headers through `app.api.caller_headers.CallerContextHeaders`. Requests with `accessScope` must pass that scope into `signal_permission_problem_or_none(...)`; out-of-scope requests fail closed with product-safe 403 behavior before domain evaluation. `make signal-api-contract-gate` blocks route-local `X-Caller-*` header clones, scope-unaware permission checks, duplicate signal permission policy, weak 400/403 examples, and operation-event drift. |
| Temporal validation | API timestamp-awareness and UTC checks live in `app.api.temporal_validation`. `make api-temporal-validation-boundary-gate` blocks route-local `tzinfo` and `utcoffset()` checks so request DTO and query-parameter time semantics stay consistent. |
| Source authority | Signal routes consume source-owned evidence and carry source refs; `lotus-idea` does not recompute official performance, risk, accounting, suitability, or report facts. |
| Error responses | Certified business and operator endpoints must expose product-safe `ProblemDetails` examples. Workflow/operator routes and app-entrypoint exception handlers use shared `app.api.problem_details` metadata and runtime response helpers for concrete 400/403/404/409/503 ProblemDetails responses; `make api-problem-details-boundary-gate` blocks direct API route or app-entrypoint imports from `app.errors`, and `make openapi-problem-details-example-gate` blocks missing OpenAPI examples. Caller-supplied signal routes use `app.api.signal_api_support` for their stricter route-family contract. |
| Sensitive data | Responses and diagnostics must not expose raw source payloads, raw idempotency keys, portfolio identifiers in aggregate diagnostics, prompt/provider payloads, or broker payloads. |

## Evidence Paths

| Evidence | Use |
| --- | --- |
| [API certification guide](https://github.com/sgajbi/lotus-idea/blob/main/docs/operations/api-certification.md) | Human-readable endpoint inventory, intended use, boundaries, and test evidence. |
| [Endpoint certification ledger](https://github.com/sgajbi/lotus-idea/blob/main/docs/operations/endpoint-certification-ledger.json) | Machine-readable source for endpoint certification and evidence references. |
| [OpenAPI quality gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/openapi_quality_gate.py) | Contract documentation and example validation. |
| [ProblemDetails example gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/openapi_problem_details_example_gate.py) | Generated OpenAPI check that every public `ProblemDetails` response has a product-safe example. |
| [ProblemDetails boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_problem_details_boundary_gate.py) | API boundary check that route modules and the app entrypoint import ProblemDetails runtime helpers through `app.api.problem_details`, not directly from `app.errors`. |
| [Idempotency boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_idempotency_boundary_gate.py) | API boundary check that mutating workflow routes use shared `app.api.idempotency` validation instead of route-local `Idempotency-Key` validator clones. |
| [CamelModel boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_camel_model_boundary_gate.py) | API boundary check that route modules use shared `app.api.base_model.CamelModel` instead of local camel-case DTO base-model clones. |
| [Signal model boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_signal_model_boundary_gate.py) | API boundary check that shared signal-family DTOs are imported from `app.api.signal_models`, not from concrete route modules. |
| [Endpoint certification gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/endpoint_certification_gate.py) | Synchronizes OpenAPI operations with certification evidence and supported-boundary language. |
| [Operations Runbook](Operations-Runbook) | Operator diagnostics, readiness semantics, proof-artifact interpretation, and first checks. |
| [Validation and CI](Validation-and-CI) | Repo-native gates that block weak API, OpenAPI, documentation, and supported-feature claims. |

## Copy-Paste Checks

```powershell
make openapi-gate
make endpoint-certification-gate
make api-route-metadata-gate
make api-problem-details-boundary-gate
make api-idempotency-boundary-gate
make api-camel-model-boundary-gate
make api-signal-model-boundary-gate
make api-temporal-validation-boundary-gate
make openapi-problem-details-example-gate
make signal-api-contract-gate
make documentation-contract-gate
```

Use `make check` before PR when an API route, schema, OpenAPI description,
endpoint ledger row, or wiki API claim changes.

## Do Not Infer

Certified API foundation does not mean the product is externally supported.
Do not infer client publication, suitability approval, rebalance authority,
official risk/performance methodology, report rendering, archive authority,
data-mesh certification, live provider execution, or Workbench support unless
the owning repository evidence, `supported-features`, docs/wiki truth, CI, and
mainline validation all agree.
