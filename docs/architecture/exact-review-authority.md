# Exact Review Authority

## Audience and purpose

This document defines how product engineers, API consumers, database operators,
and control reviewers determine whether an Idea conversion is authorized by the
human decision actually made. It covers Idea-owned review authority only.
Advise, Manage, Report, compliance, suitability, execution, and client
communication remain authoritative for their own business outcomes.

## Control outcome

An approval authorizes exactly one candidate material version and evidence
version. A mutable `approved_for_conversion` posture is necessary but is never
sufficient. Conversion also requires the immutable approving review, its exact
evidence identity, and an active applicability window at Idea server acceptance
time.

```mermaid
sequenceDiagram
    participant W as Workbench
    participant I as Lotus Idea
    participant P as PostgreSQL
    participant D as Advise / Manage / Report

    W->>I: Read ranked candidate v4/e1
    W->>I: Persist presentation receipt v4/e1
    I->>P: Store receipt + queue/ranking digest
    W->>I: Approve v4/e1 with receipt ID
    I->>P: Lock candidate; verify scope, identity, receipt, time
    P-->>I: Immutable review decision / authority grant
    W->>I: Request conversion using review ID + v4/e1
    I->>P: Lock candidate; recheck exact active grant
    P-->>I: Persist intent and outbox atomically
    I->>D: Submit intent; downstream retains business authority
```

## Authority identity

`CandidateEvidenceIdentity` is the equality boundary used at presentation,
review, and conversion:

| Field | Meaning |
| --- | --- |
| `candidate_id` | Stable Idea candidate resource. |
| `material_version` | Decision-relevant economic opportunity revision. |
| `evidence_version` | Exact evidence revision supporting that material. |
| `evidence_packet_id` | Governed evidence-pack resource. |
| `evidence_content_hash` | Content identity of the evidence lineage. |

A Workbench review additionally binds `presentation_receipt_id` and
`queue_snapshot_digest`. The receipt proves that the exact candidate revision
was rendered in a governed queue context; a queue read alone is not proof of
presentation. Operator reviews are explicit and cannot carry a fabricated
Workbench receipt. New `legacy_unverified` reviews are rejected.

## Admission order

Review admission is intentionally ordered to avoid existence leakage:

1. authorize the caller role and persisted candidate scope;
2. validate lifecycle eligibility;
3. compare expected material/evidence/packet/hash identity;
4. load the receipt within the same tenant and candidate scope;
5. validate receipt identity, chronology, and the 30-minute review window;
6. apply and persist the review mutation under the candidate lock.

Conversion admission first honors exact idempotent replay. A new intent then
requires an approved, evidence-ready, target-eligible candidate, an exact
persisted approving review, an exact current evidence identity, and active
authority strictly before applicability expiry. The repository repeats the
grant check under its candidate mutation lock before writing the intent and
outbox event.

## Evidence-change compatibility policy

The current policy is `idea-review-authority-v1`:

The immutable decision and conversion grant persist this value as
`review_authority_policy_version` and expose it to consumers as
`authorityPolicyVersion`. A missing or unsupported value revokes effective
authority; it is never interpreted as the current policy.

- every material-version change supersedes the approval;
- every evidence-version, packet-ID, or evidence-hash change supersedes the
  approval, even when candidate material is unchanged;
- expiry at or before server acceptance makes the approval inactive;
- history is retained, but a fresh presentation and review are required;
- exact replay of an intent accepted before expiry remains replayable after
  expiry because it returns the already governed result and creates no new
  mutation.

No non-semantic repair class is certified in v1. Authority preservation must
not be inferred from an `evidence_correction` label. A future policy may preserve
authority only after it defines a deterministic repair proof, versions that
proof, and adds independent adversarial tests. Until then all evidence changes
fail closed.

## Legacy migration and operator audit

Migration `025_exact_review_authority.sql` does not backfill unverifiable facts.
It marks incomplete historical decisions as `legacy_unverified`, writes an
explicit null authority grant on historical intents that lack one, and exposes
the read-only `idea_review_authority_migration_audit` view.

Operators must inspect the view before rollout and after migration:

```sql
SELECT finding, COUNT(*) AS affected_resources
FROM idea_review_authority_migration_audit
GROUP BY finding
ORDER BY finding;
```

| Finding | Required action |
| --- | --- |
| `legacy_review_authority_unverified` | Retain the decision as history; do not treat it as conversion authority. |
| `conversion_intent_without_exact_review_authority` | Preserve the intent for audit/outcome reconciliation; do not replay it as proof of a governed approval. |
| `approved_candidate_without_exact_review_authority` | Re-present current evidence and obtain a new review before creating another conversion intent. |

An empty result proves only that the database contains no classified legacy
authority gaps. It does not certify Gateway/Workbench presentation, production
identity, downstream acceptance, or supported-feature promotion.

## Consumer contract

Workbench creates the presentation receipt only after the candidate is actually
visible. Gateway forwards the receipt and review/conversion fields unchanged;
neither consumer may reconstruct or alias authority identity. Canonical consumer
runtime evidence remains separately required.

## Validation

- Domain and application tests cover stale material/evidence/packet/hash,
  receipt absence and mismatch, scope isolation, role/channel ownership,
  applicability expiry, and replay.
- PostgreSQL tests cover immutable review identity, locked conversion admission,
  concurrency, restart hydration, and legacy migration classification.
- Endpoint certification and generated OpenAPI examples publish the exact
  review and conversion contract.
- Supported features remain unpromoted until remaining consumer and production
  certification evidence exists.
