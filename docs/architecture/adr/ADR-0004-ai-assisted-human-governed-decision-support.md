# ADR-0004: AI-Assisted Human-Governed Decision Support

Status: Accepted

Date: 2026-06-21

## Context

The idea blueprint calls for AI-assisted explanations and opportunity discovery,
but Lotus must remain bank-buyable. AI cannot be the uncontrolled owner of
suitability, compliance, execution, or client communication.

## Decision

`lotus-idea` will be deterministic-first and AI-assisted-second.

Deterministic rules create, score, suppress, expire, and route ideas. AI
capabilities are consumed from `lotus-ai` for explanation drafting, evidence
summarization, verifier workflows, and natural-language support where the
relevant RFC approves the use case.

Human review remains mandatory before advisory, portfolio-management, reporting,
or client-facing realization.

## Consequences

AI can improve advisor productivity without weakening governance. Every AI
artifact must be linked to source evidence, prompt/workflow version, model
evaluation posture, verifier result where applicable, and human review outcome.
