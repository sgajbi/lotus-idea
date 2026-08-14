# RFC-0002 Execution Status

Current posture: RFC-0002 foundations are implementation-backed, but no
externally supported Lotus Idea product feature is promoted.

Use this page to find the current issue posture, canonical QA status,
dependency map, and closure rules without relying on chat memory.

## Reader Map

| Audience | Read first | Decision this page supports |
| --- | --- | --- |
| Business and product | [What Is Already Implementation-Backed](#what-is-already-implementation-backed) and [Non-Claims](#non-claims) | What can be described as current foundation versus what remains unsupported. |
| Sales and demo | [Canonical Front-Office QA Status](#canonical-front-office-qa-status) and [Next Execution Order](#next-execution-order) | Whether an end-to-end demo claim has current evidence. |
| Operations and support | [Current Snapshot](#current-snapshot) and [Highest-Leverage Remaining Dependencies](#highest-leverage-remaining-dependencies) | Which blocker class owns the next recovery or escalation path. |
| Engineering and agents | [Open Status Counts](#open-status-counts) and [Closure Decision Matrix](#closure-decision-matrix) | Which issues can be fixed, closed, or must remain blocked. |

## Current Snapshot

| Evidence | Current value |
| --- | --- |
| Snapshot command | `make rfc0002-cross-repo-issue-posture` |
| Execution audit | `make rfc0002-github-issue-execution-state-audit` passed |
| Repositories checked | 13 |
| Total RFC-0002 issues | 202 |
| Closed RFC-0002 issues | 164 |
| Open RFC-0002 issues | 38 |
| Open blocked issues | 25 |
| App-actionable blocked issues | 0 |
| Active synchronization tracker | `sgajbi/lotus-idea#681`; `sgajbi/lotus-idea#1094` is closed after PR #1095 for AI-governance test-support maintainability. The latest Idea implementation-backed closure is PR #1095 on main `0a8fbfac146c6fb99c70ddb109b33b9b88586f66` after exact-main Main Releasability run `31802296872`, CodeQL run `31802289873`, wiki publication `44060bc`, strict wiki parity, and branch hygiene passed. `sgajbi/lotus-idea#1091` is the previous Slice 12/13/19 conversion-intent API handler boundary maintainability issue. The latest QA-closed Idea maintainability issues are `sgajbi/lotus-idea#1094`, `#1091`, `#1088`, `#1084`, and `#1082`. |

The zero app-actionable blocked count is important. It means an open issue may
remain `status/blocked` only when the remaining authority is Core-owned,
protected-environment evidence, production identity/session authority,
provider/legal/model-risk approval, or certification evidence. If writable
application work is discovered in a blocked issue, move that issue out of
blocked posture and implement or reclassify it.

```mermaid
flowchart LR
    Issues["GitHub issue posture<br/>202 label-backed RFC-0002 issues"]
    Open["165 closed and 37 open<br/>25 `status/blocked`, 0 `status/fixed-local`, 1 `status/in-progress`, 1 `status/merged-main`, 2 `status/merged-to-main`, 0 `status/pr-open`, 8 `status/tracker`"]
    Blocked["Blocked classifier<br/>0 app-actionable blocked"]
    Work["Writable work<br/>only when evidence proves app-code ownership"]
    External["Core / protected / identity / provider / legal evidence"]
    QA["Canonical QA<br/>required before closure"]

    Issues --> Open
    Open --> Blocked
    Blocked -->|"writable defect found"| Work
    Blocked -->|"current classified state"| External
    Open --> QA
```

## Open Status Counts

| Status label | Count | Interpretation |
| --- | ---: | --- |
| `status/blocked` | 25 | Protected, identity, provider, legal, publication, canonical QA, or certification evidence. |
| `status/fixed-local` | 0 | No locally proven issue is waiting for PR handoff. |
| `status/in-progress` | 1 | Continuous Slice 18 synchronization tracker `sgajbi/lotus-idea#681`. |
| `status/merged-main` | 1 | Merged-main issue awaiting QA closure evidence, currently `sgajbi/lotus-ai#126`. |
| `status/merged-to-main` | 2 | Repository-local Advise merged-main alias awaiting QA closure evidence. |
| `status/pr-open` | 0 | No RFC-0002 issue currently has an open PR. |
| `status/tracker` | 8 | Parent or umbrella tracking issues, not immediate implementation items. |

Latest synchronization evidence: Current GitHub issue posture has 202
label-backed RFC-0002 issues, 165 closed and 37 open, with 25
`status/blocked`, 0 `status/fixed-local`, 1 `status/in-progress`, 1
`status/merged-main`, 2 `status/merged-to-main`, 0 `status/pr-open`, 8
`status/tracker`, and 0 app-actionable blocked issues. The Idea source ledger
tracks 133 RFC-0002 issues: 108 closed and 25 open. `lotus-idea#1094` is
closed after PR #1095 for test-support maintainability; `lotus-idea#1091` is
closed after PR #1092 reached exact main
`a1273204c47168806e4f1b1b21d8c30660aa8970`; Main Releasability run
`31796812445`, Push-on-main run `31796803970`, wiki publication `37352ca`,
strict wiki parity, and branch cleanup passed. This is source-truth
synchronization only; no closure in this section promotes a Lotus Idea
supported feature.

## Highest-Leverage Remaining Dependencies

| Priority | Issue | Why it matters | Current owner boundary |
| --- | --- | --- | --- |
| 1 | Current mainline-source provenance readiness | Fresh read-only preflight `rfc0002-mainline-preflight-20260814-212624.json` failed closed with 11/13 repositories aligned. Core PR #948 leaves `lotus-core` on `feat/ingestion-evidence-authority` at `5acbfae338918acb96195205f9e8aeee52273958` instead of `origin/main` `04939c7d360233e35746639c7f823f9f4563d9c9`; Workbench PR #701 leaves `lotus-workbench` on `feat/699-performance-evidence-assurance` at `6eba673f0abd049fc91654f7707e829dabc2fa10` instead of `origin/main` `9ff3161c917bf38c41aef4e8f9c42cb3d9c40b50`. | Core and Workbench owned; do not modify from Idea. Ask the owning agents to get PR #948 and PR #701 green/merged before closure-grade canonical proof. |
| 2 | Workbench/Gateway/Idea feedback-action proof | The latest completed canonical QA stopped before AI/Advise proof because the Workbench browser did not observe the expected Gateway-backed feedback confirmation. Workbench PR #698 is merged and exact-main validated, but Workbench PR #701 is now the active non-mainline Workbench branch and neither PR replaces fresh canonical QA. | Workbench/Gateway/Idea runtime proof after Core and Workbench are clean exact main. |
| 3 | Idea `#814`, `#685`, and `#686` canonical proof | Core `#882` is closed; these issues still require fresh governed PB_SG_GLOBAL_BAL_001 queue/detail/action evidence, not downstream hash fabrication or stale artifacts. | Canonical full-stack proof across Idea, Gateway, and Workbench. |
| 4 | QA-pending merged-main issues | `sgajbi/lotus-ai#126`, `sgajbi/lotus-advise#481`, and `sgajbi/lotus-advise#485` need fresh issue-specific canonical evidence before closure. | Close only when the fresh run reaches and proves each path. |
| 5 | Production identity/session issues | Blocks supported-feature promotion and production principal proof. | Not implemented in local/dev; tracked through Workbench `#436`, platform `#563`, Manage `#624`, and Idea `#687` / `#380`. |

```mermaid
flowchart TD
    CoreClosed["Core #882/#885<br/>closed on 2026-08-09"]
    Core948["Core PR #948<br/>open / not exact main"]
    Workbench701["Workbench PR #701<br/>open / not exact main"]
    Workbench698["Workbench PR #698<br/>merged and exact-main validated"]
    Feedback["Workbench/Gateway/Idea<br/>feedback-action proof"]
    CanonicalQA["Canonical front-office QA<br/>PB_SG_GLOBAL_BAL_001"]
    IdeaProof["Idea #685/#686/#814<br/>queue, detail, actions, seed proof"]
    Core917["Core #917<br/>closed report-only governance pilot"]
    QAPending["QA-pending merged-main issues<br/>AI #126, Advise #481/#485"]
    Support["Supported feature promotion<br/>still blocked"]
    Identity["Production identity/session<br/>Workbench #436 / Platform #563 / Manage #624 / Idea #687/#380"]
    Protected["Protected/runtime/provider/legal evidence"]

    CoreClosed --> IdeaProof
    Core948 --> CanonicalQA
    Workbench701 --> CanonicalQA
    Workbench698 --> Feedback
    Feedback --> CanonicalQA
    IdeaProof --> CanonicalQA
    CanonicalQA --> QAPending
    QAPending --> Support
    Identity --> Support
    Protected --> Support
```

## Recently Unblocked Dependencies

| Issue | Current state | Why it matters now |
| --- | --- | --- |
| `sgajbi/lotus-core#882` | Closed on 2026-08-09 with `status/merged-main`. | The blocker classifier no longer treats Core DPM source-batch fingerprint publication as open. Idea `#814`, `#685`, and `#686` must now be proved with fresh canonical runtime evidence. |
| `sgajbi/lotus-core#885` | Closed on 2026-08-09 with `status/merged-main`. | Data-product request-scope drift is no longer an open blocked dependency in the RFC-0002 cross-repo posture. |
| `sgajbi/lotus-core#917` | Closed on 2026-08-09 with `status/merged-main`. | Core completed the report-only technology-governance pilot evidence. It removes the Core pilot from active in-progress posture but does not certify production vulnerability posture or supported-feature promotion. |
| `sgajbi/lotus-platform#659` | Closed on 2026-08-09 with `status/merged-main`. | Canonical QA `canonical-front-office-qa-20260809-084903` proved the DPM command-center seed completed with status `ok`; the later Workbench browser failure remains tracked separately. |

## Canonical Front-Office QA Status

Latest known full canonical run:

| Field | Value |
| --- | --- |
| Platform summary | `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260809-084903.md` |
| Platform JSON | `lotus-platform/output/front-office-qa/canonical-front-office-qa-20260809-084903.json` |
| Live validation summary | `lotus-platform/output/front-office-qa/rfc0002-canonical-qa-20260809-0849/live-validation-summary.json` |
| Portfolio | `PB_SG_GLOBAL_BAL_001` |
| DPM command-center seed | Passed and wrote `dpm-command-center-seed-20260809-091311.json` |
| Lotus Idea readiness | Ready on direct and canonical hosts |
| Run result | Failed in canonical Workbench browser validation |

Failure observed:

```text
expect(locator).toBeVisible() failed
Expected text:
Feedback recorded through Gateway. Source-owned detail and queue posture have been refreshed.
```

This failure happened before the run reached the advisory copilot and Advise
proposal proof paths. Therefore it cannot close:

| Issue | Closure requirement still missing |
| --- | --- |
| `sgajbi/lotus-ai#126` | Fresh canonical QA must prove the advisory copilot `PROPOSAL_EXPLANATION` path reaches `REVIEW_REQUIRED` or later reviewed posture. |
| `sgajbi/lotus-advise#481` | Fresh canonical QA must prove Advise startup remains valid in the full front-office runtime. |
| `sgajbi/lotus-advise#485` | Fresh canonical QA must prove the reviewed narrative report-package request path progresses through Workbench/Gateway. |

Current dependency refresh: `lotus-workbench` PR #698 is merged to main
`9ff3161c917bf38c41aef4e8f9c42cb3d9c40b50`, exact-main Main Releasability
run `31784470442` passed, wiki parity is `DiffCount 0`, and issue
`sgajbi/lotus-workbench#697` carries post-merge evidence. That removes the
known Workbench review-workspace implementation dependency, but it does not
replace a fresh canonical QA run. A fresh 2026-08-14 read-only mainline-source
preflight now fails before stack mutation because Core PR #948 and Workbench
PR #701 leave `lotus-core` and `lotus-workbench` off exact `origin/main`.
Closure-grade canonical proof remains pending until both repositories return to
clean exact mainline state.

## Closure Decision Matrix

| Situation | Correct action | Incorrect action to avoid |
| --- | --- | --- |
| Issue is `status/merged-main` or Advise `status/merged-to-main`, but fresh canonical QA has not reached its proof path. | Keep open and wait for issue-specific QA evidence. | Closing because the PR merged or because an earlier run passed another path. |
| Issue is `status/blocked` and the remaining authority is Core, protected runtime, identity, provider, legal, or production certification. | Keep blocked with owner/evidence clearly stated. | Reclassifying as writable app work without evidence. |
| A blocked issue reveals a writable app-code defect. | Move it out of blocked posture, link or create the canonical issue, fix, test, and validate. | Leaving app-actionable work hidden under `status/blocked`. |
| Canonical QA fails before downstream proof paths. | Record the failure and fix the first failing owned path. | Closing later-stage AI/Advise/platform issues from an incomplete run. |
| Supported-feature registry remains `foundation_only`. | Use foundation and roadmap language only. | Calling the product supported, bank-ready, or client-ready. |

## What Is Already Implementation-Backed

RFC-0002 has implementation-backed foundations across:

| Area | Current support level |
| --- | --- |
| Domain vocabulary and lifecycle | Implemented foundation, not product support. |
| Deterministic opportunity policies | Implemented internal candidate foundations across Core, Performance, Risk, Advise, and Manage source evidence. |
| Persistence, replay, idempotency, and audit | Implemented repository foundations with PostgreSQL proof paths. |
| Advisor queues, review, feedback, and conversion intent | Implemented internal foundations with trusted caller and entitlement boundaries. |
| AI explanation governance | Implemented deterministic and review-gated foundations; live-provider and model-risk production certification remain blocked. |
| API/OpenAPI certification | Implemented internal certified endpoint foundations and gates. |
| Downstream realization | Implemented bounded conversion/report intent and source-contract proof consumption; client publication remains blocked. |
| Operations and vulnerability posture | Implemented bounded internal posture and gates; protected execution and production evidence remain blocked. |

Use [Supported Features](Supported-Features) for the externally supported
feature truth. The registry remains `foundation_only` with an empty `features`
list.

## Next Execution Order

| Order | Work | Completion evidence |
| --- | --- | --- |
| 1 | Resolve current mainline-source blockers: Core PR #948 and Workbench PR #701 must merge or the repos must otherwise return to clean exact `origin/main`. | Passing `mainline-source-provenance` preflight for all 13 canonical repositories before any stack mutation. |
| 2 | Finish the current Workbench/Gateway/Idea feedback-action canonical QA blocker. | Issue-backed commits, focused tests, and fresh canonical QA progressing past the feedback step. |
| 3 | Re-run canonical front-office QA after Core `#882` closure is consumed by the stack and current Core/Workbench branches are mainline-clean. | Machine-readable `live-validation-summary.json`, screenshot index, platform QA JSON/Markdown, and no failed browser assertions for queue/detail/action proof. |
| 4 | Reconcile Idea `#814`, `#685`, and `#686` from fresh runtime artifacts only. | Queue/detail/action-control proof from the governed runtime, with stale artifacts rejected. |
| 5 | Close QA-pending merged-main issues only when their specific proof appears in the fresh run. | Issue-loop `qa_passed_closed` comments retaining merged-main evidence. |
| 6 | Continue Slice 18/19 hardening and Slice 20 closure only after blockers are resolved or explicitly classified. | Updated docs/wiki/context, exact-main CI evidence, wiki publication, and branch hygiene. |

## Non-Claims

This page does not promote:

1. client-ready opportunity advice,
2. suitability, compliance, mandate, risk, performance, or execution authority,
3. production identity/session-token proof,
4. live AI-provider/model-risk certification,
5. protected deployment, cost, or capacity certification,
6. data-product activation or supported-feature promotion,
7. final RFC-0002 closure.

Those claims stay blocked until their owning issues carry implementation-backed
mainline evidence and the supported-feature registry changes from
`foundation_only`.
