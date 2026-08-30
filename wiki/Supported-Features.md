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

PR #746 corrected stale ready posture for issue #380 and reconciled it to
`open_blocked` on exact main `6f8875dc6784dd17975e6700c09b9ff71d66fb8b`;
Main Releasability `30327202465` and CodeQL `30327193673` passed for that
state. This is blocker-truth evidence, not promotion evidence. The registry
stays `foundation_only` with zero promoted features until production
principal/session, authenticated Workbench BFF, core-owned canonical runtime,
canonical all-main Gateway/Workbench live evidence, entitlement-denied proof,
mesh onboarding certification, and the supported-feature promotion evaluator
all agree that a feature is supportable.

## Current Execution Impact

For live RFC execution posture, see
[RFC-0002 Execution Status](RFC-0002-Execution-Status).

| Audience | What this means now | Safe next action |
| --- | --- | --- |
| Business and product | Lotus Idea has implementation-backed foundations for opportunity intelligence, review, evidence, and conversion intent, but no external feature is supportable yet. | Use foundation language; do not claim a supported advisory product. |
| Sales and demo | Demonstrations may describe governed foundations and do-not-claim boundaries only. The latest canonical QA did not complete. Workbench PR #698 is merged and validated, but it is not end-to-end product proof. | Wait for fresh canonical QA evidence before using end-to-end product proof. |
| Operations and support | Internal health, readiness, issue posture, and supportability diagnostics exist; production support obligations are not promoted. | Use the runbooks and QA artifacts to diagnose, not to certify production readiness. |
| Engineering and agents | The dated 2026-08-30 baseline tracks 238 label-backed RFC-0002 issues across 13 repositories: 201 closed and 37 open, with 25 `status/blocked`, 2 `status/in-progress`, 1 `status/merged-main`, 9 `status/tracker`, and 0 app-actionable blocked issues. The Idea source ledger tracks 147 RFC-0002 issues: 121 closed and 26 open, with `sgajbi/lotus-idea#681` and `#1145` in progress and `#1139` closed after PR #1147 exact-main, live-posture, wiki, and branch-hygiene proof; `#1119`, `#1121`, `#1123`, `#1125`, `#1127`, `#1129`, and `#1131` are closed after Slice 17 release-governance hardening. | Fix writable blockers when discovered, keep GitHub state durable, and rerun canonical QA before closure. |

The latest canonical front-office QA failed before AI/Advise proof because the
Workbench browser did not observe the Gateway-backed feedback confirmation.
That run cannot close remaining QA-pending merged-main issues such as
`sgajbi/lotus-ai#126`, `sgajbi/lotus-advise#481`,
or `sgajbi/lotus-advise#485`. It did prove `sgajbi/lotus-platform#659`
because the DPM command-center seed completed with status `ok` before the
later browser failure.

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
profile, and `make source-ingestion-scheduled-worker-check` also exist. Static
scheduler declarations are non-clearing `source_contract` evidence; deployment
blocker clearance requires a separate matching observed deployment receipt.
`POST /api/v1/source-ingestion/run-once` adds a certified internal
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
broker runtime, Gateway event, platform-mesh event runtime publication, downstream
delivery, or supported event publication exists. `lotus-gateway` now publishes bounded
advisor queue/detail reads plus Idea-owned review-action, feedback, and
conversion-intent routes with caller entitlement-scope, idempotency, correlation,
and trace forwarding. `lotus-workbench` renders the corresponding controls
through its BFF, which removes browser-supplied Idea authority. Its configured
authority fixture is development-only and non-development requests fail closed
before Gateway. These foundations are not authenticated-principal or
identity-provider proof, deployed scheduler daemon proof, live Core worker
certification, full Workbench live proof, or supported-feature promotion. The bounded live source-ingestion
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
model-risk operations source-contract proof validates repo-owned dashboard,
alert-rule, and runbook source against implemented operation telemetry. It
clears no readiness blocker and does not prove provisioning, rule evaluation,
alert delivery, Workbench behavior, client-ready publication, or
supported-feature promotion. Source-safe AI explanation lineage persistence has
PostgreSQL runtime proof for accepted, replayed, and conflicting request ids,
and the readiness diagnostic reports durable lineage backing when the active
repository is durable. That proof is repository durability evidence, not
`lotus-ai` runtime execution or AI product certification. The bounded
AI workflow-pack registration source-contract proof validates sibling `lotus-ai`
`idea_explanation.pack@v1` registration, binding, queue policy,
supportability, and tests only. It adds evidence without clearing
`workflow_pack_runtime_contract_not_certified`; it is not runtime registry
observation, provider execution, model-risk
operations certification, Workbench proof, or supported-feature promotion. The
bounded AI workflow-pack runtime execution proof validates an actual
deterministic review-gated invocation, receipt identity, evidence-hash binding,
guardrails, stub-provider routing, and restricted
`lotus-idea` caller policy only; it is not live provider execution, provider
rollout certification, model-risk operations certification, Workbench proof,
client-ready publication, or supported-feature promotion. The
downstream realization readiness diagnostic is an operator supportability
check only; it reports workflow counts, local unresolved downstream submission
submission denominator, reconciliation workload, planned Advise/Manage/Report contract posture,
optional digest-bound route source-contract evidence, optional bounded
Report/Render/Archive source-contract evidence, and remaining authority/product
blockers without calling downstream services from `lotus-idea`, granting
suitability or rebalance/execution authority, authorizing client publication,
or creating a supported feature.
The implementation-proof readiness diagnostic is also an operator supportability
check only; it aggregates blockers and evidence refs across source ingestion,
advisor queue, AI explanation, data mesh, runtime trust telemetry
preview/snapshot endpoint and evidence, outbox delivery, Workbench,
opportunity archetype scenarios, downstream realization, supported-feature
promotion, and the Slice 17 full-live journey proof contract. The full-live
journey proof can compose readiness, Gateway/Workbench runtime evidence,
downstream handoff posture, and supported-feature blockers, but it remains
non-promotional while any blocker remains. Freshness-guarded Workbench evidence
is required; stale `live-validation-summary.json` and screenshot artifacts
cannot be regenerated into current live-journey proof. It consumes a
  source-safe receipt-bound source-ingestion runtime-execution artifact, digest-bound mesh
  policy source-contract artifact, bounded Workbench read-path source-contract artifact, bounded
  Gateway/Workbench source-contract proof artifact, and bounded
  Gateway/Workbench discovery contract proof artifact. It can also consume an
  optional bounded Gateway/Workbench runtime-execution artifact generated from
  Workbench canonical live-validation evidence. The source-contract artifacts add
  evidence references without clearing runtime blockers:
  `gateway_workbench_proof_missing` and
  `gateway_workbench_discovery_proof_missing` remain until observed runtime
  evidence exists. The runtime artifact may clear only
  `workbench_gateway_bff_consumption_proof_missing` when valid and
  aggregate-current. The diagnostic does not
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
evidence are present. The scheduler source contract and deployment-evidence
contract are foundation controls only and do not promote a supported feature.

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
