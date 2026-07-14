# Advisor Intelligence Product Differentiation Charter

| Field | Value |
| --- | --- |
| **Status** | Research and delivery guardrail; not implementation or supported-feature evidence |
| **Applies to** | RFC-0002 Slice 09 and later Gateway, Workbench, proof, and promotion slices |
| **Last reviewed** | 2026-07-14 |
| **Product owner** | `lotus-idea` for opportunity intelligence; `lotus-ai` for AI runtime infrastructure and governed workflow packs |
| **Review trigger** | Before Slice 09 implementation resumes, before a material AI capability decision, and before supported-feature promotion |

## Decision

Lotus Idea will differentiate through **governed advisor decision support**, not
through a general-purpose chatbot or autonomous next-best-action engine.

The market baseline already includes proactive opportunity surfacing,
portfolio-grounded commentary, meeting preparation, and personalized nudges.
Lotus must go further where private-bank buyers carry the most risk: every
advisor-visible output must be evidence-bound, source-authority preserving,
replayable, uncertainty-aware, entitlement-safe, review-gated, and measurable.

This document records product hypotheses and delivery controls. A hypothesis
becomes product truth only after code, tests, contracts, OpenAPI evidence,
runtime proof, documentation and wiki synchronization, CI proof, mainline
validation, and supported-feature promotion all exist.

## Market Baseline

Primary sources reviewed on 2026-07-14 show four established patterns:

| Pattern | Public evidence | Consequence for Lotus |
| --- | --- | --- |
| Portfolio analytics translated into advisor commentary | [BlackRock AI-enabled investing](https://www.blackrock.com/aladdin/discover/blog/ai-enabled-investor) describes governed Auto Commentary over analytics, firm views, portfolio holdings, and preferences, with advisor review before use. | Summarization and human review are baseline. Lotus explanations must additionally expose evidence coverage, provenance, conflicts, and abstention. |
| Proactive opportunity and liquidity-event detection | [UBS advisor AI](https://www.ubs.com/us/en/wealth-management/financial-advisor-experience/articles/ai-for-financial-advisors.html) describes analytics and ML surfacing client opportunities and meeting briefings. | Detection must be cross-domain and deterministic-first, with explicit source authority and queue-policy lineage. |
| Meeting workflow assistance with human control | [Morgan Stanley AI Debrief](https://www.morganstanley.com/press-releases/ai-at-morgan-stanley-debrief-launch) creates meeting notes, action items, and drafts for advisor review. | Human review is baseline. Lotus must additionally bind outputs to governed evidence and prohibit downstream authority. |
| Personalized nudges at operating scale | [DBS AI-powered nudges](https://www.dbs.com/artificial-intelligence-machine-learning/index.html) describes personalized insights and relationship-manager discussion prompts. | Personalization must be bounded by entitlement, purpose, policy, freshness, and model-risk controls rather than opaque targeting. |

Control design must continue to use current authoritative guidance, including
the [NIST Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
and applicable financial-sector model-risk and responsible-AI requirements.
Market material informs hypotheses; it never certifies Lotus behavior.

## Differentiation Hypotheses

The following capabilities are candidates for implementation research. They are
ordered by bank value and control feasibility, not novelty alone.

| Capability hypothesis | Differentiating behavior | Required deterministic anchor | Minimum proof before promotion |
| --- | --- | --- | --- |
| Evidence-grounded advisor narrative | Every statement maps to an evidence item, source product, freshness posture, and supported or unsupported claim state. | Immutable evidence packet and source-authority contract | Claim-level grounding tests, adversarial unsupported-claim tests, lineage replay, and advisor-visible provenance proof |
| Counterfactual opportunity analysis | Shows which governed facts or thresholds caused an idea and what bounded change would remove or reprioritize it, without calculating official risk or performance. | Versioned detection, scoring, and queue policies over source-owned facts | Boundary tests, threshold-edge tests, policy-version replay, and source-owner parity evidence |
| Governed review prioritization | Recommends review order with explicit reasons, urgency, evidence quality, conflicts, and abstention instead of an opaque rank. | Deterministic score and compatible queue-ranking policy | Stable-order, policy-compatibility, fairness-segment evaluation, drift, stale-evidence, and fail-closed tests |
| Multilingual controlled explanation | Produces localized advisor drafts while reason codes, figures, source references, and prohibited-action controls remain invariant. | Canonical structured explanation before translation | Terminology glossary, numeric invariance, prohibited-content, locale fallback, and qualified human review evidence |
| Feedback learning with model-risk fences | Uses approved aggregate review outcomes to evaluate policies or propose a challenger; it never changes production policy autonomously. | Versioned feedback taxonomy, approved training view, champion/challenger governance | Leakage, bias, representativeness, reproducibility, approval, rollback, and no-online-learning proof |
| Evidence-aware meeting preparation | Builds a bounded briefing from current ideas, conflicts, unanswered evidence, and approved firm context while clearly separating facts from draft language. | Entitled candidate/evidence projection and governed workflow pack | Purpose-limited retrieval, redaction, stale/conflict handling, prompt/output lineage, and human-review proof |

Novelty is not an acceptance criterion. A capability should be rejected when it
adds cognitive or runtime complexity without measurable advisor value,
defensible control improvement, or a clear operating owner.

## Selected Delivery Hypothesis

Issue [#389](https://github.com/sgajbi/lotus-idea/issues/389) selects the
evidence-grounded advisor narrative hypothesis for the current bounded delivery.

| Dimension | Falsifiable decision |
| --- | --- |
| Advisor outcome | Every accepted advisor-visible sentence is rendered by Idea from an ordered claim that passed deterministic source-product verification. |
| Control outcome | The submitted provider narrative is absent from the accepted response, audit attributes, and persisted lineage; source-safe claim references expose product/version, as-of date, freshness, and quality. |
| Failure posture | Unsupported or otherwise blocked output returns no grounded claims and cannot be presented as evidence-backed narrative. |
| Ownership | `lotus-ai` owns provider/model execution and attestation; `lotus-idea` owns deterministic claim verification, grounded projection, replay identity, and human-review posture. |
| Acceptance threshold | Behavioral tests prove 100% of accepted narrative derives from verified claims and zero submitted narrative is returned or persisted. |

This is a controlled explanation foundation, not a claim that Lotus predicts an
outcome, gives advice, or has completed live-provider, Gateway, Workbench, or
supported-feature certification. BlackRock's 2026 product framing reinforces
that advisor commentary and mandatory advisor review are now baseline; Lotus's
selected differentiator is the deterministic evidence and control boundary.

## Bank-Buyability Controls

Every AI-assisted capability must satisfy all of these controls:

1. deterministic evidence exists before AI execution;
2. source services retain authority for portfolio, performance, risk,
   suitability, compliance, mandate, and reference-data facts;
3. entitlement and purpose checks occur before evidence retrieval or workflow
   invocation;
4. prompts, retrieval inputs, outputs, model identity, workflow-pack identity,
   policy versions, evaluations, and reviewer outcomes have governed lineage;
5. unsupported evidence, stale evidence, conflicting evidence, provider
   failure, and verifier failure produce explicit abstention or deterministic
   fallback;
6. AI cannot alter score, lifecycle, review state, conversion state, official
   calculations, suitability, compliance, mandate approval, client
   communication, or execution authority;
7. production use has model inventory, risk classification, evaluation suites,
   drift and quality telemetry, incident handling, rollback, retention, and
   change approval;
8. sensitive data minimization and closed metadata allowlists are proven at
   API, application, adapter, persistence, log, and telemetry boundaries;
9. advisor-visible wording distinguishes source fact, deterministic inference,
   AI draft, uncertainty, missing evidence, and prohibited action;
10. supported-feature claims remain blocked until live canonical and mainline
    evidence proves the complete path.

## Architecture Constraint

Design modularity comes first. Keep candidate intelligence, evidence
projection, explanation policy, evaluation, and feedback measurement as
internally bounded modules with stable ports.

`lotus-idea` must use `lotus-ai` for governed AI workflow execution. A new
runtime process or service is justified only by measured workload,
failure-isolation, ownership, security-boundary, or operability evidence. AI
features do not justify moving deterministic opportunity truth or source-owned
analytics out of their existing owners.

## Research-To-Delivery Gate

Before implementing a capability from this charter:

1. refresh primary-source market and regulatory research and record the access
   date;
2. write a falsifiable differentiation hypothesis and identify the advisor and
   control outcome it should improve;
3. define ownership, data classification, source authority, entitlement,
   lifecycle, failure, fallback, audit, and human-review contracts;
4. define offline evaluation sets, adversarial cases, acceptance thresholds,
   and production telemetry before selecting a model or prompt;
5. implement through API, DTO mapping, application use case, domain policy,
   port, and infrastructure adapter layers;
6. prove edge cases, contract truth, replay, operability, and clean degradation;
7. validate the canonical Gateway and Workbench journey only after backend
   truth is ready;
8. promote support only through the governed supported-feature gate.

Research that does not change a decision belongs in working notes, not this
charter. Durable updates should record a changed hypothesis, control, source,
or acceptance criterion and keep this page concise.
