# RFC-0002 Slice 18: Documentation, Wiki, Support, And Agent Context

Status: Partially implemented - API certification, outbox readiness, implementation-proof, live source-proof contract, scheduled-worker source-contract and deployment-evidence contracts, durable repository proof contract, runtime telemetry test-execution contract, bounded Workbench read-path source contract, bounded Gateway/Workbench contract proof, bounded Gateway/Workbench discovery contract proof, digest-bound Advise/Manage route source contracts, bounded Report intake route source contract, bounded downstream outcome certification supporting proof, bounded outbox broker source-contract proof, bounded outbox platform-mesh event source-contract proof, digest-bound mesh policy source contract, AI lineage store proof, closed v3 Manage mandate, closed v2 Advise mandate/restriction, Advise missing-suitability, and Advise missing-risk-profile runtime evidence, receipt-bound Core portfolio-state, bond-maturity, and low-income cashflow runtime evidence, typed Advise mandate/restriction source-product proof, typed Advise missing risk-profile source-product proof, underperformance, allocation-drift, and drawdown-review API foundation truth, mandate/restriction and missing-benchmark policy foundation truth, client-demo process, downstream submission/reconciliation workload readiness truth, downstream contract documentation, and #379 merged-main execution-truth synchronization completed

## Outcome

Update durable documentation and agent guidance to match implemented truth.

## Current Implementation Evidence

This slice is partially implemented for API certification documentation truth and
durable operating-context enforcement:

Current documentation truth also records the concentration-risk caller-supplied
API foundation and shared signal API support module as implementation-backed
internal foundations only. They harden source-authority, authorization,
operation-event, and problem-detail behavior without adding a runtime
microservice boundary or promoting Risk methodology, trade advice, rebalance,
Workbench, data-mesh, client-publication, or supported-feature claims.
Documentation truth now also records the underperformance caller-supplied API
foundation over Lotus Performance active-return and benchmark-context evidence
as implementation-backed internal posture only. It preserves the boundary that
`lotus-idea` does not calculate returns, assign benchmarks, certify benchmark
methodology, recommend trades, create rebalance actions, publish to clients,
certify data mesh, prove Workbench behavior, or promote supported features.
Documentation truth now also records the drawdown-review caller-supplied API
foundation over Lotus Risk `DrawdownAnalyticsReport:v1` maximum-drawdown
evidence as implementation-backed internal posture only. It preserves the
boundary that `lotus-idea` does not calculate drawdown, approve Risk
methodology, recommend trades, create rebalance actions, certify data mesh,
prove Workbench behavior, or promote supported features.
Documentation truth now also records the allocation-drift / mandate-review
caller-supplied API foundation over Lotus Manage `PortfolioActionRegister:v1`
action-register and mandate-health source-ref posture as implementation-backed
internal posture only. It preserves the boundary that `lotus-idea` does not
fetch Manage sources, calculate drift, approve mandate compliance, create
rebalance actions, create orders, certify data mesh, prove Workbench behavior,
publish to clients, or promote supported features.
The opportunity archetype contract and `make opportunity-archetype-contract-gate`
now also require the allocation-drift API module, route, and integration test
as evidence refs so proof-readiness and demo-readiness docs cannot regress to
policy-only evidence.
`make signal-api-contract-gate` is blocking through `make lint` and the CI
contract self-check so future caller-supplied signal API slices cannot
reintroduce local signal-evaluation permission policy, local outcome mapping,
or unshared source-authority/error/event mechanics. It also requires signal
evaluation route metadata to compose the shared product-safe 400/403
`ProblemDetails` OpenAPI examples, preventing weak or inconsistent error-model
documentation across opportunity signal APIs.

1. `docs/operations/api-certification.md` now lists the full certified internal
   foundation endpoint inventory from
   `docs/operations/endpoint-certification-ledger.json`, including high-cash
   evaluation, high-cash persistence, candidate evidence replay, lifecycle
   transition, AI explanation evaluation, advisor queue, review action,
   feedback, conversion intent, conversion outcome, report evidence-pack
   request, data-mesh-readiness, outbox-delivery-readiness, and
   implementation-proof-readiness diagnostic endpoints.
2. The certification guide records each endpoint's current foundation scope,
   required capability, and unsupported boundary so future agents do not
   promote internal API foundations as business-supported product features.
3. The guide keeps baseline health and metadata endpoints separate with
   `baseline_certified` posture.
4. README, repository context, RFC index, and wiki source are updated in the
   same slice when documentation truth changes.
5. `docs/operations/ai-governance.md` now describes the certified internal AI
   evaluator API while preserving the unsupported boundary around provider
   execution, workflow-pack runtime, certified model-risk operations,
   Gateway/Workbench proof, and supported feature promotion. The source-safe
   AI lineage store proof clears only the aggregate lineage-store blocker and
   does not certify `lotus-ai` runtime execution or external AI support.
6. `make documentation-contract-gate` now runs through `make lint` and blocks
   removal, thinning, missing anchors, or placeholder erosion across the
   required README, repository context, enterprise standard, runbook, RFC
   index, quality, evidence, and wiki surfaces future implementation agents
   depend on. It also enforces a polished proof/readiness guide profile so
   operator-facing diagnostics use current-truth tables, proof and non-proof
   boundaries, blocker sections, response-shape tables, evidence references,
   and executable examples instead of raw text dumps.
7. Focused unit coverage proves the documentation contract gate passes current
   repository truth and fails missing, thin, missing-anchor, and placeholder
   documentation surfaces, plus unpolished operator diagnostics without
   required headings, tables, or command examples.
8. `docs/operations/implementation-proof-readiness.md`, README, repository
   context, demo claims, operations runbooks, and wiki source now describe the
   certified internal implementation-proof readiness diagnostic, including the
   outbox-delivery proof family, and preserve its no-external-publication and
   no-supported-feature-promotion boundaries.
9. `docs/operations/downstream-realization-readiness.md`, README, repository
   context, API certification docs, demo claims, operations runbooks, RFC index,
   quality scorecard, and wiki source now describe the certified internal
   downstream realization readiness diagnostic with a polished operator-facing
   structure: current truth, proof boundary, blockers, response shape, evidence,
   and executable example. Issue `#662` adds the
   `downstreamSubmissionCount` and `downstreamReconciliationRequiredCount`
   response fields and documents them as local handoff posture counts only; they do not prove downstream
   acceptance, materialization, rendering, archive creation, client publication,
   Gateway/Workbench behavior, or supported-feature promotion.
10. `docs/operations/implementation-proof-readiness.md` now uses the same
    polished operator-facing structure and is protected by the documentation
    contract gate, making implementation proof posture readable for business,
    engineering, operations, release, and demo reviewers without overclaiming
    live proof, certified live broker runtime, downstream delivery, or
    supported-feature promotion.
10. RFC-0002 issue-derived learning is now source-controlled through
    `contracts/implementation-proof/rfc0002-issue-learning-patterns.v1.json`
    and `make rfc0002-github-issue-learning-pattern-gate`. Every non-complete
    RFC-0002 execution issue must belong to a durable learning cluster with
    control refs, future-agent guidance, and no-claim boundaries, so repeated
    GitHub issue patterns are handled before the next slice rather than being
    kept in chat memory. Partial PR text can now be validated from exact
    `--title-file` and `--body-file` artifacts before PR creation, preventing
    saved PR Markdown from bypassing the local keep-open/auto-close wording
    gate. After `sgajbi/lotus-platform#653` / PR #654, that validation is also
    treated as a fail-closed precondition before `gh pr create`, `gh pr edit`,
    or a branch-head refresh; PowerShell runners must check `$LASTEXITCODE`
    immediately so unsafe PR text cannot be followed by a later GitHub mutation.
11. The caller-context contract gate now scans nested API route modules under
    `src/app/api/**`, not only top-level API files. This promotes the #686
    same-pattern lesson into deterministic enforcement: future route packages
    such as review queues, outbox, and data-lifecycle operations cannot bypass
    trusted-caller provenance forwarding or strict role-and-capability
    authorization by moving into a nested module.
12. `docs/demo/README.md`, `docs/demo/client-demo-operating-process.md`,
    `docs/demo/client-facing-lotus-idea-brief.md`,
    `docs/demo/client-demo-pack.template.md`, `docs/demo/demo-claims.md`, and
    `wiki/Demo-Readiness.md` now give client, sales, marketing, product,
    operations, and engineering reviewers a polished process for explaining
    what Lotus is doing, which claims are implementation-backed, and which
    boundaries remain blocked before any client-facing pack is marked
    client-ready.
12. README, repository context, `docs/operations/api-certification.md`,
    `docs/operations/persistence.md`, `docs/operations/observability.md`, RFC
    index, quality scorecard, and wiki source now describe the certified
    internal outbox delivery readiness diagnostic, bounded run-once operator
    action, and HTTP publisher adapter foundation while preserving the boundary
    that no certified live broker runtime, downstream delivery, platform mesh
    event certification, Gateway/Workbench proof, or supported-feature
    promotion exists.
13. README, repository context, `docs/operations/downstream-realization-readiness.md`,
    `docs/operations/api-certification.md`, quality guides, RFC evidence, and
    wiki source now describe the governed downstream contract plan and
    `make downstream-realization-contract-gate` while preserving the boundary
    that no downstream route existence, downstream execution, or
    supported-feature promotion exists.
13. README, repository context,
    `docs/operations/downstream-realization-readiness.md`,
    `docs/operations/implementation-proof-readiness.md`, quality scorecard,
    RFC evidence, and wiki source now describe bounded Advise proposal and
    Manage action route-proof generation, aggregate consumption, and
    `make downstream-route-source-contract-proof-gate`, while preserving the boundary
    that valid artifacts clear only route-foundation blockers and do not grant
    suitability, policy approval, mandate/rebalance authority, execution,
    client communication, or supported-feature promotion.
13. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/api-certification.md`, observability and persistence
    guides, quality scorecard, RFC evidence, and wiki source now describe the
    certified internal `POST /api/v1/source-ingestion/run-once` operator action
    while preserving the boundary that bounded live Core source-ingestion proof
    is proof evidence only, not live Core source certification, scheduler
    deployment or execution through that endpoint, certified long-running
    scheduled runtime, Gateway/Workbench proof, or supported-feature promotion.
14. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs,
    RFC evidence, and wiki source now describe the live source-proof artifact
    contract, aggregate source-safe `blockReasonCounts`, and
    `make source-ingestion-runtime-execution-contract-gate`, while preserving the
    boundary that only a family-valid and aggregate-current artifact clears the
    live-Core blocker and does not promote source ingestion as a supported
    feature.
15. README, repository context, `docs/operations/source-ingestion-run-once.md`,
    `docs/operations/api-certification.md`, `docs/operations/observability.md`,
    `docs/operations/implementation-proof-readiness.md`, demo claims, quality
    docs, RFC evidence, and wiki source now describe the scheduled worker
    entrypoint, Compose worker profile, separate source/deployment evidence
    contracts, and `make source-ingestion-scheduled-worker-check`, while
    preserving the boundary that static source evidence clears no blocker and
    matching deployment evidence clears only the scheduler deployment blocker.
16. README, repository context, `docs/operations/persistence.md`,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs,
    RFC evidence, and wiki source now describe the durable repository proof
    artifact contract and `make durable-repository-proof-contract-gate`, while
    preserving the boundary that a valid artifact clears only aggregate
    proof-readiness storage blockers and does not configure runtime storage,
    replace PostgreSQL runtime proof, certify production storage, or promote a
    supported feature.
17. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/mesh-readiness.md`, quality gate docs, RFC evidence, and
    wiki source now describe the runtime trust telemetry v2 `test_execution`
    contract and `make runtime-trust-telemetry-test-execution-contract-gate`.
    Valid current evidence adds provenance only, clears no blocker, and cannot
    certify durable runtime, the platform mesh, or supported-feature promotion.
18. README, repository context, API certification docs, demo claims, RFC
    evidence, and wiki source now describe `lotus-workbench` PR #391 as
    bounded read-only Workbench queue/detail rendering through Gateway, while
    preserving the boundary that full live proof, entitlement-denied proof,
    mutation affordances, downstream realization, data-product certification,
    and supported-feature promotion remain blocked.
19. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs, RFC
    evidence, and wiki source now describe the Workbench read-path v2
    `source_contract` artifact and
    `make workbench-read-path-source-contract-proof-gate`. The artifact adds
    provenance but clears no blocker, so
    `workbench_gateway_bff_consumption_proof_missing` remains until observed
    Gateway serving, Workbench consumption, entitlement, and browser evidence
    exists.
20. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs, RFC
    evidence, and wiki source now describe the Gateway/Workbench source-contract
    proof artifact and `make gateway-workbench-contract-proof-contract-gate`,
    while preserving the boundary that a valid artifact adds an evidence
    reference but clears no blocker. `gateway_workbench_proof_missing` remains
    for source-ingestion and outbox-delivery until observed runtime evidence
    exists, and the artifact does not certify Workbench product proof, browser proof,
    canonical demo runtime, data-product discovery, or supported features.
21. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, quality gate docs, RFC
    evidence, and wiki source now describe the Gateway/Workbench discovery
    contract proof artifact and
    `make gateway-workbench-discovery-contract-proof-contract-gate`. A valid
    artifact adds evidence to data-mesh and runtime trust telemetry test-execution evidence
    families but clears no blocker. The
    `gateway_workbench_discovery_proof_missing` blocker remains, and the
    artifact does not certify data-mesh products, activate producer products,
    certify full Workbench product behavior, or promote supported features.
21. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, RFC evidence, and
    wiki source now describe that the live implementation-proof readiness API
    consumes configured source-ingestion live, source-ingestion scheduled-worker,
    durable repository, runtime trust telemetry, and Workbench read-path source-contract proof
    artifact paths, records validated source-safe artifact refs in capability
    evidence, and preserves the boundary that only matching aggregate blockers
    are cleared and no certification or supported-feature promotion is implied.
21. README, repository context,
    `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/persistence.md`, quality gate docs, RFC evidence, and wiki
    source now describe the bounded outbox broker source-contract artifact, its
    zero-blocker-clearance scope, and its remaining broker-configuration/runtime,
    downstream-consumer, mesh-event, Gateway/Workbench, and supported-feature
    boundaries.
22. README, repository context,
    `docs/operations/implementation-proof-readiness.md`, RFC evidence, demo
    claims, and wiki source now describe the bounded outbox platform mesh event
    publication proof artifact, its default generated output, its aggregate
    blocker-clearance scope, and its remaining external broker publication,
    downstream delivery, Gateway/Workbench, client-ready publication, and
    supported-feature boundaries.
23. Repository context,
    `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/mesh-readiness.md`, service runbooks, quality gate docs,
    RFC evidence, and wiki source now describe the v3 platform catalog source
    contract, digest-bound authority, default generation, aggregate
    consumption, and unpromoted certification-candidate boundary for
    `IdeaCandidate:v1`. They preserve the boundary that missing sibling
    evidence is a non-proof artifact and no runtime publication, platform
    certification, active product declaration, Gateway/Workbench discovery
    certification, deployment, production certification, or supported-feature promotion is
    implied. The README data-mesh capability row now uses the bounded
    source-contract name and blocker posture. OpenAPI, migrations, database
    ownership, runtime topology, and supported-feature truth remain unchanged.
24. README, repository context,
    `docs/operations/implementation-proof-readiness.md`,
    `docs/operations/mesh-readiness.md`, quality gate docs, RFC evidence, and
    wiki source now describe default mesh policy source-contract generation and
    aggregate consumption while preserving the boundary that local
    SLO/access/evidence declarations clear no certification blocker and do not
    certify policy operation or the platform mesh, activate products, prove
    Gateway/Workbench discovery, or promote supported features.
25. `docs/demo/README.md` now gives client-demo teams a governed entry point
    for explaining what Lotus Idea is doing, choosing the right process
    artifact, tying claims to proof, and keeping unsupported autonomy,
    suitability, execution, publication, downstream materialization, and
    certified data-product claims out of client material.
26. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    service runbooks, quality gate docs, RFC evidence, demo claims, and wiki
    source now describe closed v3 Manage mandate runtime evidence while preserving the
    boundary that a valid artifact clears only the portfolio-scoped Manage
    source blocker plus source refs for source-owned mandate performance-health
    and mandate risk-health contexts, and does not prove Core portfolio state,
    data-mesh certification, Workbench support, client publication, supported
    features, rebalance authority, action authority, order creation, execution,
    or settlement. The documentation names Manage `#620` as the producer-owned
    trust-metadata dependency and requires Idea to fail closed rather than
    synthesize source authority.
27. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    RFC evidence, demo claims, and wiki source now describe bounded low-income
    Core cashflow live proof while preserving the boundary that a valid
    artifact clears only the low-income Core cashflow source blocker and does
    not certify client income needs, funding advice, treasury instruction,
    suitability, planning objectives, data mesh, Workbench behavior, client
    publication, or supported-feature promotion.
28. README, repository context, `docs/operations/implementation-proof-readiness.md`,
    RFC evidence, demo claims, and wiki source now describe bounded Core
    portfolio-state live proof while preserving the boundary that a valid
    artifact clears only the allocation-drift Core portfolio-state source-ref
    blocker and does not prove Manage action-register posture, mandate
    performance health, mandate risk health, data mesh, Workbench behavior,
    client publication, rebalance authority, action authority, order execution,
    or supported-feature promotion.
29. README, repository context, API certification docs, RFC evidence, demo
    claims, and wiki source now describe the bounded bond-maturity /
    reinvestment policy, caller-supplied API foundation, and fail-closed Core
    maturity-summary source-adapter contract while preserving the boundary that no
    data-mesh certification, Workbench product proof, client publication,
    product recommendation, reinvestment advice, maturity schedule authority,
    order execution, or supported-feature promotion exists.
30. The allocation-drift opportunity archetype evidence contract now pins the
    caller-supplied API module, route, and integration test in addition to
    Manage/Core source-proof evidence, preserving the boundary that this is
    API evidence only and not Manage source fetch, drift calculation, mandate
    approval, rebalance/action/order authority, data-mesh certification,
    Workbench proof, client publication, or supported-feature promotion.
31. The high-volatility / drawdown opportunity archetype evidence contract now
    pins the high-volatility and drawdown caller-supplied API modules, routes,
    and integration tests in addition to Risk source-proof evidence,
    preserving the boundary that this is API evidence only and not Risk source
    fetch, volatility or drawdown calculation, Risk methodology approval,
    rebalance/action/order authority, data-mesh certification, Workbench proof,
    client publication, or supported-feature promotion.
32. The opportunity archetype evidence contract and contract gate now enforce
    API-evidence parity for every implemented caller-supplied signal API
    recorded in the archetype contract. This pins concentration,
    underperformance, allocation drift, bond maturity, high volatility,
    drawdown, missing suitability, missing risk profile, mandate/restriction,
    low income, and missing benchmark API modules, routes, and integration
    tests without promoting any of those foundations to supported features.
33. The repo-local wiki now includes dedicated `API-Surface` and
    `Troubleshooting` pages, both linked from `Home` and `_Sidebar`, so API
    readers and operators have first-stop maps before entering the longer
    operations and validation runbooks. The pages summarize current
    implementation-backed API posture, problem-response expectations, wiki
    publication handling, and first-response diagnostics without promoting a
    supported feature.
34. Issue `#437` synchronizes the Report intake route artifact as v2
    `source_contract` evidence across repository context, implementation-proof
    and downstream-readiness guides, RFC evidence, quality truth, demo claims,
    and wiki source. Static sibling declarations add provenance but clear no
    blocker; `lotus_report_live_intake_route_proof_missing` remains until the
    owning Report runtime supplies machine-verifiable serving, authorization,
    tenant-isolation, and request-execution evidence.
35. Issue `#438` synchronized the Report materialization artifact as
    `source_contract` evidence across code, CLI and Make vocabulary,
    repository context, evidence inventory, implementation-proof and
    downstream-readiness guides, RFC truth, quality/demo claims, and wiki
    source. The v3 artifact now links `sgajbi/lotus-report#152` as the closed
    Report owner proof. It clears no blocker and preserves materialization execution,
    rendered-output, archive-record, retention/legal-hold, publication,
    certification, and supported-feature boundaries.
36. Issue `#456` synchronizes source-ingestion v2 `runtime_execution` truth
    across the run-once and implementation-proof runbooks, Slice 09/17,
    quality gates, repository context, evidence/review ledgers, and authored
    wiki. The artifact is implementation-backed by exact Core source refs and
    durable persistence receipts; it preserves scheduler, mesh,
    Gateway/Workbench, production, and supported-feature boundaries.
37. Issue `#459` synchronizes signed AI attestation declarations as closed v2
    `source_contract` evidence across the AI governance runbook, Slice 09/15/17,
    quality gates, repository context, evidence/review ledgers, and authored
    wiki. Separate digest-bound producer and consumer authority collections make
    full and consumer-only validation scopes explicit. Both clear no blocker;
    live provider/model execution, model-risk approval, deployment, production,
    Workbench, publication, and promotion remain unproven.

The missing-suitability operator and engineering material now describes the
closed v2 receipt contract, one-fetch generator, truthful no-opportunity
qualification, preserved authority boundaries, and prohibited flat v1 paths.
The existing environment variable and Make target remain stable, but do not
accept legacy artifacts.

The missing-risk-profile material now records the same receipt-bound execution
standard through its capability-owned contract while retaining independent
risk-profile posture semantics. Shared Advise request and workflow validation
removes duplicate producer qualification; a one-fetch generator preserves the
exact source result, candidate and truthful no-opportunity executions qualify,
and retired flat v1 paths are prohibited.

Typed Advise source-product material now uses one capability-owned
`advise_source_product_evidence/` package with independent
mandate/restriction and missing-risk-profile profiles. Both are closed v2
`source_contract` evidence over current producer declaration and trust
telemetry files, preserve blocked producer posture, and reject authority
inflation. The aggregate artifact registry makes CLI, application, evidence
class, tracking issue, and documentation inventory drift a blocking
documentation-contract failure. Issue `#508` now records the locally
implemented scheduled-worker source-contract and deployment-evidence boundary;
an actual environment deployment receipt remains absent rather than being
hidden by this documentation slice.

Issue `#513` records the registry-effect enforcement boundary in operator,
architecture, RFC, repository-context, review-ledger, and wiki truth. The
documentation gate rejects duplicate payload and reference arguments, while
application tests mutate effects and prove that supporting evidence cannot be
consumed as blocker-clearing evidence. README, API/OpenAPI, migration,
database, seed, and supported-feature truth are unchanged because this slice
changes internal proof governance rather than product support.

Issue `#701` adds a blueprint scope coverage contract and blocking
`make blueprint-scope-coverage-gate`. The contract parses
`docs/LOTUS_IDEA_BLUEPRINT.md` and maps every Idea-owned capability, non-owned
authority boundary, and target opportunity family to RFC-0002 slice IDs,
GitHub issues, evidence references, and the `foundation_only_not_promoted`
supported-feature posture. This makes remaining RFC-0002 execution durable in
GitHub and repo-owned source while preserving the boundary that local/dev auth,
source-authoritative portfolio/performance/risk/suitability/report/archive/AI
infrastructure, downstream acceptance, Workbench proof, platform mesh
certification, client-ready publication, and supported-feature promotion remain
blocked until their owning evidence exists.

The 2026-07-19 cross-repository issue audit verified that the current
blueprint/proof contract references have owner-repo tracking across Advise, AI,
Archive, Core, Gateway, Manage, Performance, Platform, Render, Report, Risk, and
Workbench. No additional product dependency issue was required by the audited
contract state. `sgajbi/lotus-platform#602` now tracks the reusable platform
auditor and skill hook for future RFC issue-coverage checks, including issue
existence, RFC/slice labels, open/closed and blocked state, priority, owner
repository, and duplicate/superseded posture.

Issue `#681` now adds
`contracts/implementation-proof/rfc0002-github-issue-execution-ledger.v1.json`
and `make rfc0002-github-issue-execution-ledger-gate` as the durable
RFC-0002 issue execution ledger. The ledger covers the current RFC execution
issues and now reconciles every GitHub issue carrying the `rfc/RFC-0002` label,
including legacy blocker issues `#340`, `#343`, `#344`, `#345`, `#375`,
`#379`, `#380`, and closed OpenAPI certification issue `#542` alongside the
slice execution set `#673` through `#704` where applicable. It fails closed when
an open or partial issue allows PR auto-close, lacks a `Keep #<issue> open`
instruction, duplicates or omits a current execution issue, or describes closed
truth with open-issue wording. This prevents future source-contract or
evidence-consumption PRs from using `Closes`, `Fixes`, or `Resolves` for work
that still lacks live runtime, downstream, publication, support, or
supported-feature evidence.

Slice 18 also adds `make rfc0002-github-issue-pr-text-gate`, backed by
`scripts/github_issue_pr_text_gate.py`, as the pull-request title/body
companion for keep-open RFC issue posture. The target passes offline when no PR
text is supplied. PR Merge Gate supplies the GitHub pull-request title and body,
and the gate fails early when text says `Keep #<open issue> open` while also
using standalone GitHub auto-close keywords such as `fixes`, `closes`, or
`resolves`. Partial RFC PRs must use neutral verbs such as `updates`, `records`,
`reconciles`, or `addresses` until the complete evidence class is merged and
QA-backed closure is intended. Negated closure references such as `does not
close #681` remain unsafe because GitHub still sees the closing keyword and
issue reference; describe non-completion without an issue reference instead.
When the gate is run locally or in an agent script, it is a fail-closed
precondition before `gh pr create`, `gh pr edit`, or any branch-head refresh
intended to prove corrected PR text. PowerShell flows must check
`$LASTEXITCODE` immediately after the gate and exit on failure; do not group the
gate with a later GitHub mutation in a way that can continue after unsafe
keep-open wording is rejected. This consumes the platform-wide
execution-control fix tracked by `sgajbi/lotus-platform#653` and merged in PR
#654.

The same Slice 18 learning loop now adds
`make rfc0002-github-issue-execution-state-audit`, backed by
`scripts/github_issue_execution_state_audit.py`. The audit compares the ledger
with current GitHub issue state and lifecycle labels, so reopened issues,
blocked issues, in-progress issues, open tracker issues,
merged-main-QA-pending issues, and closed-complete issues cannot drift silently
away from the durable execution ledger. It also fails when a GitHub issue is
labeled `rfc/RFC-0002` but missing from the ledger, or when a ledger issue lacks
the RFC label in GitHub. Parent `open_tracker` issues now require
`status/tracker`; the #681 anchor carries the current execution label, such as
`status/pr-open` while a Slice 18 synchronization PR is open and
`status/in-progress` between PRs. Future partial Slice 18 PRs must keep the
correct lifecycle label and use `Keep #681 open`
until full RFC documentation, wiki, support, and agent context closure is
complete.

Slice 18 now also adds `make rfc0002-cross-repo-issue-posture`, backed by
`scripts/cross_repo_issue_posture.py`, so cross-repository RFC-0002
status is generated from live GitHub state instead of reconstructed from chat,
assignee filters, or one-off shell snippets. The command checks the governed
RFC-0002 coordination repo set across Idea, Advise, AI, Platform, Gateway,
Workbench, Manage, Risk, and Performance; reports total open issues, open and
closed RFC-0002 counts, open status-label posture, and attention issues such as
`status/in-progress`, `status/blocked`, `status/pr-open`, `status/fixed-local`,
or `status/merged-main`. Pending final-closure and post-completion issues must
not carry `status/ready` while prerequisite blockers remain open. It is
coordination evidence only: it does not clear
blockers, promote supported features, prove implementation, replace repo-local
ledgers, or substitute for exact-main validation.

PR #765 merged that cross-repo posture command to main at
`3ab78c4e9ba23b08eec5396f0641acf21c98f74a`; Main Releasability `30411606383`
passed for the exact SHA; repo-authored wiki publication completed at
`lotus-idea.wiki` commit `0aea688` with strict `DiffCount 0`; and branch
hygiene verified the PR branch absent remotely and locally after
patch-equivalence cleanup. The source ledger now pins this #681 evidence and
the gate requires those identifiers so the partial Slice 18 coordination work
cannot regress into chat-only memory. #681 remains open: this tranche does not
clear any RFC-0002 blocker, promote supported features, prove product support,
or complete the full documentation/wiki/support/context closure requirement.

The same #681 source ledger now rolls forward through the later Slice 18
governance tranches: PR #767 made pending final-closure and post-completion
issue sections explicit, PR #768 added keep-open PR text enforcement, PR #769
synchronized Manage temporal receipt identity consumption after
`sgajbi/lotus-manage#620`, and PR #770 reconciled historical Manage #620 closure
truth after downstream evidence was posted. PR #772 synchronized platform
vulnerability-exception register linkage from `sgajbi/lotus-platform#596`, PR
#775 synchronized #690 merged-main evidence, and PR #776 synchronized #690
final QA closure truth. PR #777 synchronized #681 evidence after #690 QA closure.
PR #787 then corrected cross-repo RFC-0002 posture coverage so Core, Report,
Render, and Archive dependencies are included in the default live posture.
The latest rollup checkpoint is main
`39a480ddf115649acc3f6793a69596d4e5912bc8`, Main Releasability `30451401411`,
Push on main `30451387946`, wiki commit `d06f46b`, strict wiki parity, no unmerged
local or remote feature branch, live cross-repo RFC-0002 posture over the
governed 13-repository owner/dependency set of 77 tracked issues, 40 closed,
and 37 open. PR #789 then source-controlled blocker actionability on main
`01ae36ba89f975508bde47b4361190ef5c083597` with Main Releasability
`30456433618`, Main CodeQL/Push run `30456425304`, wiki commit `c926899`,
strict wiki parity, branch cleanup, and a classified blocked posture of 26
blocked issues, 0 app-actionable blocked issues, 5 Core dependencies, and 21
external/protected-evidence blockers. PR #790 synchronized that evidence into
source-controlled execution truth on main
`f23c72d7d95d1676b8f673f538a9336e4b704fbc` with Main Releasability
`30458163573`, Main CodeQL/Push run `30458146092`, wiki commit `bbd9e2f`,
strict wiki parity, and branch cleanup. PR #791 synchronized PR #790 evidence
into source-controlled execution truth on main
`65e11890aaddb70fea4cf9d80e836ce1625a6c44` with Main Releasability
`30460122600`, Main CodeQL `30460101418`, wiki commit
`2453c3006722ee40e48762d884581fb6b3893bbe`, strict wiki parity, and branch
cleanup. Workbench PR #505 narrowed the BFF principal-boundary blocker on
Workbench main `1b4afb92f4c810c99921fc26e451b04bca731e28`; Pull Request Merge
Gate `30464152669`, branch head `c4add59871bc3f0e78dc6602c8857c5e141e6367`,
Main Releasability `30465110912`, Workbench wiki commit `3b4f78f`, strict wiki
parity, and branch cleanup passed. Platform PR #639 hardened stale PR-text
payload guidance on platform main `641aabe9f303a178f3a4e489c52b3d789d8339d3`
with Main Releasability `30475978275` passing. Platform PR #654 then hardened
the platform-owned issue/PR skills and PR loop playbook so PR-text gates run
fail closed before PR creation, PR edits, or branch-head refreshes; platform
Main Releasability `31256159863` passed on main
`e0ad0596afcda7bc8cf33909f8ece04b1d944647`. PR #801 then synchronized final
#797/#681 evidence on Idea main
`95c47d27f45e09369f6b709588fa2de1a1f8700b`; exact-main Main Releasability
`30487277416` passed. PR #802 then synchronized current RFC-0002 posture truth
on Idea main `7df8fbff1fbab3acb5568a8e95eb7d5d58c8dcdd`; exact-main Main
Releasability `30488990343` passed and wiki publication reached `ec05a36`
with strict `DiffCount 0`. PR #803 then synchronized PR #802 evidence truth on
Idea main `31e5157de796e0accd0f23d3a80102ecd0871c71`; exact-main Main
Releasability `30490458612` passed and wiki publication reached `3743f01`
with strict `DiffCount 0`. PR #804 then synchronized PR #803 evidence truth on
Idea main `615e3ba848af551801c897dd9b0a52f964801da0`; exact-main Main
Releasability `30491918891` passed and wiki publication reached `05026e8`
with strict `DiffCount 0`. PR #806 merged the Slice 15 runtime-image hardening
remediation on Idea main `a92144773d1b74bcf19e15396215dd988b5dc0af`;
exact-main Main Releasability `30496796215` passed and strict wiki parity
remained `DiffCount 0`. PR #808 then synchronized #807 source truth on exact
Idea main
`f577efcc14d51208375f3fde87284ac98f8ebb7a`; Main Releasability `30498306031`
passed, strict wiki parity remained `DiffCount 0`, and final QA closed #807 for
the repository-owned runtime-image remediation only. PR #809 then synchronized
the final #807 closure truth on Idea main
`c340daa01b41097410bbc8a802d9a8d1f9f24135`; exact-main Main Releasability
`30499444726` passed, including lint/typecheck/security, unit, integration,
e2e, PostgreSQL runtime proof, combined coverage, Docker build, runtime smoke,
image scan, release identity/license evidence binding, and CI signal evidence.
At the PR #809 snapshot, the then-current Idea RFC-0002 ledger posture was 54
tracked issues, 25 open, and 29 closed. The then-current governed cross-repo
posture was 93 label-backed tracked issues, 56 closed, and 37 open across 13
repositories after #814 moved from PR-open to Core-blocked posture. After fresh
canonical validation reopened `sgajbi/lotus-core#836` as
`status/in-progress`, `sgajbi/lotus-core#840` remained `status/in-progress`,
and `sgajbi/lotus-manage#626` closed with `status/merged-main`, current open
posture is 27 blocked issues, 2 in-progress issues, and 8 tracker issues. The blocked
posture remains 27 blocked issues, 0 app-actionable blocked issues, 4 Core
dependencies, and 23
external/protected-evidence blockers. #683 and #684 are
not ready implementation issues while prerequisite RFC blockers remain open;
their richer pending semantics remain in the execution ledger and summary. This
evidence still preserves `sgajbi/lotus-manage#624`
and the other blocked production/certification dependencies; it is not Slice 18
completion evidence and does not certify
production vulnerability posture or production IdP/session/token-claims
principal proof. #814 also remains open until Core #836 is resolved and fresh
full canonical validation produces mainline capacity-seed evidence; it does not
implement production authentication or promote supported features.

The cross-repo issue posture count is label-backed by `rfc/RFC-0002`. Historical
title-only RFC-0002 references are reported separately and excluded from the
governed count unless they are deliberately labeled and ledgered; this prevents
ad hoc title searches from overstating or understating durable RFC execution
truth.

PR #810 then synchronized PR #809 main evidence and Core/Workbench handoff
posture to Idea main `fe7f0efac9fca86a3e19302e8b8436e8941f3d0c`;
exact-main Main Releasability `30500588217` passed, including workflow lint,
lint/typecheck/security, unit, integration, e2e, PostgreSQL runtime proof,
combined coverage, Docker/release validation, image scan, commit-tagged image
publish and digest proof, published-digest runtime proof, image signing,
provenance/SBOM attestations, release metadata, image identity binding, release
license evidence binding, and CI signal evidence. Repo-authored wiki
publication reached `lotus-idea.wiki` commit `f0f9293` with strict
`DiffCount 0`. The historical durable handoff evidence was recorded on
`sgajbi/lotus-core#836`, `sgajbi/lotus-core#840`,
`sgajbi/lotus-workbench#500`, #685, and #686. Workbench #500 is now closed
with `status/merged-main` after Workbench PR #501 and Idea PR #837; current
open proof posture is anchored by `sgajbi/lotus-core#882`,
`sgajbi/lotus-core#885`, #814, #685, and #686. `sgajbi/lotus-manage#626`
records the closed Manage tax-lot identity fix merged by PR #627 on Manage main
`5ba2757c1235ce3e28c630afd44257327c91edf3` with Main Releasability
`30536615979` passing and branch cleanup complete. The open blocker is now
canonical Core/Platform command-center seed runtime evidence, not hidden Manage
app-code work.

This Slice 18 synchronization also carries the platform vulnerability-exception
register lesson from `sgajbi/lotus-platform#596` into Idea's repository truth.
The dependency vulnerability posture contract now records the platform schema
and report-only validator, and the gate rejects active exceptions that lack a
`VX-*` platform register identity, exact platform schema ref, affected
version/digest, exposure and exploitability assessments, planned fix path, or
matching active/no-active register status. This is documentation, context, and
contract synchronization only. It keeps #681 open, adds no supported feature,
and does not certify production vulnerability posture or replace exact-main
release scanning, SBOM, signing, provenance, digest, release-manifest, wiki,
and branch-hygiene evidence.

The #379 downstream outcome certification supporting-proof tranche is now
synchronized across repo context,
`docs/operations/downstream-realization-readiness.md`,
`wiki/Validation-and-CI.md`, Slice 12, Slice 13, and the RFC-0002 execution
ledger. PR #742 merged the aggregate proof to main at
`0a4e7a55495cb3b979672f52b08ba2630603cf94`; Main Releasability run
`30323405962` passed; wiki publication completed at `lotus-idea.wiki` commit
`ce29814` with strict `DiffCount 0`; PR #743 reconciled the execution ledger at
current main `8ccee32d9a25fb6c47c723e105e2c48d1c4b3c70`, with Main
Releasability run `30324178801` passing. Issue #379 remains open in
`status/blocked`: this evidence clears only the source-safe aggregate proof
composition and owner-app local implementation tranche. Production/certification
evidence, trusted IdP caller context, and Archive legal/privacy lifecycle
conformance remain open after Idea consumes the
`sgajbi/lotus-manage#620` temporal receipt identity tranche. Report-owned
retention-policy conformance is closed through `sgajbi/lotus-report#136` on
lotus-report main `f8d220d74dd21d0c51cc310c117264c96b879d62` with Main
Releasability run `30898036781` and current-main focused QA. Remaining blockers
are `sgajbi/lotus-manage#624` and `sgajbi/lotus-archive#55`; no suitability,
rebalance/execution, report
rendering, archive authority, client publication, production identity,
supported-feature promotion, legal/privacy approval, or full downstream outcome
certification closure is claimed.

The #340/#380 posture reconciliation is now synchronized across the RFC-0002
execution ledger, `docs/operations/implementation-proof-readiness.md`,
`wiki/Validation-and-CI.md`, `wiki/Supported-Features.md`, and repository
context. PR #745 reconciled #340 to `open_merged_main_qa_pending` at
`eeabfc683f595b4cbc9ffb5aa0aa51c3e5622903`; Main Releasability
`30326431318` and CodeQL `30326422515` passed. Final QA closed #340 on
2026-07-29 after Idea-side attestation/governance/lineage/API proof and
producer-side `lotus-ai` workflow-run attestation proof passed against current
mainline evidence. PR #746 corrected stale ready
posture for #380 and reconciled it to `open_blocked` at
`6f8875dc6784dd17975e6700c09b9ff71d66fb8b`; Main Releasability
`30327202465` and CodeQL `30327193673` passed. After PR #798 merged the
incident-response operating model, wiki publication `0d075af` reached strict
parity, PR #799 synchronized #797 merge evidence, and PR #800 moved #797 to
closed source truth on exact main
`4ab19e3a85d4b00fc3daeb5d63d2ce1f98a43740` with Main Releasability
`30485290281`, PR Merge Gate, Feature Lane, and CodeQL passing, and PR #806
merged the Slice 15 runtime-image hardening remediation to exact main
`a92144773d1b74bcf19e15396215dd988b5dc0af` with Main Releasability
`30496796215` passing, and PR #808 synchronized #807 source truth to exact main
`f577efcc14d51208375f3fde87284ac98f8ebb7a` with Main Releasability
`30498306031` passing, and PR #809 synchronized #807 final QA closure truth to
exact main `c340daa01b41097410bbc8a802d9a8d1f9f24135` with Main Releasability
`30499444726` passing. PR #810 synchronized PR #809 main evidence and
Core/Workbench handoff posture to exact main
`fe7f0efac9fca86a3e19302e8b8436e8941f3d0c` with Main Releasability
`30500588217` passing and repo-authored wiki publication `f0f9293` at strict
`DiffCount 0`; after the PR #828/#829 evidence-sync cycle, current source truth
records 54 tracked RFC-0002 issues, 29 closed complete, 25 open, no
`open_merged_main_qa_pending`, 1 `open_in_progress`, no `open_pr_raised`, and
14 `open_blocked` issues. #681 is active after PR #829 reached exact main
`b9793a6e119a7510cd8aa881ad37abefe3612a81`, and #814 is currently blocked by
Core in-window aggregation readiness issue `sgajbi/lotus-core#873`. #807 is
closed complete for repository-owned runtime-image remediation only; no
production vulnerability certification, registry promotion, protected
deployment, supported-feature promotion, or full Slice 15 closure is claimed.
#379 is `open_blocked`, not
QA-pending because its
owner-app local implementation dependencies are merged and Report-owned
retention-policy conformance is closed, but production/certification,
trusted-identity, and Archive legal/privacy lifecycle evidence remains open.
#685 is `open_blocked`, not QA-pending: the
2026-07-29 governed Workbench startup attempt via `npm run live:stack:up`
restored core portfolio readiness for `PB_SG_GLOBAL_BAL_001`; valuation and
aggregation jobs drained to zero, positions/cash data quality reached
`COMPLETE`, and analytics/return-path dates reached `2026-04-10`. The run then
failed in the DPM command-center action-register seed because
`POST http://manage.dev.lotus/api/v1/rebalance/simulate` returned HTTP 424 with
`DPM_CORE_CONTEXT_INCOMPLETE`. The then-current blocker was tracked in
`sgajbi/lotus-core#840`, with refreshed 2026-07-30 owner handoff evidence on
`sgajbi/lotus-core#836`, `sgajbi/lotus-core#840`,
`sgajbi/lotus-workbench#500`, #685, and #686. Workbench #500 is now closed;
Core `sgajbi/lotus-core#882` and `sgajbi/lotus-core#885` closed on
2026-08-09, so current canonical proof now requires fresh
Gateway/BFF-backed Workbench queue/detail/action runtime evidence before #685,
#686, or #814 can move to QA closure.
PR #819 synchronized the #380 Core-blocker reference to then-current `sgajbi/lotus-core#856`
on Idea main `3b2cc0bb4472a158cb4617b277276244c0e4a22b`; exact-main Main
Releasability `30555536256` and CodeQL `30555528134` passed for that SHA.
Wiki source did not change in PR #819, strict parity stayed `DiffCount 0`, and
remote/local branch cleanup completed after patch-equivalence proof. This is
Slice 18 source-truth synchronization only: #681 and #380 stay open. Fresh
canonical validation after Core PR #858 reopened Core #836 because positions
data quality remained `UNKNOWN` despite ready/current Core diagnostics, and
supported-feature promotion remains unclaimed.

PR #824 then synchronized that Core #836 canonical QA-failure posture through
Idea main `f4904af523cb2e54cd18db0c5eb71c8725998df8`. Exact-main Main
Releasability `30620242970` and CodeQL `30620237795` passed for that SHA,
including release-image build/smoke/scan, image push, digest inspection,
signing, provenance/SBOM attestations, release manifest, and release evidence
upload. Repo-authored wiki source was published to `lotus-idea.wiki` commit
`5e63705` with strict `DiffCount 0`, and local/remote branch cleanup completed
with no unmerged remote branches. At that synchronized snapshot, the
then-current governed posture was 93 label-backed RFC-0002 issues, 56 closed,
and 37 open: 27 blocked, 2 in-progress, 8 tracker, 0 app-actionable blocked, 4
Core dependencies, and 23 external/protected evidence blockers. This is Slice
18 source-truth synchronization only; #681 and the remaining blocker issues
stay open.

PR #825 then synchronized PR #824 merged-main evidence through Idea main
`8e76736148e9cd2078a1adfd692884da7d78a95f`. PR Merge Gate `30621485539`,
post-merge Main Releasability `30621899968`, and post-merge CodeQL
`30621893764` passed. Repo-authored wiki source was published to
`lotus-idea.wiki` commit `eefd44a` with strict `DiffCount 0`; the remote PR
branch was deleted, the local feature branch was deleted after exact
tree-equivalence verification, the local branch list contained only `main`, and
no unmerged remote branches remained. The then-current governed posture was 93
label-backed RFC-0002 issues, 56 closed, and 37 open: 27 blocked, 2
in-progress, 8 tracker, 0 app-actionable blocked, 4 Core dependencies, and 23
external/protected evidence blockers. This was Slice 18 source-truth
synchronization only; #681 remained open and no blocker issue, supported
feature, client-publication claim, production identity/session-token authority,
canonical browser proof, or final RFC-0002 closure was promoted.

PR #826 then synchronized that PR #825 evidence through Idea main
`6fd8159495ca3a7294ade2d819c80ea6aaa350fd`. PR Merge Gate `30623781720`,
Feature Lane `30623778382`, CodeQL `30624121200`, and exact-main Main
Releasability `30624125739` passed. Repo-authored wiki source was published to
`lotus-idea.wiki` commit `272f7cf` with strict `DiffCount 0`; remote branch
cleanup completed, the local feature branch was absent after fetch/prune, the
local branch list contained only `main`, and no unmerged remote branches
remained. #681 returned to `open_in_progress` because Slice 18 remains a
continuing synchronization issue. This is merged-main evidence synchronization
only; the remaining RFC-0002 blockers, supported-feature promotion,
client-publication, production identity/session-token authority, canonical
browser proof, and final RFC-0002 closure remain open.

PR #828 then synchronized the Render/Core validation handoff through Idea main
`82884cf8953ebcd2a33d42a6f1159ec9f4328421`. Render PR #69 had merged the local
host allowlist fix to Render main `034b085f0e208f1a322eaaea12edb2f00f009ba6`
with Main Releasability `30642955519` and wiki publication `ededc37` at strict
`DiffCount 0`. The follow-on canonical Workbench validation advanced beyond
Render readiness, Core instrument persistence, valuation queue drain, and
positions/cash data-quality convergence, then blocked in Core on two in-window
unleased `PENDING` aggregation jobs for `PB_SG_GLOBAL_BAL_001`; the current
Core blocker is `sgajbi/lotus-core#873`. PR #828 reached exact Idea main after
PR Merge Gate `30646651549`, Feature Lane `30646648800`, CodeQL `91209723012`,
Queue Auto Merge `30646652878`, and Main Releasability `30647077649` passed. No
repo-authored wiki source changed and branch cleanup completed.

PR #829 then synchronized PR #828 merged-main evidence and the continuing #681
execution posture through Idea main `b9793a6e119a7510cd8aa881ad37abefe3612a81`.
Exact-main Main Releasability `30648791483` passed for that SHA, including
workflow lint, lint/typecheck/security, PostgreSQL runtime proof, unit,
integration, e2e, combined coverage, Docker build validation, and CI signal
evidence. Repo-authored wiki source did not change in PR #829, so no wiki
publication was required. Local `main` tracked `origin/main`, no open PRs
remained, no extra worktrees or feature branches remained, and no remote
branches were unmerged into `origin/main`. This is source-truth synchronization
only; #681 stays open and RFC-0002 still does not claim Core readiness,
canonical browser proof, client publication, supported-feature promotion,
production identity/session-token authority, protected runtime certification,
or final closure.

PR #830 then synchronized PR #829 evidence through Idea main
`8a8cd5431e725267a1a0d39e6e1742fe8e7c5721`; exact-main Main Releasability
`30650553039` passed and no repo-authored wiki source changed. PR #831 then
merged the file-backed PR title/body validation guard to Idea main
`17e64208c6d0614fdd07f95755453978813a7612`; replacement exact-main Main
Releasability `30652543470` passed, and the earlier duplicate-dispatch runs
`30652453290` and `30652462394` are explicitly non-certifying cancelled runs.
The 2026-08-02 live blocker and CI audit reports 108 label-backed RFC-0002
issues across 13 repositories, with 71 closed and 37 open after QA closure of
the already merged-main Advise, Gateway, Workbench, and AI dependency issues.
The open set is 28 blocked, no PR-open issues, 1 in-progress issue (#681), 8
tracker, and no open merged-main/merged-to-main QA-pending issues. The
blocked-actionability classifier remains at 0 app-actionable blocked issues,
split into 5 Core dependencies and 23 external/protected evidence blockers.
Idea PR #838 synchronized PR #837 exact-main evidence to main
`2c2d35667643ad5efae83924475574ab6c16be03`, passed Main Releasability
`30723235065`, and published wiki source to `lotus-idea.wiki` commit
`ee15dc3`. Idea PR #839 synchronized PR #838 merged-main evidence to main
`71867084c2832d053342db048557e03720a3773a`, passed Main Releasability
`30724145516`, published wiki source to `lotus-idea.wiki` commit `c2258e6`,
completed branch cleanup, and returned #681 to `status/in-progress` because
Slice 18 remains a continuing synchronization issue.
Idea PR #842 synchronized PR #841 evidence to main
`4e2dd20c3f1b7f17a30eda016e79c62e631b2a2f`, passed exact-main Main
Releasability `30727100273` and CodeQL `30727098069`, and had no wiki-source
change. Idea PR #843 merged the posture-snapshot documentation guard to main
`2ed353b0394a625dd212b437fb93c0d5d4c02a89`, passed exact-main Main
Releasability `30728039165` and CodeQL `30728037050`, published wiki source to
`lotus-idea.wiki` commit `87dd4e4` with strict DiffCount 0, and completed
branch cleanup.
Idea PR #844 synchronized PR #843 evidence to main
`c21deeb55dcb1d46395c02c95053ab6149ef6ad6`, passed exact-main Main
Releasability `30728738511` and CodeQL `30728733346`, published wiki source to
`lotus-idea.wiki` commit `b47cbcb` with strict DiffCount 0, recorded final
#681 GitHub evidence in the
[#681 PR #844 final evidence comment](https://github.com/sgajbi/lotus-idea/issues/681#issuecomment-5154685336),
and completed branch cleanup. This keeps #681 open because remaining RFC-0002
blockers still require Core #882/#885, production identity/session-token,
protected runtime, provider, legal, client-publication, support, supported
feature, and final closure evidence.
Evidence-only Slice 18 synchronization PRs now have a non-recursive evidence
boundary: the PR's own post-merge proof is durable when recorded as a final
#681 GitHub issue comment with PR URL, merged main SHA, exact-main Main
Releasability run, wiki publication or no-wiki-change decision, and branch
hygiene. PR #845 is the current example in the
[#681 PR #845 final evidence comment](https://github.com/sgajbi/lotus-idea/issues/681#issuecomment-5154811626).
This policy prevents evidence-sync churn while preserving the stricter rule
that implementation truth, blocker state, support posture, wiki source,
context, or policy changes still require source-controlled updates.
Platform PR `sgajbi/lotus-platform#646` merged the platform-owned keep-open PR
guidance hardening to main `c041a7e13358feb322b8e92b3827f3ed2a834b43` and
passed exact-main Main Releasability run `30731910564`. The reusable
`gh-issue-fix-qa-loop`, `lotus-pr-premerge-gate`, and `PR-LOOP-PLAYBOOK.md`
guidance now treats negated closing-keyword text with an issue reference as
unsafe for keep-open work, with platform regression coverage. This is Slice 18
agent-context synchronization only; it does not clear implementation blockers,
promote supported features, or replace final closure evidence.
The current canonical Workbench/Idea proof blocker is `sgajbi/lotus-core#882`:
Core must publish a deterministic non-empty `source_batch_fingerprint` /
content hash for `DpmPortfolioUniverseCandidate:v1` READY responses before
Manage, Gateway, and Workbench can preserve source-ref authority through fresh
canonical validation. The stale queued Platform End-to-End Validation run
`30603744637` was recorded on `sgajbi/lotus-platform#599`, cancelled as queue
hygiene, and the post-cancel detector returned `Stale workflow runs: 0`; this
does not clear protected runner, cost-attribution, deployment-promotion, or
production-certification blockers.

The 2026-08-09 continuation audit refreshed the execution posture from current
`lotus-idea` branch source and live GitHub state after creating #871 for the
execution-ledger gate-policy refactor. `make
rfc0002-github-issue-execution-state-audit`, `make
rfc0002-github-issue-execution-summary`, and `make
rfc0002-cross-repo-issue-posture` passed. At that audit point, the Idea ledger
had 58 tracked RFC-0002 issues, 32 closed and 26 open. The governed cross-repo
posture was 127 label-backed RFC-0002 issues across 13 repositories, 88 closed
and 39 open: 25 blocked, no PR-open issues, 2 in-progress issues (#681 and
#871), 4 merged-main or merged-to-main QA-pending dependencies, and 8 tracker
issues. The blocked-actionability classifier reported 0 app-actionable blocked
issues; the remaining blocked issues require production identity/session
authority, protected runtime/deployment evidence, provider/bank/legal approval,
final-closure prerequisites, or certification evidence.

Fresh durable blocker evidence now treats Core `#882`, `#885`, and `#917` as
closed with `status/merged-main`; those issues no longer justify app-code
blocking by themselves. Fresh canonical Workbench/Gateway/Idea proof remains
required before #814/#685/#686 can close. Core `#917` closed after PR #929
reached exact main `6bc937bb173051e0bd4ee9a07ffebd54face0163` and Main
Releasability `31308743764` passed. That evidence is report-only
technology-governance pilot posture and does not certify production
vulnerability posture or Lotus Idea supported-feature promotion. #871 later
closed as a Slice 18 maintainability issue after PR #872 moved static gate
policy into a versioned implementation-proof contract without changing
supported-feature posture, product certification, production identity, or
protected runtime evidence.
Platform
`sgajbi/lotus-platform#647` remains open/blocked: stale scheduled run
`31235891576` was cancelled and the detector returned zero stale runs, but
protected/self-hosted runner capacity is still absent. Current Core main
release instability is tracked outside RFC-0002 through Core `#795` for
same-SHA `Performance Load Gate (Full)` drain timeout, while the earlier
PR #897 merge-SHA migration rollback failure is already represented by the
Core `#730` / PR #899 CI-isolation trail.

Stranded-truth reconciliation on 2026-08-08 first found only active Dependabot
`cryptography-50.0.0` branches touching `pyproject.toml`, with no unique RFC,
docs, wiki, context, contract, or workflow truth. The same source-sync PR then
incorporated the runtime dependency security remediation by pinning
`cryptography==50.0.0`, because GitHub PR Merge Gate `security-audit` reported
`cryptography 49.0.0` as vulnerable with fixed version `50.0.0`. This audit and
dependency posture update do not clear blockers, promote supported features,
certify product support, or replace Core, production identity, protected
runtime, provider, legal, client-publication, support, or final closure
evidence.

The 2026-08-09 SGT continuation sync incorporated the Manage
`sgajbi/lotus-manage#629` post-merge QA finding after PR #630 merged the Core
content-identity consumer fix to Manage main
`4638650e5544900f571303c4767c520f1f28f610`. Although Manage Main Releasability
run `31266349878` and local exact-main `make check` passed, QA found two valid
hash-compatibility defects: the report-input `content_hash` still drifted for
legacy-equivalent waves when optional batch lineage was absent/null, and the
normalizer still mutated unrestricted producer metadata under nested
`selection_basis.source_refs`. #629 is therefore open with
`status/in-progress`, not merged-main QA-pending. It does not clear #379, #675,
#676, #685, #686, #699, or #814 by implication: Manage corrective work, Core
owner evidence, production identity/session authority, protected runtime
evidence, Report/Archive legal-lifecycle conformance, supported-feature
promotion, and final Slice 20 closure remain separately tracked.

The 2026-08-09 Workbench/Manage exact-main refresh recorded then-current live GitHub
state after Workbench PR #555 and Manage PR #631 completed. Workbench PR #555
merged `sgajbi/lotus-workbench#549`, `#550`, `#556`, and `#557` to main
`afd0474524f20bc7d001ccb764a6e587f81d02c5`; Main Releasability run
`31285317629` passed for that exact SHA across workflow lint,
lint/typecheck/coverage/build, Playwright smoke, Docker build/security/SBOM,
and CI-local Docker parity. Manage PR #631 moved `sgajbi/lotus-manage#629` to
`status/merged-main` on main `a6bc609f379b8efadb226c9a2084d7c97b2e26e7` after
Main Releasability run `31268949391` passed. Then-current live `make
rfc0002-cross-repo-issue-posture` reported 124 label-backed RFC-0002 issues
across 13 repositories: 75 closed and 49 open. The open set is 28 blocked, 1
in-progress issue (#681), 10 `status/merged-main`, 2 `status/merged-to-main`,
and 8 tracker issues. Blocked actionability remained 0 app-actionable blocked
issues: 6 Core dependencies and 22 external/protected-evidence dependencies.
This was Slice 18 source-truth synchronization only; it did not close
QA-pending merged-main issues, clear the remaining runtime/protected-evidence blockers, promote supported
features, certify product support, or replace production identity/session
authority, protected runtime, provider, legal, client-publication, support, or
final RFC-0002 closure evidence.

The 2026-08-09 Core blocker closure sync then updated the live blocker
classifier after `sgajbi/lotus-core#882` and `sgajbi/lotus-core#885` closed on
main. Core `#917` later also closed with `status/merged-main` after the
report-only technology-governance pilot reached main. Live `make
rfc0002-cross-repo-issue-posture` now reports 128 label-backed RFC-0002 issues
across 13 repositories: 90 closed and 38 open. The open set is 25
`status/blocked`, 1 `status/in-progress` (`sgajbi/lotus-idea#681`),
2 `status/merged-main`, 2 `status/merged-to-main`,
and 8 `status/tracker`.
Blocked actionability remains 0 app-actionable blocked
issues; the classifier now contains 25 external/protected/canonical-proof
evidence blockers and no Core dependency rows. Idea `#814`, `#685`, and `#686`
now require fresh governed PB_SG_GLOBAL_BAL_001 runtime evidence for Idea seed,
Gateway-backed Workbench queue/detail reads, and browser
review-action/feedback/conversion-intent controls. This sync does not promote a
supported feature, close QA-pending issues, or replace production
identity/session, protected runtime, provider, legal, client-publication,
support, or final RFC-0002 closure evidence.

The 2026-08-09 #871 closure-truth sync records that PR #872 merged the
RFC-0002 execution-ledger gate-policy refactor to Idea main
`f7aca4746e16d3d851c892654a8007743d7ec87a`, main CodeQL `31321978400`
passed, and exact-main Main Releasability `31321981636` passed with workflow
lint, lint/typecheck/security, unit/integration/e2e, PostgreSQL runtime proof,
combined coverage, Docker/release validation, image scan, SBOM, signed
published image digest, provenance/SBOM attestations, release metadata
manifest, and release identity/license binding. Repo-authored wiki source was
published to `lotus-idea.wiki` commit `852ba82` with strict `DiffCount 0`.
The Idea ledger now has 59 tracked RFC-0002 issues, 34 closed and 25 open;
`#681` is the in-progress Slice 18 tracker. The cross-repo posture has
128 label-backed RFC-0002 issues, 90 closed and 38 open, with 25
`status/blocked`, 1 `status/in-progress`, and 0 app-actionable blocked issues.
This sync closes only the ledger-gate maintainability issue and does not close Workbench/Gateway
runtime-proof blockers, production identity/session blockers, protected runtime
evidence, supported-feature promotion, or final RFC-0002 closure.

The 2026-08-09 #864/#866 proof-readiness hardening closure sync keeps
`lotus-idea#681` as the only in-progress RFC-0002 issue. Idea #864 is closed
after PR #865 refactored implementation-proof readiness composition to exact
main `35091eec121ea0c7186302526b211e288a59abed`; Main Releasability
`31304700457`, PR Merge Gate `31304443459`, CodeQL `31304442120`, and Feature
Lane `31304427464` passed. Idea PR #867
merged implementation-proof readiness generator input hardening to exact main
`6d40f7489d70af33e42e28dfb9ffe6e40d880994`; Main Releasability
`31306314749` and CodeQL `31306311168` passed. Idea PR #868 synchronized
source-controlled closure truth to exact main
`560ddcfff9ba61f2db3008fabc62c31c20cfb425`; Main Releasability
`31306932624` and CodeQL `31306929484` passed. #864 and #866 are now present
in the RFC-0002 execution ledger as closed Slice 17/19 hardening issues. This
is Slice 18 source-truth synchronization only; #681 remains open and the update
does not clear Workbench/Gateway runtime proof, data-product certification,
supported-feature promotion, production identity/session, protected runtime,
provider, legal, client-publication, support, or final RFC-0002 closure
evidence.

The 2026-07-31 dependency audit then verified current-main source-side posture
for the writable cross-repo blockers without finding hidden app-actionable
blocked work. Durable evidence comments were posted on `sgajbi/lotus-platform#495`,
`sgajbi/lotus-platform#563`, `sgajbi/lotus-ai#115`, `sgajbi/lotus-ai#122`,
`sgajbi/lotus-manage#624`, then-open `sgajbi/lotus-report#136`,
`sgajbi/lotus-archive#55`, `sgajbi/lotus-workbench#436`, and
`sgajbi/lotus-workbench#500`, then coordinated through #681. Workbench #500
later closed with `status/merged-main` and was removed from the current open
blocked classifier by Idea PR #837. Focused
owner-repo validation passed for platform cost-attribution, BFF
principal-session source contracts, AI retention and Idea workflow-pack proof,
Manage temporal receipt/action-intake proof, Report Idea intake/materialization
and retention policy, Archive Idea lifecycle decisions, and Workbench
opportunities/BFF/action-control proof. This audit keeps those issues open
because remaining acceptance criteria require Core readiness, production
IdP/session/token-claims authority, protected FinOps evidence, live
provider/model-risk certification, legal/lifecycle approval, managed signing
keys, canonical live browser proof, client-publication authority, or final
RFC-0002 closure evidence.
Platform PR `sgajbi/lotus-platform#631` fixes the prior Manage seed
authorization failure; #686 is blocked, not QA-pending, until
`sgajbi/lotus-core#882` restores Core DPM portfolio-universe candidate
source-batch fingerprints and Workbench live browser action-control proof can
be rerun. This records lifecycle truth only: #340 is closed for the signed
attestation trust boundary without claiming
supported-feature promotion, client-ready publication, Workbench proof,
autonomous advice, prompt/RAG infrastructure, model training, or broader
production rollout. #380 remains blocked for production principal/session,
authenticated Workbench BFF, core-owned canonical runtime, mesh onboarding,
entitlement-denied, and supported-feature promotion evidence; #690 is
`closed_complete` after PR #774 merged bounded Report intake runtime proof, PR
#775 synchronized merged-main evidence, and PR #776 synchronized final QA
closure truth to exact main
`aa492aedd46f30b854c8478edb919605dbdd58fc` with Main Releasability
`30432065538`, CodeQL `30432058627`, wiki commit `c08509a`, strict wiki
parity, and branch cleanup. #691, #692, #693, and #699 remain blocked rather
than QA-pending because their merged implementation tranches preserve only
bounded Render/Archive, mesh-readiness, cost-attribution, and proof-control
evidence; lifecycle-safe publication authority, production identity, Archive
production trust/legal evidence, platform mesh certification, Gateway/Workbench
discovery proof, protected capacity/FinOps attestations, supported-feature
promotion, and final live-journey evidence remain open.

The cross-repo posture command now includes a source-controlled blocker
actionability classifier at
`contracts/implementation-proof/rfc0002-cross-repo-blocker-classification.v1.json`.
Its Markdown output also renders each blocked issue with issue URL,
actionability, blocker class, and remaining authority, so the current
Core-vs-protected/external split is durable execution evidence rather than a
chat-only explanation.
For the current 109-issue label-backed RFC-0002 program posture, all 29 open
`status/blocked` issues are classified: 6 are Core dependencies and 23 require
external or protected evidence. The current app-actionable blocked count is 0.
Future agents must not use `status/blocked` for writable non-Core app work; if
the remaining acceptance criteria can be satisfied in `lotus-idea`,
`lotus-gateway`, `lotus-workbench`, `lotus-manage`, `lotus-report`,
`lotus-render`, `lotus-archive`, `lotus-ai`, or `lotus-platform` without Core,
IdP, protected-environment, provider, bank/legal, or certification evidence,
the issue must be reclassified to ready or in-progress and implemented.

The missing-benchmark Core material now records the independently owned closed
v2 runtime contract implemented by issue `#499`. One named application use case
performs one Core fetch and preserves exact evidence or a stable error. Request,
source assignment-state, and deterministic candidate or ready-assignment
no-opportunity receipts are pseudonymous and digest-bound. The stable operator
environment variable and Make target accept v2 only; retired flat paths are
prohibited. Performance benchmark readiness remains a separate authority and
is now documented through its own source-preserving use case and closed v2
runtime-evidence contract under issue `#500`. The stable environment variable,
readiness CLI argument, output filename, and Make target remain, but retired
flat v1 artifacts are rejected. The contract binds exact Performance
product/route/time, provenance hashes, benchmark context, coverage,
freshness/quality, producer correlation/trace, and deterministic
review-required or no-opportunity posture. A fresh v2 runtime capture remains
required; the historical July 5 v1 artifact is not qualifying evidence.

This documentation slice does not promote any supported feature. It records
bounded Workbench read-path source contract, Gateway/Workbench contract proof, and
Gateway/Workbench discovery contract proof only; it does not add full
Gateway/Workbench live proof, data-product certification, downstream
realization, live source certification, or certified long-running scheduled
runtime proof. The bond-maturity / reinvestment update records only
deterministic policy, caller-supplied API, and fail-closed source-port truth; it
does not prove source-backed generation or promote a client-ready reinvestment
journey.

## Required Work

1. Update README, repository context, API docs, operations docs, data-product
   docs, model-risk docs, demo docs, supported features, and wiki source.
2. Run wiki check-only validation.
3. Update `lotus-platform` scaffold/context or skill routing only if reusable
   Lotus guidance changed.
4. Record explicit no-change decisions for platform context, wiki, or skills
   where no update is required.

## Wiki Page Standard

The repo-local wiki source must include current-state pages for:

1. Home,
2. Overview,
3. Architecture,
4. Getting Started,
5. Development Workflow,
6. Validation And CI,
7. RFC Index,
8. Integrations,
9. Supported Features,
10. Operations Runbook,
11. Security And Governance,
12. Demo Readiness,
13. Roadmap.

Pages must summarize and route to source docs. They must not duplicate RFC
mechanics or promote planned target-state behavior as supported capability.

## Acceptance Gate

1. Docs describe actual endpoints, modules, fields, proof artifacts, and
   constraints.
2. Wiki summarizes and routes to source docs without stale duplication.
3. Supported features are implementation-backed.
4. Future agents can pick up the repository without rediscovering boundaries.
