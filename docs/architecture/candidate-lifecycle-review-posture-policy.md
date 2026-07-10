# Candidate Lifecycle And Review-Posture Policy

## Purpose

Lotus Idea uses lifecycle status and review posture as one governed candidate
state, not as independent flags. Policy `idea-candidate-state-v1` prevents a
terminal candidate from remaining actionable and gives API, queue, persistence,
audit, and support tooling one deterministic interpretation.

This policy governs Lotus Idea's internal opportunity and review workflow. It
does not grant downstream suitability, compliance, mandate, execution,
settlement, performance, risk, report-rendering, or archive authority.

## Core Invariants

1. Every `IdeaCandidate` must have a lifecycle/posture pair present in the
   golden matrix.
2. Construction and PostgreSQL JSON rehydration reject contradictory pairs with
   `candidate_state_conflict` and policy version `idea-candidate-state-v1`.
3. Transitions to `expired` or `closed` normalize posture to `no_action`.
4. Transitions to `rejected` normalize posture to `rejected`.
5. Approval and conversion-intent states retain
   `approved_for_conversion`; this records Idea review posture and does not
   assert downstream acceptance or execution.
6. PostgreSQL review queue and readiness queries derive compatibility from the
   domain policy and classify contradictory legacy records as `invalid_state`.

## Golden Matrix

| Lifecycle status | Allowed review postures |
| --- | --- |
| `detected`, `generated`, `enriched`, `scored`, `governance_checked` | `not_reviewed`, `advisor_review_required`, `pm_review_required`, `compliance_review_required`, `suppressed` |
| `ready_for_review` | `advisor_review_required`, `pm_review_required`, `compliance_review_required`, `suppressed` |
| `reviewed_by_advisor` | `advisor_reviewed`, `pm_review_required`, `compliance_review_required`, `suppressed` |
| `approved` | `approved_for_conversion` |
| `converted_to_proposal`, `converted_to_manage_review`, `converted_to_report` | `approved_for_conversion` |
| `accepted`, `executed` | `approved_for_conversion`; these statuses remain reserved for source-authority ingestion and are not caller-settable lifecycle targets |
| `rejected` | `rejected` |
| `expired`, `closed` | `no_action` |

## Review-Action Matrix

| Action family | Allowed lifecycle states | Repeated behavior |
| --- | --- | --- |
| approve, reject, no action | `ready_for_review`, `reviewed_by_advisor` | first action produces a terminal or approved state; subsequent actions fail with `review_action_conflict` |
| suppress, snooze, PM escalation, compliance escalation | reviewable states from `generated` through `ready_for_review`, plus `reviewed_by_advisor` | an equivalent repeated domain command is deterministic; repository idempotency remains the request replay boundary |

Entitlement and access-scope checks run before state checks so an unauthorized
caller cannot use conflict responses to inspect candidate posture.

## Persistence And Queue Behavior

Migration `005_candidate_state_policy` performs two controls:

1. copies existing contradictory snapshots into
   `idea_candidate_state_quarantine` with policy version and diagnostic code;
2. adds `ck_idea_candidate_record_state_policy_v1` as a `NOT VALID` check.

`NOT VALID` is intentional: it blocks contradictory inserts and updates without
making deployment depend on immediate cleanup of historical records. Queue and
readiness SQL independently excludes those historical rows as `invalid_state`,
so they cannot become advisor work items.

## Legacy Reconciliation

Operations should reconcile quarantine entries in this order:

1. compare the row with lifecycle history and the latest governed review
   decision;
2. determine the correct pair from this matrix without inferring downstream
   acceptance or execution;
3. update the candidate through a controlled repair procedure that records
   actor, change reference, prior state, resulting state, and policy version;
4. verify the row no longer appears in readiness `invalid_state` counts;
5. validate `ck_idea_candidate_record_state_policy_v1` only after all legacy
   contradictions are reconciled.

Do not delete quarantine evidence merely to make validation pass.

## API And Operability

Review mutations return product-safe `409` ProblemDetails:

- `review_action_conflict` when an action is not allowed for a valid state;
- `candidate_state_conflict` when persisted state itself is contradictory;
- `idempotency_conflict` when the request key conflicts with an earlier payload.

Rejected review operation events include candidate ID, prior lifecycle,
posture, requested action, and policy version. They exclude client, portfolio,
request-body, and entitlement material. Accepted audit records carry the same
state-transition context plus actor role and evidence packet reference.

## Runtime Modularity Decision

This control is implemented as an internal bounded domain policy with a derived
PostgreSQL adapter predicate. A separate service would add network, deployment,
consistency, and incident-response complexity without workload, scaling,
failure-isolation, ownership, or operability evidence. Runtime separation is
therefore not justified.

## Validation

Run:

```powershell
make candidate-state-contract-gate
make migration-execution-gate
make test-unit
make test-integration
make typecheck
make lint
```

Supported-feature promotion remains blocked until merge, remote CI, canonical
runtime proof, data-mesh certification, documentation/wiki publication, and
mainline validation are complete.
