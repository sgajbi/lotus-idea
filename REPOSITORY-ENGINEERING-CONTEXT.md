# Repository Engineering Context

This is the concise, repository-specific operating context for `lotus-idea`. It complements the
shared Lotus contract; it does not replace `AGENTS.md`, duplicate platform standards, or track
active delivery history.

Start every task with this small set:

1. Read `AGENTS.md` for instruction precedence and mandatory controls.
2. Read the shared
   [Lotus Quickstart Context](https://github.com/sgajbi/lotus-platform/blob/main/context/LOTUS-QUICKSTART-CONTEXT.md).
3. Read this file for Idea ownership, architecture, invariants, and task routing.
4. Load specialist documents only when the task route below requires them.

When a sibling `lotus-platform` checkout exists, use its `context/` and `skills/` sources. When it
does not, use the canonical GitHub links in this file. Active issues, PRs, branches, runs, and
temporary blockers belong in GitHub rather than this context.

## Repository Role

`lotus-idea` provides opportunity intelligence and governed review for Lotus wealth applications.
It turns authoritative portfolio evidence into explainable opportunity candidates, lets advisers
review those candidates, records governed conversion intent, and reconciles source-owned outcomes.

The implemented lifecycle is:

```text
detect -> qualify -> score/rank -> review -> convert -> outcome -> learn
```

Idea owns candidate identity, evidence, qualification, ranking, presentation posture, adviser
review evidence, conversion intent, and its reconciliation record. It does not become the source
of truth for holdings, risk, performance, suitability, proposals, mandates, reports, or archives.

## Business And Domain Responsibility

Idea supports opportunity families such as high cash, portfolio concentration, approaching bond
maturity, drawdown review, and high volatility. A candidate is decision support, not advice,
approval, suitability, or execution.

Domain language must preserve these distinctions:

- A **source observation** is evidence supplied by its owning service.
- An **opportunity candidate** is a deterministic, scoped interpretation of that evidence.
- A **presentation receipt** proves what an adviser was shown; it is not a decision. Its request
  names the tenant and trusted caller entitlements authorize membership, so plural entitlement
  order never selects the tenant or durable receipt identity.
- A **review decision** is adviser-owned evidence accepted through the review command.
- A **conversion intent** records a governed request for downstream work.
- A **downstream outcome** is authoritative only when reconciled from the owning service.
- A transport success, timeout, or not-found response is never a business outcome by itself.

Use `docs/LOTUS_IDEA_BLUEPRINT.md` as the product-definition anchor. Do not present planned
blueprint capabilities as delivered.

## Current-State Summary

Internal foundations are implemented; externally supported product features remain unpromoted.
The authoritative capability classification is `supported-features/supported-features.json`, and
promotion rules are in `docs/operations/supported-feature-promotion.md`.

Implemented foundations include:

- deterministic candidate identity and evidence hashing;
- source-revision and source-time coherence classification;
- qualification, scoring, ranking, suppression, snooze, expiry, recurrence, and reopen policy;
- persisted presentation receipts, review decisions, feedback, and conversion intents;
- action-specific review evidence is exclusive: suppression reason belongs only
  to `suppress`, and snooze horizon belongs only to `snooze`; invalid combinations
  fail before durable mutation;
- exact replay, concurrency fencing, PostgreSQL persistence, and transactional outbox behavior;
- durable intent-before-I/O for downstream submission;
- tenant-scoped caller replay identity plus one governed downstream submission
  per tenant/resource/target, with opaque recovery references;
- exact read-only reconciliation after uncertain downstream submission;
- cross-process PostgreSQL proof for Report retained-receipt advancement,
  version fencing, concurrency convergence, and no duplicate submission;
- trusted local acceptance chronology while preserving source-observed time separately;
- governed AI explanation evidence and completion fencing;
- opportunity-quality golden evaluation and effectiveness evidence;
- readiness, observability, migrations, recovery controls, image scanning, and release evidence.

No externally supported product feature is promoted yet. Production identity, protected deployment
evidence, live source-owner acceptance, canonical consumer proof, archive trust, client publication,
and feature-promotion approval remain separate certification boundaries. Consult the live GitHub
issues linked from `docs/operations/implementation-proof-readiness.md` for current execution state.

## Architecture And Module Map

The service follows inward dependencies:

```text
HTTP API / middleware
        |
application workflows and commands
        |
domain policy and immutable evidence
        |
ports / repository contracts
        |
PostgreSQL and outbound HTTP adapters
```

| Area | Responsibility | Start here |
| --- | --- | --- |
| API | HTTP resources, request validation, OpenAPI | `src/app/main.py`, `src/app/api/` |
| Application | Use-case orchestration and transaction boundaries | `src/app/application/` |
| Domain | Candidate, review, scoring, identity, chronology, outcome policy | `src/app/domain/` |
| Persistence | Repository interfaces, PostgreSQL state, migrations | `src/app/ports/`, `src/app/infrastructure/`, `migrations/` |
| Integration | Source and downstream contracts/adapters | `src/app/integration/` |
| Runtime | Readiness, release identity, outbox, recovery posture | `src/app/runtime/` |
| Observability | Structured operation events and service indicators | `src/app/observability/`, `src/app/middleware/` |
| Contracts | Schemas and governed operational limits | `contracts/`, `src/app/contracts/` |

Keep business rules in domain/application code, not route handlers or infrastructure adapters.
Preserve one authoritative implementation per rule. Remove dead paths when equivalence and callers
are proven; do not retain compatibility layers speculatively.

## Runtime And Integration Boundaries

The recommended local runtime is `docker compose up -d --build`: Idea API plus its PostgreSQL
repository. The API listens on port `8330`; `/health/live` reports process liveness and
`/health/ready` reports dependency-aware readiness. A degraded dependency must produce truthful
readiness rather than a synthetic success.

Core, Risk, and Performance own upstream facts. Advise, Manage, Report, Render, and Archive own
their resulting business state. Gateway and Workbench are consumers, not alternative authorities.

Critical invariants:

1. Candidate scope must be explicit; unscoped durable candidates are rejected.
2. Candidate identity is deterministic from economic identity and governed evidence.
3. Evidence and lineage content hashes use canonical `sha256:<64 lowercase hex>` values. Only the
   historical revision-vector boundary permits the explicit `legacy:unknown` sentinel.
4. Known source-revision or restatement contradictions fail authority advancement. Shared cut IDs
   and time tolerance cannot override a known contradiction.
5. Unknown comparison remains uncertain; never invent source-owner identities or coherence.
6. Generic lifecycle mutation cannot create review, approval, or conversion authority; malformed
   review/conversion evidence digests fail request validation before authority or persistence work.
7. Review and conversion use their owned commands and exact presentation/review grants.
8. Conversion outcomes require complete trusted tenant/book/portfolio/client entitlements matching
   the persisted candidate before idempotency precheck or mutation.
9. Trusted acceptance time governs local chronology; source-observed time remains separate evidence.
10. Outbound work records durable intent before I/O.
11. An uncertain submission is not automatically resubmitted. Reconciliation is exact and read-only.
12. A first downstream conversion attempt revalidates current candidate evidence, exact active
    review authority, source-cut authority, target lifecycle, and owner authority before claim or
    I/O. Retained `legacy:unknown` evidence remains auditable but cannot authorize new owner work.
13. Exact replay does not create duplicate state, owner work, events, or outbox records.
14. AI output is advisory evidence. It cannot bypass deterministic eligibility or human authority.
15. Sensitive source payloads and adviser content must not be emitted in logs or metrics.

Configuration is defined in `src/app/runtime/settings.py` and `.env.example`. Keep environment
examples non-secret and fail closed when protected controls are required but unavailable.
Data-mesh declarations remain proposed until the evidence in
`docs/operations/mesh-readiness.md` satisfies the platform-owned promotion contract.

## Repo-Native Commands

Run commands from the `lotus-idea` repository root. Python 3.12 is the tested baseline;
`pyproject.toml` declares Python `>=3.12`. The install target creates `.venv` and installs the
locked contributor environment:

```powershell
make install
```

Preferred validation commands:

| Intent | Command |
| --- | --- |
| Fast repository gate | `make check` |
| Lint and governed static gates | `make lint` |
| Static typing | `make typecheck` |
| Unit tests | `make test-unit` |
| Integration tests | `make test-integration` |
| End-to-end journey | `make test-e2e` |
| Documentation contract | `make documentation-contract-gate` |
| Foundation structure | `make foundation-structure-gate` |
| Implementation truth | `make implementation-truth-gate` |
| PostgreSQL proof lane | `make postgres-integration-gate` (automatically runs every integration test that directly requests `postgres_database_url`) |
| Full release evidence | `make ci-release` |

Durable local startup:

```powershell
docker compose up -d --build
Invoke-RestMethod http://127.0.0.1:8330/health/ready
docker compose down
```

Expected readiness is HTTP `200` with `status: ready`. Preserve the named PostgreSQL volume unless
the task explicitly requires destructive reset evidence. The reload-based process described in
`wiki/Getting-Started.md` is an ephemeral developer alternative.

## Validation And CI Expectations

Select validation in proportion to the changed risk, then run the repository-native PR lane before
merge. Never make a test green by weakening assertions, skipping behavior, or hiding a failure.

For all changes:

- add behavioral tests for the new or corrected invariant;
- test rejection paths and state non-mutation, not only successful responses;
- preserve exact replay and concurrency behavior where lifecycle state changes;
- validate OpenAPI and contracts when public request/response behavior changes;
- validate PostgreSQL state, evidence, and outbox consistency for persistence changes;
- run `make documentation-contract-gate` when governed prose changes;
- record either the wiki update or an explicit no-wiki-change decision in the PR;
- use `make check` as the normal local pre-PR baseline.

Before claiming completion, verify the PR head and the resulting `main` revision. Required checks,
release identity, wiki publication when applicable, and branch cleanup are completion evidence—not
substitutes for product behavior.

Do not create source-sync PRs for volatile issue counts, run IDs, branch names, image digests, or
current PR numbers. Record that evidence in GitHub or generated artifacts.

## Standards And RFCs That Govern This Repository

Load only the material relevant to the task:

| Task | Read because |
| --- | --- |
| Any code change | `AGENTS.md`, shared engineering context, this file |
| API or OpenAPI | `docs/architecture/README.md`, `docs/operations/api-certification.md`, API contracts |
| Candidate/domain policy | `docs/LOTUS_IDEA_BLUEPRINT.md`, relevant RFC-0002 slice, domain tests |
| Review or conversion | `docs/architecture/exact-review-authority.md`, `docs/operations/conversion-governance.md` |
| Downstream reconciliation | `docs/architecture/conversion-outcome-identity-and-lifecycle.md`, downstream readiness runbook |
| Source chronology/revisions | `docs/architecture/source-revision-authority.md`, `docs/architecture/trusted-control-time.md` |
| AI explanation/governance | `docs/operations/ai-governance.md`, ADR-0004, AI contracts |
| Persistence/migrations/recovery | `docs/operations/persistence.md`, migration and DR runbooks |
| CI/release/security | `quality/ci_quality_gates.md`, enterprise readiness, platform-owned standards |
| Documentation/wiki | README/wiki governance skill and repository documentation contract |
| RFC work | `docs/rfcs/README.md`, controlling RFC and slice file, GitHub controller issue |

Shared standards and skills are authoritative in
[lotus-platform](https://github.com/sgajbi/lotus-platform). Consult the
[Skill Routing Map](https://github.com/sgajbi/lotus-platform/blob/main/context/LOTUS-SKILL-ROUTING-MAP.md)
before choosing overlapping workflows. Repository-local documents own Idea-specific truth.

## Known Constraints And Implementation Notes

- Supported-feature promotion remains fail-closed until its independent evidence is complete.
- Local development does not require production authentication. Production identity, authorization,
  session claims, and protected secret/key integration remain explicit deployment prerequisites.
- Protected-environment DR, migration, and recovery execution requires named operator access,
  provider credentials, target database coordinates, and approved evidence storage.
- Live downstream acceptance is owned by the corresponding service and environment. Idea may prove
  its intent and reconciliation behavior but cannot self-certify an owner's business outcome.
- Archive trust, legal retention, client publication, and canonical consumer acceptance remain
  separately governed.
- Archive lifecycle key trust uses the governed `active`/`rotated`/`revoked` vocabulary. Revoked
  keys are intentionally refused; missing, ambiguous, and revoked signer states have distinct
  source-safe operation-event reasons. Zero active keys never implies revocation. Key windows are
  evaluated at decision issue time. A temporary `retired` wire alias exists only for the
  coordinated consumer-first Archive #147 cutover.
- Historical authority is immutable. Corrections add reconciled evidence; they do not silently
  rewrite accepted history.
- PostgreSQL is the durable runtime. In-memory components are test fixtures or explicitly ephemeral
  alternatives, never production evidence.
- Candidate-bound mutation idempotency is scoped by the trusted tenant stored on the candidate;
  callers continue to send an unchanged raw `Idempotency-Key`. Migration `028` fails closed on
  unattributable history and refuses a rollback that would collapse legitimate cross-tenant reuse.
  System-only outbox delivery runs retain a separate global namespace. Migration `030` adds an
  internal storage primary key for restore and default replica identity; the tenant/system partial
  unique indexes remain the business-identity authority.
- GitHub is the durable execution system. Search current issues and PRs before treating this summary
  as execution posture.

Repository hygiene is one active implementation PR, one checkout, and one feature branch locally
and remotely. Preserve unique work before deleting branches; classify unmerged durable truth as
must-merge, cherry-pick, superseded, delete, or active.

## Context Maintenance Rule

Update this file only when durable Idea architecture, ownership, commands, constraints, or task
routing changes. Keep it concise and current.

Do not add:

- issue-by-issue execution diaries;
- PR, run, SHA, branch, or issue-count snapshots;
- copied platform standards or skill procedures;
- speculative product plans;
- historical review commentary already preserved in GitHub.

Update `README.md` when the product front door or primary navigation changes. Update specialist
docs when their subject changes. Update repo-local `wiki/` source when operator or reader-facing
wiki truth changes, then use the platform publication workflow. Improve shared conventions in
`lotus-platform` rather than creating a competing Idea-only standard.

When editing headings or routes, run `make documentation-contract-gate` and perform a fresh-start
walkthrough from `AGENTS.md`: identify repository purpose, applicable standard and skill,
task-specific context, validation command, and completion evidence without undocumented knowledge.

## Cross-Links

Repository navigation:

- Product front door: `README.md`
- Product definition: `docs/LOTUS_IDEA_BLUEPRINT.md`
- Architecture index: `docs/architecture/README.md`
- RFC index: `docs/rfcs/README.md`
- Operations: `docs/runbooks/service-operations.md`
- Supported features: `wiki/Supported-Features.md`
- Contribution: `README.md#contributor-path`
- Wiki home: `wiki/Home.md`

Shared navigation, using `<workspace-root>` when sibling repositories are present:

- `<workspace-root>/lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
- `<workspace-root>/lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
- `<workspace-root>/lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
- `<workspace-root>/lotus-platform/context/LOTUS-SKILL-ROUTING-MAP.md`
- `<workspace-root>/lotus-platform/context/PROCEDURAL-MEMORY-INDEX.md`
- `<workspace-root>/lotus-platform/context/Repository-Engineering-Context-Contract.md`

Canonical remote fallback:

- [Lotus engineering context](https://github.com/sgajbi/lotus-platform/blob/main/context/LOTUS-ENGINEERING-CONTEXT.md)
- [Context reference map](https://github.com/sgajbi/lotus-platform/blob/main/context/CONTEXT-REFERENCE-MAP.md)
- [Repository context contract](https://github.com/sgajbi/lotus-platform/blob/main/context/Repository-Engineering-Context-Contract.md)
- [Procedural memory index](https://github.com/sgajbi/lotus-platform/blob/main/context/PROCEDURAL-MEMORY-INDEX.md)
