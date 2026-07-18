# Lotus Idea Blueprint

| Field | Value |
| --- | --- |
| Status | Repo-authored product and architecture anchor |
| Applies to | RFC-0002 and later Lotus Idea opportunity-intelligence work |
| Current support posture | Foundation-only; no external supported feature is promoted |
| Issue evidence | `#594` |
| Last reviewed | 2026-07-18 |

This blueprint is the durable repository anchor for the Lotus Idea product
direction. It replaces dependency on a local Downloads-path source during
RFC execution and keeps future work aligned to the same product boundary,
engineering posture, and private-banking operating model.

This document is not implementation evidence by itself. Current implementation
truth remains the combination of code, tests, contracts, OpenAPI evidence,
RFC slice files, repository context, wiki source, CI proof, GitHub issue state,
and `supported-features/supported-features.json`.

## Product Definition

`lotus-idea` is the Lotus private-banking opportunity-intelligence and governed
idea-lifecycle engine. It turns source-owned portfolio, performance, risk,
advisory, management, reporting, and AI evidence into reviewable opportunity
candidates.

The service must behave as a bank-grade advisor decision-support system, not as
a generic chatbot and not as an autonomous investment engine.

The operating model is:

```text
source-owned facts
→ deterministic signal and eligibility policy
→ candidate and evidence packet
→ deterministic score, reason codes, and readiness posture
→ human advisor review
→ governed conversion intent
→ downstream owner acceptance or rejection
→ feedback and audit evidence
```

AI/ML/RAG can assist with explanation, summarization, ranking research, and
future learning only when deterministic evidence, source authority, entitlement
controls, model-risk governance, prompt/output governance, auditability, and
human review are in place.

## Owned Capabilities

`lotus-idea` owns:

1. opportunity detection policy,
2. idea candidate identity,
3. idea lifecycle status and review posture,
4. evidence packet composition and source-reference preservation,
5. deterministic scoring, ranking, suppression, and queue policy,
6. advisor review workflow and feedback capture,
7. conversion intent and local submission posture,
8. implementation-proof, runtime-readiness, and trust-telemetry posture for
   Idea-owned records,
9. Idea data-product declarations until platform certification and support
   promotion are proven.

## Non-Owned Capabilities

`lotus-idea` must not own or imply authority over:

1. portfolio accounting, official holdings, official cash, benchmark identity,
   client master, product master, or instrument master data;
2. official performance, attribution, benchmark methodology, risk,
   concentration, volatility, drawdown, stress, or scenario calculations;
3. suitability approval, compliance approval, mandate approval, proposal
   approval, rebalance authority, order execution, settlement, report
   rendering, archive authority, retention/legal-hold authority, or client-ready
   publication;
4. AI provider infrastructure, model hosting, prompt-platform ownership, RAG
   platform ownership, embedding/vector runtime, model operations, or autonomous
   AI decisions;
5. production identity-provider, token-claims, or authorization infrastructure.

Local and development fixtures may support controlled proof work, but they must
fail closed outside explicit local/test/development profiles and must never be
represented as production authentication, authorization, or entitlement proof.

## Source Authority Map

| Source authority | Owns | `lotus-idea` usage boundary |
| --- | --- | --- |
| `lotus-core` | Portfolio state, holdings, cash, benchmark assignment, maturity facts, client/product/instrument facts | Consume source receipts and create evidence-backed opportunity candidates; do not recompute or assign source facts |
| `lotus-performance` | Returns, attribution, benchmark-relative performance, methodology | Consume performance concern evidence; do not calculate official returns or benchmark methodology |
| `lotus-risk` | Risk metrics, concentration, volatility, drawdown, scenarios, stress | Consume risk concern evidence; do not calculate or approve risk methodology |
| `lotus-advise` | Suitability, advisory policy, proposals, approvals, risk profile, advisory journey | Block or prepare conversion posture; do not approve suitability or advisory recommendations |
| `lotus-manage` | Model portfolios, mandates, rebalance, portfolio actions, DPM workflow | Create review-gated intent only; do not create authoritative actions or rebalance outputs |
| `lotus-report` | Report evidence intake and report packages | Hand off governed evidence only; do not render or publish reports |
| `lotus-render` | Deterministic rendering | No local rendering authority |
| `lotus-archive` | Archive lifecycle, retention, legal hold, retrieval, purge authority | Preserve evidence posture and verify receipts only; do not own archive authority |
| `lotus-ai` | AI workflow execution, provider abstraction, prompt governance, model evaluation, model-risk runtime | Consume governed workflow results and attestations; do not call providers directly or own AI infrastructure |
| `lotus-gateway` | Product-facing API composition/BFF publication | Publish only bounded Idea-owned read/action contracts after backend truth exists |
| `lotus-workbench` | Advisor and portfolio-manager user experience | Render Idea truth only; do not infer, rank, or authorize Idea decisions locally |

## Target Opportunity Families

The initial deterministic foundation covers or plans these private-banking
opportunity families:

1. high cash / idle liquidity,
2. concentration risk,
3. benchmark underperformance,
4. allocation drift / mandate review,
5. bond maturity / reinvestment review,
6. low income / liquidity shortfall,
7. high volatility / drawdown review,
8. missing benchmark,
9. missing risk profile,
10. missing suitability context,
11. mandate or restriction review.

Each family must keep source facts in the owning service and express Idea
behavior as reviewable opportunity posture, not as trade advice, suitability
approval, risk approval, official performance/risk calculation, or client-ready
communication.

## Advisor Operating Model

Advisor-visible ideas should include:

1. a clear private-banking opportunity type,
2. source-owned evidence references,
3. source freshness and supportability posture,
4. deterministic reason codes,
5. score and ranking-policy provenance,
6. expected action posture without downstream authority inflation,
7. human-review requirement,
8. risk warning or abstention where evidence is stale, incomplete, conflicting,
   unsupported, or outside entitlement scope,
9. audit and replay metadata.

No actionable idea may be shown as a recommendation until governance posture is
explicit, source evidence is sufficient, and human review remains in the loop.

## AI And Model-Risk Boundary

AI assistance must follow these rules:

1. deterministic evidence exists before AI execution;
2. prompt/workflow identity is governed and versioned;
3. retrieved evidence and generated output are validated;
4. provider output cannot introduce unsupported numbers, return expectations,
   suitability conclusions, or client-sensitive claims;
5. accepted advisor-visible wording is derived from verified source claims or
   deterministic fallback text;
6. model/provider execution, prompt registry, RAG infrastructure, and model-risk
   runtime stay with `lotus-ai`;
7. production use requires model inventory, evaluation, drift/quality telemetry,
   incident handling, rollback, retention, and approval evidence;
8. AI cannot change lifecycle state, score, review decision, conversion state,
   suitability, compliance, mandate approval, client communication, or execution
   authority.

## Implementation Acceptance Constraints

Every material implementation slice must satisfy:

1. API/controller code maps DTOs and calls application use cases; it does not
   query repositories or external clients directly.
2. Application use cases coordinate ports, transactions, idempotency, and domain
   services; they do not contain vendor/provider-specific logic.
3. Domain code owns lifecycle, policy, scoring, evidence sufficiency, expiry,
   and showability behavior while remaining framework-independent.
4. Infrastructure code owns database, HTTP, messaging, observability, and AI
   adapters behind ports.
5. Mutating APIs require idempotency and source-safe audit evidence.
6. Errors use RFC 7807 Problem Details and must not leak raw upstream payloads,
   credentials, client identifiers, portfolio identifiers, prompts, provider
   output, or entitlement internals.
7. PostgreSQL read paths must use bounded projections where production-scale
   access is needed; full snapshots are administrative/test/DR behavior unless
   explicitly justified.
8. All external integrations go through source-authority preserving ports and
   adapters.
9. OpenAPI, contracts, docs, wiki source, repository context, and supported
   feature truth must move with implementation changes.
10. A supported-feature claim requires code, tests, contracts, OpenAPI evidence,
    docs/wiki, runtime proof, CI proof on `main`, post-merge validation, and
    support-promotion evidence.

## Market And Differentiation Posture

The durable product thesis is governed advisor decision support:

1. portfolio-aware ideas rather than generic market commentary,
2. source-authority preserving explanations rather than opaque narratives,
3. deterministic eligibility and governance gates before AI wording,
4. advisor review before client communication or downstream action,
5. idea-to-action conversion with downstream source-owner acceptance,
6. model-risk and audit evidence suitable for bank review.

Market research informs product hypotheses only. It does not certify Lotus
behavior, supported features, or client-ready claims. Refresh and record
primary-source research in
`docs/research/advisor-intelligence-product-differentiation.md` before
external AI/product positioning changes.

## Current Non-Claim Boundary

This blueprint does not certify:

1. live source ingestion,
2. Gateway/Workbench product support,
3. data-product promotion,
4. downstream execution or report materialization,
5. broker publication,
6. production load/soak/resource/cost evidence,
7. production IdP/authn/authz,
8. AI provider-runtime execution,
9. client-ready publication,
10. externally supported product features.

Those claims remain controlled by RFC slice evidence, issue trackers, platform
certification, CI/mainline validation, and supported-feature promotion.
