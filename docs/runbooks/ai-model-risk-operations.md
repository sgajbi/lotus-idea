# AI Model-Risk Operations Runbook

## Purpose

This runbook supports the internal `lotus-idea` AI explanation foundation. It
helps operators and model-risk reviewers interpret source-safe dashboard panels
and alert rules without exposing prompt content, provider payload content,
restricted client references, portfolio references, source-route detail, trace
identifiers, or correlation identifiers.

## Operating Boundary

The dashboard and alert rules certify operational visibility over implemented
`lotus_idea_operation_events_total` telemetry only. They do not certify
`lotus-ai` live-provider execution, Workbench product behavior, data-mesh
publication, client-ready use, or supported-feature promotion.

## Dashboard Panels

| Panel | Operator Question | Expected Use |
| --- | --- | --- |
| AI Explanation Readiness Posture | Is the AI explanation foundation still blocked, not certified, and unpromoted? | Start here before any model-risk or supportability escalation. |
| AI Output Verifier Outcomes | Are AI explanation evaluations accepted, falling back, blocked, invalid, or permission denied? | Investigate repeated `blocked` or `invalid_state` outcomes through source-safe request metadata. |
| AI Lineage Durability And Promotion Guardrail | Are events coming from durable-storage-backed paths, and is promotion still false? | Confirm that readiness remains proof-backed and not overclaimed. |

## ai-explanation-unsupported-claim-block-rate

Trigger: `ai_explanation` operation events with `outcome="blocked"` increase
within the alert window.

Response:

1. Read `GET /api/v1/ai-explanations/readiness` with an operator caller context.
2. Confirm whether the blocker is unsupported source evidence, prohibited
   downstream authority, missing evidence, or invalid lifecycle posture.
3. Review source-safe AI lineage records by request id only through protected
   operator tools. Do not inspect prompt content or provider payloads in
   `lotus-idea`.
4. If the issue is workflow output quality, route it to `lotus-ai` workflow-pack
   governance. If the issue is source evidence quality, route it to the owning
   source product.

## ai-explanation-readiness-remains-blocked

Trigger: `ai_explanation_readiness_read` operation events with
`outcome="blocked"` increase within the alert window.

Response:

1. Inspect the readiness payload certification blockers.
2. Separate already-certified evidence from remaining blockers:
   `lotus-ai` runtime execution, runtime trust telemetry, Workbench product
   proof, and supported-feature promotion.
3. Do not promote the feature unless implementation-proof readiness, OpenAPI
   evidence, supported-features, docs, wiki, and GitHub checks all agree.

## Evidence Requirements

Certification evidence must include:

1. `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`,
2. `monitoring/grafana/dashboards/lotus-idea-ai-model-risk-operations.json`,
3. `monitoring/prometheus/rules/lotus-idea-ai-model-risk-operations.rules.yml`,
4. `scripts/ai_model_risk_operations_proof_contract_gate.py`,
5. `make ai-model-risk-operations-proof-contract-gate`,
6. implementation-proof readiness output showing only the dashboard and alert
   blockers cleared by this proof.
