# Supported Features

Current posture: no business feature is supported yet.

This page is the support-posture truth for business, demo, operations, and
engineering readers. A foundation can be real, tested, and useful without being
a supported feature.

## Current Support Summary

| Source of truth | Current value |
| --- | --- |
| Registry | `supported-features/supported-features.json` |
| `current_posture` | `foundation_only` |
| `features[]` | Empty |
| Planned capability records | Present under `planned_capabilities[]` only |
| Promotion gate | `make supported-features-gate` |
| Runtime reconciliation gate | `make supported-feature-promotion-contract-gate` |

## Support Vocabulary

| Term | Meaning |
| --- | --- |
| Implemented foundation | Real internal implementation with tests and evidence, but not a supported external feature. |
| Planned capability | RFC-governed target posture or roadmap item; not support. |
| Supported feature | A `features[]` entry backed by implementation, source proof, API/OpenAPI certification, docs/wiki/context truth, CI, runtime evidence, and mainline validation. |

## Detailed Foundation Inventory

Internal foundation exists for domain vocabulary, high-cash signal evaluation,
candidate persistence/replay/idempotency/audit, candidate evidence replay,
deterministic scoring with review-queue projection, source-safe candidate detail projection, advisor
review/feedback governance, AI governance redaction/verifier/fallback controls,
and certified internal AI explanation evaluator and readiness APIs, plus the first certified
internal signal API foundations for high-cash, concentration-risk,
underperformance, allocation-drift, bond-maturity, high-volatility, drawdown,
low-income, missing suitability, missing risk-profile, mandate/restriction,
and missing-benchmark review.
Internal conversion governance and certified internal
conversion intent/outcome API foundations also exist for review-gated
conversion tracking, source-authority mapping, and no-authority conversion
boundaries. Internal report evidence-pack request governance also exists for
reviewed report conversion intents, with safe source summaries, retention refs,
Report/Render/Archive authority refs, idempotency, audit, and a certified
internal API foundation. Real PostgreSQL runtime proof exists for high-cash
persistence/replay plus the first internal advisor queue, lifecycle, review,
feedback, conversion, report evidence-pack request workflow path, and internal
source-ingestion replay/conflict recovery. A manifest-backed run-once
source-ingestion worker CLI and `make source-ingestion-worker-check` also
exist; the gate validates both manifest shape and source-safe check-only output
shape. A bounded scheduled-worker entrypoint, opt-in Docker Compose worker
profile, and `make source-ingestion-scheduled-worker-check` also exist for
deploy-contract proof. `POST /api/v1/source-ingestion/run-once` adds a certified internal
operator action over the same batch foundation, but it requires durable
repository posture plus configured manifest and Core settings, returns
aggregate decision counts only, isolates route-owned runtime cleanup failures
into source-safe suppressed operation events, and remains `not_certified`.
The database foundation also includes protected exact-image deployment
migration automation with PostgreSQL advisory locking, durable release-bound
history, pending-only apply, checksum drift rejection, explicit legacy schema
adoption, bounded rollback, append-only events, and source-safe attested
evidence validation. This is implementation and operator-control evidence only.
No protected environment execution or rollout-health attestation has been
accepted, so `supported-features/supported-features.json` correctly remains
`foundation_only` with an empty `features[]` list.
Accepted internal mutations now create source-safe outbox records with
required correlation and trace lineage, optional parent-event causation,
lease-fenced delivery state, durable retry scheduling, retryable failed status,
published status, and dead-letter status through the repository port. Certified
internal outbox delivery readiness and run-once operator endpoints now report aggregate
backlog/status, due retry, retry-deferred, leased, and expired-lease posture and can execute one bounded
configured-publisher pass that claims rows before broker publication without exposing event identifiers,
aggregate identifiers, raw idempotency keys, source payloads, broker payloads,
or downstream claims; route-owned publisher cleanup failures are suppressed into
source-safe diagnostics without masking completed, replayed, conflict, or
bounded blocked responses. That is recoverability foundation only; no certified live
broker runtime, Gateway event, platform mesh event publication, downstream
delivery, or supported event publication exists. `lotus-gateway` now publishes bounded
read-only advisor queue and candidate detail routes with caller
entitlement-scope forwarding, and `lotus-workbench` now renders the bounded
read-only advisor queue/detail path through Gateway. These foundations are not
deployed scheduler daemon proof, live Core worker certification, full Workbench
live proof, or supported-feature promotion. The bounded live source-ingestion
proof artifact is implementation evidence for source-ingestion readiness only;
it is not live source-worker certification or a supported feature. The AI
explanation readiness diagnostic is an operator supportability check only; it
does not invoke `lotus-ai` or promote AI explanation support. The AI
explanation evaluator accepts only the governed
`lotus-ai:idea-explanation:v1` / `v1` /
`lotus-ai:governed-verifier:v1` workflow-pack contract and maps that public
request identity to proof identity `idea_explanation.pack@v1`; arbitrary
caller-supplied workflow-pack identities are rejected before candidate lookup
or lineage persistence. The AI
model-risk operations proof certifies repo-owned dashboard, alert-rule, and
runbook artifacts against implemented operation telemetry without certifying
Workbench, client-ready publication, or supported-feature promotion. Source-safe AI explanation lineage persistence has
PostgreSQL runtime proof for accepted, replayed, and conflicting request ids,
and the readiness diagnostic reports durable lineage backing when the active
repository is durable. That proof is repository durability evidence, not
`lotus-ai` runtime execution or AI product certification. The bounded
AI workflow-pack registration proof validates sibling `lotus-ai`
`idea_explanation.pack@v1` registration, binding, queue policy,
supportability, and tests only; it is not provider execution, model-risk
operations certification, Workbench proof, or supported-feature promotion. The
bounded AI workflow-pack runtime execution proof validates an actual
deterministic review-gated invocation, receipt identity, evidence-hash binding,
guardrails, stub-provider routing, and restricted
`lotus-idea` caller policy only; it is not live provider execution, provider
rollout certification, model-risk operations certification, Workbench proof,
client-ready publication, or supported-feature promotion. The
downstream realization readiness diagnostic is an operator supportability
check only; it reports workflow counts, planned Advise/Manage/Report contract
posture, optional bounded route-foundation proof, optional bounded
Report/Render/Archive materialization proof, and remaining authority/product
blockers without calling downstream services from `lotus-idea`, granting
suitability or rebalance/execution authority, authorizing client publication,
or creating a supported feature.
The implementation-proof readiness diagnostic is also an operator supportability
check only; it aggregates blockers and evidence refs across source ingestion,
advisor queue, AI explanation, data mesh, runtime trust telemetry
preview/snapshot endpoint and evidence, outbox delivery, Workbench,
opportunity archetype scenarios, downstream realization, and supported-feature
promotion. It consumes a
  source-safe bounded live source-ingestion proof artifact, mesh policy proof
  artifact, bounded Workbench read-path proof artifact, bounded
  Gateway/Workbench source-contract proof artifact, and bounded
  Gateway/Workbench discovery contract proof artifact. Both artifacts add
  evidence references without clearing runtime blockers:
  `gateway_workbench_proof_missing` and
  `gateway_workbench_discovery_proof_missing` remain until observed runtime
  evidence exists. The diagnostic does not
provide full live implementation proof, external broker publication, downstream
delivery, full Gateway/Workbench live proof, data-product certification, or
supported-feature promotion. The opportunity archetype scenario readiness
family is taxonomy and replay-gap evidence only; the allocation-drift archetype
now requires API module, route, and integration-test evidence in the contract
gate, but that still does not promote live archetype proof, client-ready demo
material, or a supported feature. These are not externally
supported features until live source-worker certification, certified
long-running scheduled source-worker runtime proof, full Workbench live proof,
downstream acceptance, data-product certification, and supported-feature
evidence are present. The current scheduled worker deploy-contract proof is a
foundation control only.

Planned capabilities:

1. idea lifecycle and review state,
2. source-owned signal ingestion,
3. idea evidence packets,
4. deterministic scoring and ranking,
5. advisor opportunity queues,
6. feedback and suppression,
7. AI-assisted explanation through `lotus-ai`,
8. advisory and manage conversion intents,
9. reportable idea evidence,
10. any demo-ready opportunity journeys before full validation.

Promotion rule: a capability is supported only after implementation, tests,
endpoint certification, supported-feature registration, docs/wiki updates, and
validation evidence exist.

The registration step is now structured and machine-checked. Any future
entry under `features[]` in `supported-features/supported-features.json` must be
`implemented` and must carry owner, scope, unsupported scope, API surfaces tied
to the endpoint certification ledger, UI/consumer publication state, source
dependencies, Gateway/Workbench state, data-product state, tests, runtime
evidence, CI evidence, docs/runbooks, proof artifacts, known gaps,
last-reviewed UTC timestamp, and the promotion decision reference. Planned
capabilities remain under `planned_capabilities[]`; planned or not-applicable
records under `features[]` do not count as supported-feature promotion and are
rejected by `make supported-features-gate`. The implementation-proof readiness
diagnostic uses the same structured evaluator as the gate before clearing
`no_supported_features_promoted`. `make supported-features-gate` rejects
placeholder, string-only, stale-path, uncertified-endpoint, planned, or
not-applicable feature evidence. Reviews older than 90 days additionally emit
`supported_feature_promotion_evidence_stale`; invalid registry state emits
`supported_feature_registry_invalid`. API and generated readiness artifacts
project the same count and promotion state, and expose only safe registry refs.
This does not promote any current feature.
