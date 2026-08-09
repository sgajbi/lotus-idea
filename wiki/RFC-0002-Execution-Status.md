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
| Total RFC-0002 issues | 124 |
| Closed RFC-0002 issues | 83 |
| Open RFC-0002 issues | 41 |
| Open blocked issues | 28 |
| App-actionable blocked issues | 0 |
| Active synchronization tracker | `sgajbi/lotus-idea#681` |

The zero app-actionable blocked count is important. It means an open issue may
remain `status/blocked` only when the remaining authority is Core-owned,
protected-environment evidence, production identity/session authority,
provider/legal/model-risk approval, or certification evidence. If writable
application work is discovered in a blocked issue, move that issue out of
blocked posture and implement or reclassify it.

```mermaid
flowchart LR
    Issues["GitHub issue posture<br/>124 RFC-0002 issues"]
    Open["41 open<br/>28 blocked, 1 in progress,<br/>4 QA-pending aliases, 8 trackers"]
    Blocked["Blocked classifier<br/>0 app-actionable"]
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
| `status/blocked` | 28 | Core, protected, identity, provider, legal, publication, or certification evidence. |
| `status/in-progress` | 1 | Continuous Slice 18 synchronization tracker `sgajbi/lotus-idea#681`. |
| `status/merged-main` | 2 | Merged-main issues awaiting canonical QA closure evidence. |
| `status/merged-to-main` | 2 | Repository-local Advise merged-main alias awaiting QA closure evidence. |
| `status/tracker` | 8 | Parent or umbrella tracking issues, not immediate implementation items. |

## Highest-Leverage Remaining Dependencies

| Priority | Issue | Why it matters | Current owner boundary |
| --- | --- | --- | --- |
| 1 | `sgajbi/lotus-core#882` | Blocks Idea `#814`, `#685`, and `#686` by preventing Core-owned deterministic `source_batch_fingerprint` or content-hash publication for `DpmPortfolioUniverseCandidate:v1` READY responses. | Core must publish the source authority. Downstream repos must not fabricate it. |
| 2 | Workbench/Gateway/Idea feedback-action proof | The latest canonical QA stopped before AI/Advise proof because the Workbench browser did not observe the expected Gateway-backed feedback confirmation. | Workbench/Gateway/Idea investigation; not identity work. |
| 3 | `sgajbi/lotus-core#885` | Blocks data-product trust telemetry and catalog promotion where Core request-scope semantics drift for `HoldingsAsOf` and `IngestionEvidenceBundle`. | Core owns domain-product request-scope truth. |
| 4 | `sgajbi/lotus-core#917` | Blocks platform technology-governance vulnerability posture rollout evidence against Core. | Core owns the pilot evidence; platform owns policy/gate rollout. |
| 5 | Production identity/session issues | Blocks supported-feature promotion and production principal proof. | Not implemented in local/dev; tracked through Workbench `#436`, platform `#563`, Manage `#624`, and Idea `#687` / `#380`. |

```mermaid
flowchart TD
    Core882["Core #882<br/>DPM source batch fingerprint"]
    Feedback["Workbench/Gateway/Idea<br/>feedback-action proof"]
    CanonicalQA["Canonical front-office QA<br/>PB_SG_GLOBAL_BAL_001"]
    IdeaProof["Idea #685/#686/#814<br/>queue, detail, actions, seed proof"]
    QAPending["QA-pending merged-main issues<br/>AI #126, Advise #481/#485, Platform #659"]
    Support["Supported feature promotion<br/>still blocked"]
    Identity["Production identity/session<br/>Workbench #436 / Platform #563 / Manage #624 / Idea #687/#380"]
    Protected["Protected/runtime/provider/legal evidence"]

    Core882 --> IdeaProof
    Feedback --> CanonicalQA
    IdeaProof --> CanonicalQA
    CanonicalQA --> QAPending
    QAPending --> Support
    Identity --> Support
    Protected --> Support
```

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
| `sgajbi/lotus-platform#659` | Fresh canonical QA must prove the DPM seed no longer fails on `DPM_WORKFLOW_NOT_REQUIRED_FOR_RUN_STATUS`. |

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
| 1 | Fix the current Workbench/Gateway/Idea feedback-action canonical QA blocker. | Issue-backed commits, focused tests, and fresh canonical QA progressing past the feedback step. |
| 2 | Consume Core `#882` after it lands on Core main. | Fresh Gateway/Workbench queue/detail and action-control runtime proof for Idea `#685`, `#686`, and `#814`. |
| 3 | Re-run canonical front-office QA. | Machine-readable `live-validation-summary.json`, screenshot index, platform QA JSON/Markdown, and no failed browser assertions. |
| 4 | Close QA-pending merged-main issues only when their specific proof appears in the fresh run. | Issue-loop `qa_passed_closed` comments retaining merged-main evidence. |
| 5 | Continue Slice 18/19 hardening and Slice 20 closure only after blockers are resolved or explicitly classified. | Updated docs/wiki/context, exact-main CI evidence, wiki publication, and branch hygiene. |

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
