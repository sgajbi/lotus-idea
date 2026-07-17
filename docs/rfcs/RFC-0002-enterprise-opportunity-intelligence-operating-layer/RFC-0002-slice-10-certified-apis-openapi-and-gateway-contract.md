# RFC-0002 Slice 10: Certified APIs, OpenAPI, And Gateway Contract

Status: Partially implemented - certified internal API foundations plus bounded read-only Gateway publication for advisor queue and candidate detail

## Outcome

Expose certified `lotus-idea` APIs and Gateway routes for supported behavior.

## Implemented In This Slice

The first certified API foundations are:

- `POST /api/v1/idea-signals/high-cash/evaluate`
- `POST /api/v1/idea-signals/high-cash/evaluate-from-source`
- `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`
- `POST /api/v1/idea-signals/low-income/evaluate`
- `POST /api/v1/idea-signals/bond-maturity/evaluate`
- `POST /api/v1/idea-signals/concentration-risk/evaluate`
- `POST /api/v1/idea-signals/high-volatility/evaluate`
- `POST /api/v1/idea-signals/drawdown-review/evaluate`
- `POST /api/v1/idea-signals/underperformance/evaluate`
- `POST /api/v1/idea-signals/allocation-drift/evaluate`
- `POST /api/v1/idea-signals/missing-suitability/evaluate`
- `POST /api/v1/idea-signals/missing-risk-profile/evaluate`
- `POST /api/v1/idea-signals/mandate-restriction/evaluate`
- `POST /api/v1/idea-signals/missing-benchmark/evaluate`
- `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions`
- `GET /api/v1/idea-candidates/{candidateId}`
- `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`
- `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`
- `GET /api/v1/review-queues/advisor`
- `POST /api/v1/idea-candidates/{candidateId}/review-actions`
- `POST /api/v1/idea-candidates/{candidateId}/feedback`
- `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`
- `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`
- `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`

These endpoints evaluate caller-supplied, source-owned `lotus-core` evidence
for the high-cash / idle-liquidity signal family. They consume source-reported
cash weight and source references; they do not fetch upstream data and do not
calculate official cash, holdings, or portfolio values.

The concentration-risk, high-volatility, drawdown-review, underperformance, allocation-drift, low-income, bond-maturity, missing suitability, missing
risk-profile, mandate/restriction, and missing-benchmark signal endpoints
expose bounded caller-supplied evidence evaluation over source-owned Risk,
Performance, Core, Advise, or Manage
posture evidence. They create only source-safe review candidates or blocked
posture, require advisor role and `idea.signal.evaluate` capability, redact raw source
routes and content hashes from response candidates, emit bounded operation
events, and do not infer client income needs, provide funding advice, issue
treasury instructions, approve planning suitability, recommend replacement
products, calculate reinvestment advice, calculate concentration, calculate volatility, calculate
drawdown, calculate returns, calculate allocation drift, assign benchmarks, approve risk
methodology, recommend trades, create rebalance actions, own maturity
schedules, create orders, approve suitability, policy, proposal, sign-off,
mandate state, restriction clearance, benchmark assignment, benchmark
methodology, performance calculation, client publication, Gateway, Workbench,
data-mesh certification, or supported-feature promotion.

`evaluate-and-persist` adds internal candidate persistence through the Slice 06
repository foundation. It requires `Idempotency-Key` and
`idea.candidate.persist`, returns replay/conflict posture for idempotency
behavior, and reports `durableStorageBacked` from the active repository
provider. `local` and `test` profiles may use process-local writes; `demo`,
`staging`, and `production` require `LOTUS_IDEA_DATABASE_URL` and return
`durable_repository_not_configured` before in-memory mutation when durable
storage is absent.

The lifecycle transition endpoint exposes the Slice 06 internal lifecycle
history, idempotency, and audit foundation over persisted candidates. It
requires `Idempotency-Key` and `idea.candidate.lifecycle.transition`, applies
the canonical caller-settable domain lifecycle transition graph, returns
replay/conflict, not-found, and invalid-transition posture, and keeps
`supportedFeaturePromoted=false`. The OpenAPI request contract references
`CallerSettableIdeaLifecycleStatus` so `accepted` and `executed` cannot be
submitted through generic lifecycle transitions; downstream acceptance posture
belongs to conversion outcomes and downstream submissions. `durableStorageBacked`
follows the active repository provider.

The candidate detail endpoint exposes a source-safe internal read projection
over persisted candidate snapshots. It requires
`idea.candidate.detail.read` capability or advisor/operator role, returns
redacted source evidence, lifecycle history, review decisions, feedback,
conversion intents/outcomes, report evidence-pack summaries, and audit summary
posture, and does not expose source-system routes, raw source content hashes,
downstream authority, Workbench proof, data-product certification, or
supported-feature promotion. The bounded read-only Gateway candidate detail
publication preserves this source-safe projection and forwards caller
entitlement-scope headers; `lotus-idea` applies those headers fail-closed before
returning detail. `durableStorageBacked` follows the active repository provider.
When the active durable provider is PostgreSQL, ordinary candidate-detail reads
use an internal repository-side projection for the requested candidate and its
related lifecycle, audit, review, feedback, conversion, report-evidence, and
AI-lineage rows rather than hydrating a whole repository snapshot. This is
bounded design modularity inside `lotus-idea`; it is not a separate runtime
service boundary or a supported-feature promotion.

The candidate evidence replay endpoint exposes internal operator replay posture
over persisted evidence hashes. It requires `idea.candidate.evidence.replay`
plus operator role, accepts caller-supplied current source refs, returns
matched, stale-source, hash-mismatch, expired, or not-found posture, and never
calls Core, exports raw source routes, grants downstream authority, certifies
data products, proves Gateway/Workbench behavior, or promotes a supported
feature. `durableStorageBacked` follows the active repository provider.

The review-action and feedback endpoints expose the Slice 08 internal workflow
foundation over persisted candidates. They require `Idempotency-Key`, a
mutating capability, caller role, and upstream-authorized review scope. They
record review decisions or feedback through the same internal repository
foundation, return replay/conflict/not-found posture, never grant downstream
suitability/compliance/mandate/execution/client-communication authority, and
keep `supportedFeaturePromoted=false`. `durableStorageBacked` follows the
active repository provider.

Issue `#532` certifies both executable feedback success modes. Code-owned,
DTO-validated examples now publish a newly accepted feedback event and a
cross-key business-resource replay with `feedbackEvent=null` and
`persistence.decision=replayed`. OpenAPI and the endpoint ledger must exactly
match those examples, and the endpoint certification gate fails if either
mode, its authority boundary, or its integration evidence drifts. This
contract work does not promote feedback as a data product or supported
feature.

Issue `#535` applies the same executable-contract standard to review actions
and consolidates both review-workflow mutations behind one internal contract
module. Code-owned, DTO-validated examples publish a newly accepted review
decision and a business-resource replay with `reviewDecision=null` and
`persistence.decision=replayed`. The accepted example preserves the explicit
nullable `snoozedUntilUtc` field and the
`grantsDownstreamAuthority=false` boundary. OpenAPI, the endpoint ledger, and
the contract tests must match both modes exactly; the certification gate fails
when any payload, replay evidence, or publication reference drifts. This is
design modularity inside the existing `lotus-idea` deployable and does not
create a review microservice or promote a supported review product.

PR `#536` merged issue `#535` to `main` at
`20d64edaaf15d9b85f69927f0a3887b2d57bd865`. Main Releasability run
`29523305583` passed, including lint, typecheck, security, architecture,
OpenAPI, 4,708 unit tests, integration, end-to-end, PostgreSQL runtime proof,
99% combined coverage, container runtime smoke, vulnerability scan, SBOM
generation, commit-tagged image publication, digest inspection, keyless
signing, provenance attestation, SBOM attestation, release identity validation,
and CI signal evidence. The released image is
`ghcr.io/sgajbi/lotus-idea@sha256:f57e98efd9291e731e435db3d325dc453d6c129df8a865df8236d5d995807e16`.
CodeQL run `29523299087` also passed for the exact merge SHA. Repo-authored
wiki source was published after merge and strict parity returned zero
differences. Supported-feature posture remains unchanged.

Issue `#538` certifies accepted and replayed success modes for conversion
intent and conversion outcome mutations. One code-owned conversion-workflow
example module validates both response families through their API DTOs and
publishes named OpenAPI modes. The accepted outcome preserves explicit null
correction fields, while all examples retain false downstream execution,
suitability, client-communication, and supported-feature authority. A shared
named-success validator now enforces exact OpenAPI, endpoint-ledger, and
integration-evidence parity across review and conversion workflows instead of
duplicating endpoint-specific gate logic. This is internal design modularity
inside the existing deployable and does not certify downstream realization,
Gateway, Workbench, data products, or supported features.

PR `#540` merged issue `#538` to `main` at
`f923b83075c306a658ce01232af5b8edbc099cbf`. Main Releasability run
`29525897999` passed, including lint, typecheck, security, architecture,
OpenAPI, 4,714 unit tests, integration, end-to-end, PostgreSQL runtime proof,
99% combined coverage, container runtime smoke, vulnerability scan, SBOM
generation, commit-tagged image publication, digest inspection, keyless
signing, provenance attestation, SBOM attestation, release identity validation,
and CI signal evidence. The released image is
`ghcr.io/sgajbi/lotus-idea@sha256:20529440f6366a0522efac45bf2bff64a47e81a7568034a1f13972fe6e6862f6`.
CodeQL run `29525892683` also passed for the exact merge SHA. Repo-authored
wiki source was published after merge and strict parity returned zero
differences. Supported-feature posture remains unchanged.

Issue `#539` applies the same executable-contract standard to report
evidence-pack request recording. A capability-owned, DTO-validated example
module publishes accepted and idempotent replay modes; replay exposes
`reportEvidencePack=null` with `persistence.decision=replayed`. The accepted
mode preserves `grantsClientPublicationAuthority=false`,
`createsRenderedOutput=false`, and `createsArchiveRecord=false`, while both
modes retain `supportedFeaturePromoted=false`. OpenAPI, the endpoint ledger,
and cited integration behavior must match exactly. The same-pattern inventory
opened issue `#542` for the remaining multi-shape HTTP 2xx operations, which
require capability-by-capability review rather than bulk normalization. This
is internal API design modularity and does not certify Report intake, Render,
Archive, client publication, Gateway, Workbench, data products, or supported
features.

Issue `#545` continues issue `#542` through a bounded candidate-state tranche.
One capability-owned, DTO-validated example module publishes lifecycle
`accepted` and idempotent `replayed` modes plus evidence replay `matched`,
`hash_mismatch`, `stale_source`, and `expired` modes. The audit found that the
last two replay postures were executable HTTP 200 behavior but absent from the
endpoint ledger, so the implementation corrects ledger truth rather than
copying the incomplete inventory. The shared named-success validator now
accepts generic required behavioral evidence instead of assuming every
multi-mode contract is only an idempotency replay. Exact factory, OpenAPI,
ledger, and behavioral-test parity is blocking. All examples preserve source
redaction, false downstream authority, and
`supportedFeaturePromoted=false`. This is design modularity inside the existing
deployable; signal evaluation, downstream realization, readiness metadata,
Gateway, Workbench, data products, and supported-feature promotion remain
outside this tranche.

PR `#546` merged issue `#545` by rebase to exact-main SHA
`c14d3e41716725df5143854abcb39842e115fa3e`. Main Releasability run
`29532246827` and CodeQL run `29532238824` passed for that SHA. Validation
included 4,722 unit tests, 454 integration tests with 31 declared
environment-only PostgreSQL skips, 4 end-to-end tests, 99.02% combined
coverage over 27,851 statements, MyPy over 954 source files, zero duplicate
clusters across 2,740 functions, PostgreSQL runtime proof, vulnerability
scanning, SBOM generation and attestation, keyless image signing, provenance
attestation, release identity validation, and CI signal evidence. The released
image is
`ghcr.io/sgajbi/lotus-idea@sha256:648879ec8cf725790e6c5628dcb41a397d7fdd207d1c19240dcaab265e9533e2`.
Repo-authored wiki source was published at wiki commit `25b0620`, and strict
parity returned zero differences. The implementation branch is absent locally
and remotely. Supported-feature posture remains unchanged, and issue `#542`
remains open for the other capability-owned multi-shape response families.

Issue `#548` continues issue `#542` through the high-cash signal family. One
capability-owned deterministic factory now executes the existing application
and domain services and serializes their real API DTOs for caller-supplied,
Core-backed, and evaluate-and-persist contracts. Both evaluation operations
publish `candidate_created`, `blocked`, `suppressed`, and `not_eligible` as
named HTTP 200 modes. Evaluate-and-persist additionally publishes `accepted`,
idempotent `replayed`, and `duplicate_candidate` persistence decisions, while
blocked, suppressed, and not-eligible evaluations explicitly retain
`persistence=null`. Focused HTTP tests prove every mode, including source
runtime cleanup and retry-safe duplicate handling, and the endpoint
certification gate enforces exact factory, ledger, generated OpenAPI, and cited
test parity. This is internal design modularity only. Core retains cash-weight
and source authority; live Core certification, Gateway/Workbench realization,
data-product promotion, and supported-feature promotion remain outside this
tranche.

PR `#549` merged issue `#548` by rebase to exact-main SHA
`d993eeefe97f5e6adfda68669cc82bc62c1cae9f`. Main Releasability run
`29536267571` and CodeQL run `29536268290` passed for that SHA. Validation
included 4,728 unit tests, 460 integration tests with 31 declared
environment-only PostgreSQL skips, 4 end-to-end tests, 99.02% combined
coverage over 27,916 statements, MyPy over 957 source files, zero duplicate
clusters across 2,755 functions, PostgreSQL runtime proof, container
vulnerability scanning, CycloneDX SBOM generation and attestation, keyless
image signing, provenance attestation, release identity validation, and CI
signal evidence. The released image is
`ghcr.io/sgajbi/lotus-idea@sha256:9b4e389e368370b44b904ce0ab6ac7687f3f943303c766924c7bb246e9a38219`;
the runtime `/version` response exposes the same commit, branch, repository,
build timestamp, run id, image build id, and digest-bound identity. Repo-authored
wiki source was published at wiki commit `4e28a13`, and strict parity returned
zero differences. The implementation branch is absent locally; remote cleanup
is verified during closure. A refreshed deterministic inventory leaves 26
multi-shape operations under issue `#542`, so Slice 10 remains partially
implemented and supported-feature posture remains unchanged.

Issue `#551` continues issue `#542` through the low-income /
liquidity-shortfall signal family. Capability-owned factories execute the
existing caller-supplied and Core-backed application paths and serialize the
real API response DTO. Both operations now publish named `candidate_created`,
`blocked`, `suppressed`, and `not_eligible` HTTP 200 modes. Candidate examples
retain both governed Core source products while omitting source routes and
content hashes. Focused HTTP tests add the previously missing caller
suppression and source-backed suppression/not-eligible proof, including source
runtime cleanup and no candidate persistence. Exact factory, endpoint-ledger,
generated OpenAPI, and cited-test parity is blocking. A shared example mapper
removes duplicate DTO serialization and source-reference fixture construction
from high-cash and low-income modules without moving policy or source logic out
of their capability owners.

This is internal design modularity inside the existing deployable. Core
retains cashflow and cash-movement authority. No persistence route, live Core
certification, Gateway/Workbench realization, data-product promotion, or
supported-feature promotion is introduced. README and supported-feature truth
remain unchanged by explicit scope decision. A refreshed deterministic scan
leaves 24 multi-shape operations under issue `#542`; Slice 10 remains partially
implemented.

PR `#552` merged issue `#551` by rebase to exact-main SHA
`342f1320750cd16ec8790f6f422afe1d8437407f`. Main Releasability run
`29539206978` passed on attempt 2 after attempt 1 encountered a transient GitHub
Actions API HTTP 503 while fetching job metadata; no code changed between
attempts. CodeQL run `29539202545` passed for the same SHA. Validation included
4,733 unit tests, 463 integration tests with 31 declared environment-only
PostgreSQL skips, 4 end-to-end tests, 99.02% combined coverage over 27,984
statements, MyPy over 961 source files, and zero duplicate clusters across 2,770
functions. The signed, attested image is
`ghcr.io/sgajbi/lotus-idea@sha256:c340fc2f9789708a25a9427475108de8413091b7cf3de1d4bf39fdd60bd101a8`;
its OCI labels, release manifest, digest-pinned deployment reference, and
runtime `/version` response reconcile commit, branch, repository, version,
build timestamp, run id, image build id, and image digest. Vulnerability scan,
CycloneDX SBOM and attestation, keyless signature, and provenance attestation
also passed. Repo-authored wiki source was published at wiki commit `aa6487a`,
and strict parity returned zero differences. The deterministic inventory remains
24 operations; supported-feature posture remains unchanged.

Issue `#555` continues issue `#542` through the bond-maturity / reinvestment
review signal family. Capability-owned factories execute the existing
caller-supplied and Core-backed application paths and serialize the real API
response DTO. Both operations publish named `candidate_created`, `blocked`,
`suppressed`, and `not_eligible` HTTP 200 modes. Candidate examples retain the
governed Core `HoldingsAsOf:v1` and `PortfolioMaturitySummary:v1` lineage while
omitting source routes and content hashes. Focused HTTP tests prove the
previously uncited caller suppression and source-backed suppression and
not-eligible behavior, including runtime cleanup and no candidate persistence.
Exact factory, endpoint-ledger, generated OpenAPI, and cited-test parity is a
blocking endpoint-certification contract.

This is design modularity inside the existing deployable, not a runtime split.
Core retains holdings, maturity-schedule, and maturity-summary authority;
Lotus Idea owns only deterministic opportunity detection and advisor-review
posture. No replacement-product recommendation, reinvestment advice,
suitability decision, persistence route, live Core certification,
Gateway/Workbench realization, data-product promotion, or supported-feature
promotion is introduced. README and supported-feature registry truth remain
unchanged by explicit scope decision. A refreshed deterministic scan leaves
22 multi-shape operations under issue `#542`; Slice 10 remains partially
implemented.

Issue `#557` continues issue `#542` through the allocation-drift / mandate-review
signal family. Capability-owned factories execute the existing caller-supplied
and Manage-backed application paths and serialize the real API response DTO.
Both operations publish named `candidate_created`, `blocked`, `suppressed`, and
`not_eligible` HTTP 200 modes. Source-backed candidate examples retain governed
Manage `PortfolioActionRegister:v1`, Performance
`MandatePerformanceHealthContext:v1`, and Risk `MandateRiskHealthContext:v1`
lineage while omitting source routes and content hashes. Focused HTTP tests prove
caller suppression and source-backed
suppression and not-eligible behavior, including runtime cleanup and no
candidate persistence. Exact factory, endpoint-ledger, generated OpenAPI, and
cited-test parity is a blocking endpoint-certification contract.

Named-success contract validators now register in
`scripts/endpoint_named_success_contracts.py`. The central endpoint gate remains
a stable orchestrator below its maintainability limit as additional capability
contracts are added. This is design modularity inside the existing deployable,
not a runtime split. Manage retains action-register, mandate implementation,
rebalance, and order authority; Performance and Risk retain their calculation
authority. Lotus Idea owns only deterministic opportunity detection and
advisor-review posture. No persistence route, live source certification,
Gateway/Workbench realization, data-product promotion, or supported-feature
promotion is introduced. README and supported-feature registry truth remain
unchanged by explicit scope decision. A refreshed deterministic scan leaves 20
multi-shape operations under issue `#542`; Slice 10 remains partially
implemented.

Issue `#559` continues issue `#542` through the underperformance-review signal
family. Capability-owned deterministic factories execute the existing
caller-supplied and Performance-backed application paths and serialize the
real API response DTO. Both operations publish named `candidate_created`,
`blocked`, `suppressed`, and `not_eligible` HTTP 200 modes. Candidate examples
retain Lotus Performance `ReturnsSeriesBundle:v1` identity while omitting
source routes and content hashes. Focused HTTP tests prove caller suppression,
source-backed suppression and not-eligible behavior, runtime cleanup, and the
absence of candidate persistence for non-candidate outcomes. Negative contract
tests prove that missing OpenAPI modes, ledger drift, or absent behavioral
evidence fail certification.

This is design modularity inside the existing deployable, not a runtime split.
Lotus Performance retains returns, active-return, benchmark-context, and
methodology authority; Lotus Idea owns only deterministic opportunity
detection and advisor-review posture. No persistence route, live source
certification, Gateway/Workbench realization, data-product promotion, or
supported-feature promotion is introduced. README and supported-feature
registry truth remain unchanged by explicit scope decision. A refreshed
deterministic scan leaves 18 multi-shape operations under issue `#542`; Slice
10 remains partially implemented.

Issue `#561` continues issue `#542` through the concentration-risk signal
family. Capability-owned deterministic factories execute the existing
caller-supplied and Risk-backed application paths and serialize the real API
response DTO. Both operations publish named `candidate_created`, `blocked`,
`suppressed`, and `not_eligible` HTTP 200 modes. Candidate examples retain
Lotus Risk `ConcentrationRiskReport:v1` identity while omitting source routes
and content hashes. Focused HTTP tests prove caller suppression, source-backed
suppression and not-eligible behavior, source runtime cleanup, and the absence
of candidate persistence for non-candidate outcomes. Negative contract tests
prove that missing OpenAPI modes or absent behavioral evidence fail
certification.

This is design modularity inside the existing deployable, not a runtime split.
Lotus Risk retains concentration calculations, methodology, and risk-product
authority; Lotus Idea owns only deterministic opportunity detection and
advisor-review posture. No persistence route, live source certification,
trade recommendation, rebalance/execution authority, Gateway/Workbench
realization, data-product promotion, or supported-feature promotion is
introduced. README and supported-feature registry truth remain unchanged by
explicit scope decision. A refreshed deterministic scan leaves 16 multi-shape
operations under issue `#542`; Slice 10 remains partially implemented.

Issue `#563` continues issue `#542` through the high-volatility signal family.
Capability-owned deterministic factories execute the existing caller-supplied
and Risk-backed application paths and serialize the real API response DTO.
Both operations publish named `candidate_created`, `blocked`, `suppressed`,
and `not_eligible` HTTP 200 modes. Candidate examples retain Lotus Risk
`RiskMetricsReport:v1` identity while omitting source routes and content
hashes. Focused HTTP tests prove caller suppression, source-backed suppression
and not-eligible behavior, source runtime cleanup, and the absence of candidate
persistence for non-candidate outcomes. Negative contract tests prove that
missing OpenAPI modes or absent behavioral evidence fail certification.

This is design modularity inside the existing deployable, not a runtime split.
Lotus Risk retains volatility, VaR, tracking-error calculations, methodology,
and risk-product authority; Lotus Idea owns only deterministic opportunity
detection and advisor-review posture. No persistence route, live source
certification, trade recommendation, rebalance/execution authority,
Gateway/Workbench realization, data-product promotion, or supported-feature
promotion is introduced. README and supported-feature registry truth remain
unchanged by explicit scope decision. A refreshed deterministic scan leaves
14 multi-shape operations under issue `#542`; Slice 10 remains partially
implemented.

Issue `#565` continues issue `#542` through the drawdown-review signal family.
Capability-owned deterministic factories execute the existing caller-supplied
and Risk-backed application paths and serialize the real API response DTO.
Both operations publish named `candidate_created`, `blocked`, `suppressed`,
and `not_eligible` HTTP 200 modes. Candidate examples retain Lotus Risk
`DrawdownAnalyticsReport:v1` identity while omitting source routes and content
hashes. Focused HTTP tests prove caller suppression, source-backed suppression
and not-eligible behavior, source runtime cleanup, and the absence of candidate
persistence for non-candidate outcomes. Negative contract tests prove that
missing OpenAPI modes or absent behavioral evidence fail certification.

This is design modularity inside the existing deployable, not a runtime split.
Lotus Risk retains drawdown calculation, period selection, methodology, and
risk-product authority; Lotus Idea owns only deterministic opportunity
detection and advisor-review posture. No persistence route, live source
certification, trade recommendation, rebalance/execution authority,
Gateway/Workbench realization, data-product promotion, or supported-feature
promotion is introduced. README and supported-feature registry truth remain
unchanged by explicit scope decision. A refreshed deterministic scan leaves
12 multi-shape operations under issue `#542`; Slice 10 remains partially
implemented.

Issue `#567` continues issue `#542` through the mandate-restriction signal
family. Capability-owned deterministic factories execute the existing
caller-supplied and Advise-backed application paths and serialize the real API
response DTO. Both operations publish named `candidate_created`, `blocked`,
`suppressed`, and `not_eligible` HTTP 200 modes. Caller-supplied evaluation
continues to accept only the governed Core `PortfolioStateSnapshot:v1`, Manage
`PortfolioActionRegister:v1`, or Advise `AdvisoryPolicyEvaluationRecord:v1`
source pair and reports the selected authority. Source-backed examples replace
only the Advise source port and retain redacted
`AdvisoryPolicyEvaluationRecord:v1` identity. Focused HTTP tests prove caller
and source-backed suppression/not-eligible behavior, source runtime cleanup,
and the absence of candidate persistence for non-candidate outcomes. Negative
contract tests prove that missing OpenAPI modes or absent behavioral evidence
fail certification.

This is design modularity inside the existing deployable, not a runtime split.
Core retains portfolio-state authority, Manage retains portfolio-action and
mandate-posture authority, and Advise retains policy-evaluation workflow and
restriction-diagnostic authority. Lotus Idea owns only deterministic
opportunity detection and compliance-review posture. No restriction clearance,
mandate change, suitability/policy/proposal approval, persistence route,
client publication, rebalance/order/execution authority, live source
certification, Gateway/Workbench realization, data-product promotion, or
supported-feature promotion is introduced. README and supported-feature
registry truth remain unchanged by explicit scope decision. A refreshed
deterministic scan leaves 10 multi-shape operations under issue `#542`; Slice
10 remains partially implemented.

Issue `#569` continues issue `#542` through the missing-risk-profile signal
family. Capability-owned deterministic factories execute the existing
caller-supplied and Advise-backed application paths and serialize the real API
response DTO. Both operations publish named `candidate_created`, `blocked`,
`suppressed`, and `not_eligible` HTTP 200 modes. Caller-supplied evaluation
accepts the governed Advise `AdvisoryPolicyEvaluationRecord:v1` source pair;
source-backed examples replace only the Advise source port and retain redacted
source identity. Focused HTTP tests prove caller and source-backed
suppression/not-eligible behavior, source runtime cleanup, and the absence of
candidate persistence for non-candidate outcomes. Negative contract tests prove
that missing OpenAPI modes or absent behavioral evidence fail certification.

This is design modularity inside the existing deployable, not a runtime split.
Advise retains client risk-profile workflow, effective/current/expired and
review-due diagnostic truth, risk-capacity, suitability, policy-evaluation, and
product authority. Lotus Idea owns only deterministic detection, suppression,
eligibility, source-safe references, and advisor-review posture. No client
risk-profile approval or creation, risk-capacity determination, suitability or
policy approval, persistence route, client publication, rebalance/order/
execution authority, live source certification, Gateway/Workbench realization,
data-product promotion, or supported-feature promotion is introduced. README
and supported-feature registry truth remain unchanged by explicit scope
decision. A refreshed deterministic scan leaves eight multi-shape operations
under issue `#542`; Slice 10 remains partially implemented.

Issue `#571` continues issue `#542` through the missing-benchmark signal
family. Capability-owned deterministic factories execute the existing
caller-supplied and Core-backed application paths and serialize the real API
response DTO. Both operations publish named `candidate_created`, `blocked`,
`suppressed`, and `not_eligible` HTTP 200 modes. Caller-supplied evaluation
accepts only Core `BenchmarkAssignment:v1` evidence; source-backed examples
replace only `CoreBenchmarkAssignmentSourcePort` and retain redacted source
identity. Focused HTTP tests prove caller and source-backed
suppression/not-eligible behavior, source-runtime cleanup, and the absence of
candidate persistence for non-candidate outcomes. Negative contract tests prove
that missing OpenAPI modes or absent behavioral evidence fail certification.

This is design modularity inside the existing deployable, not a runtime split.
Core retains benchmark-assignment, portfolio, and benchmark-methodology
authority. Lotus Idea owns only deterministic detection, suppression,
eligibility, source-safe references, and advisor-review posture. No benchmark
assignment, methodology approval, performance calculation, persistence route,
client publication, rebalance/order/execution authority, live source
certification, Gateway/Workbench realization, data-product promotion, or
supported-feature promotion is introduced. README and supported-feature
registry truth remain unchanged by explicit scope decision. The existing
platform named-success guardrail was reused without a new skill/context change;
a refreshed deterministic scan leaves six multi-shape operations under issue
`#542`; Slice 10 remains partially implemented.

Issue `#573` continues issue `#542` through the missing-suitability signal family.
Capability-owned factories execute the existing caller-supplied and Advise-backed
application paths, serialize the real response DTO, and publish named
`candidate_created`, `blocked`, `suppressed`, and `not_eligible` HTTP 200 modes.
Focused HTTP tests prove non-candidate no-persistence and source-runtime cleanup;
negative contract tests reject missing modes and behavior evidence.

Advise retains suitability, policy, proposal, sign-off, and client-publication
posture authority. Idea owns only deterministic evidence-gap detection,
suppression, eligibility, and compliance-review routing. No suitability or policy
approval, persistence route, runtime split, client publication, Gateway/Workbench
realization, data-product promotion, or supported-feature promotion is introduced.
README and supported-feature truth remain unchanged. The existing platform
named-success guardrail is reused; four multi-shape operations remain under #542.

Issue `#575` continues issue `#542` through the two downstream-submission
operations. Capability-owned factories execute the real conversion-intent and
report-evidence application use cases through deterministic no-I/O adapters,
then serialize `DownstreamSubmissionApiResponse`. Both routes publish accepted,
rejected, accepted-replayed, and rejected-replayed HTTP `200` modes, with
`reconciliation_required` separately published as HTTP `202`. The endpoint
ledger, generated OpenAPI, and required HTTP behavior evidence are enforced by
the shared status-aware named-success validator; negative tests reject a
missing `202` mode or behavior reference.

Idea retains only claim-before-call, local finalization, replay, uncertain
outcome preservation, reconciliation, and audit posture. Advise/Manage retain
conversion workflow and authoritative outcome authority; Report retains
materialization authority. No downstream route proof, downstream record,
automatic uncertain-call retry, suitability, execution, client publication,
Gateway/Workbench realization, data-product promotion, or supported-feature
promotion is introduced. README and supported-feature truth remain unchanged;
the status-aware repository validator is the durable improvement. A refreshed
deterministic scan leaves four multi-shape operations under #542.

Issue `#577` continues issue `#542` through the advisor-review-queue success
contract. Its capability-owned factory persists a deterministic internal
high-cash candidate through the existing use case, invokes the real queue
projection, and serializes `BusinessReviewQueueResponse`. Generated OpenAPI
and the endpoint ledger publish exact named HTTP `200` `itemsAvailable` and
`noItemsAvailable` modes; focused negative tests reject either a missing mode
or an absent empty-queue behavior reference.

This hardens the bounded, entitlement-scoped Idea queue read only. It neither
changes the snapshot/as-of policy nor grants suitability, compliance, mandate,
execution, client-publication, Workbench, data-product, or supported-feature
authority. README and supported-feature registry truth remain unchanged by
explicit scope decision. The generalized named-response helper now supports
the HTTP method of the governed operation, avoiding a POST-only hidden
assumption without introducing a runtime split.

PR `#543` merged issue `#539` to `main` at
`f6e2365eaec5f4f0184d5985e5b5fcc641b4883b`. Main Releasability run
`29528824505` passed, including lint, typecheck, security, architecture,
OpenAPI, 4,717 unit tests, integration, end-to-end, PostgreSQL runtime proof,
99% combined coverage, container runtime smoke, vulnerability scan, SBOM
generation, commit-tagged image publication, digest inspection, keyless
signing, provenance attestation, SBOM attestation, release identity validation,
and CI signal evidence. The released image is
`ghcr.io/sgajbi/lotus-idea@sha256:4e66269aa389f73ef7faf704f8006b521f33f757813f4696ea87c1fbacf4842c`.
CodeQL run `29528818845` also passed for the exact merge SHA. Repo-authored
wiki source was published in wiki commit `33a7b8a`, and strict parity returned
zero differences. Supported-feature posture remains unchanged.

PR `#533` merged issue `#532` to `main` at
`373bda0bc2203cb4e1f2ab0d011d8dd9890369ad`. Main Releasability run
`29520564704` passed on attempt 2, including lint, typecheck, security,
architecture, OpenAPI, 4,705 unit tests, integration, end-to-end, PostgreSQL
runtime proof, 99% combined coverage, container runtime smoke, vulnerability
scan, SBOM generation, commit-tagged image publication, digest inspection,
keyless signing, provenance attestation, SBOM attestation, and release identity
validation. Attempt 1 failed only while GHCR returned `unknown blob` during
layer publication; rerunning the failed release job for the same exact source
SHA succeeded without a code change. The released image is
`ghcr.io/sgajbi/lotus-idea@sha256:b3df918b60770b6e3b54251ffacd11705a9a71fe47b6fdc8ce01b71531dc734c`.
CodeQL run `29520557719` also passed for the exact merge SHA. Repo-authored
wiki source was published after merge and strict parity returned zero
differences. Supported-feature posture remains unchanged.

The conversion-intent and conversion-outcome endpoints expose the Slice 12
internal conversion workflow foundation over persisted, review-approved
candidates. They require `Idempotency-Key` and conversion-specific
capabilities, record source-authority mapped conversion intent/outcome audit
evidence, enforce target-source authority for downstream outcomes, never grant
Advise/Manage/Report workflow authority, suitability, execution, or
client-communication authority, and keep `supportedFeaturePromoted=false`.
`durableStorageBacked` follows the active repository provider.

The advisor review queue endpoint exposes the Slice 07 deterministic queue
projection over persisted candidate snapshots. It requires
advisor role plus `idea.review.queue.read` capability, returns ranked items
plus exclusions, accepts optional tenant/book/portfolio/client query filters
for scope-aware projection, and keeps `supportedFeaturePromoted=false`.
`durableStorageBacked` follows the active repository provider.

`lotus-gateway` now publishes the first bounded read-only idea routes on main:
`GET /api/v1/ideas/review-queues/advisor` and
`GET /api/v1/ideas/candidates/{candidate_id}`. Gateway forwards caller
context, caller entitlement-scope, and correlation headers to `lotus-idea`,
preserves `lotus-idea` ranking, source references, durable-storage posture, and
unsupported-feature posture, blocks any upstream `supportedFeaturePromoted=true` response, and
does not generate, rank, enrich, certify, or promote ideas locally. Workbench
PR #391 now consumes these read-only Gateway paths for bounded queue/detail
rendering. This is not full Workbench live proof, data-product certification,
full source-ingestion certification, client-ready publication, or
supported-feature promotion.

The AI explanation endpoint exposes the Slice 09 internal fallback/verifier
foundation over persisted candidate evidence. It requires
`idea.ai-explanation.evaluate` plus `Idempotency-Key`, returns redacted
evidence only, accepts only the governed `lotus-ai:idea-explanation:v1` /
`v1` / `lotus-ai:governed-verifier:v1` workflow-pack contract, rejects
unregistered pack identities with product-safe `400 invalid_ai_workflow_pack`
before candidate lookup or lineage persistence, blocks unsupported claims and
forbidden actions, replays same-key/same-request submissions without duplicate
lineage writes, rejects same-key/different-request reuse with product-safe
`409 idempotency_conflict`, never calls providers or executes `lotus-ai`
runtime workflows, never certifies runtime AI lineage-store proof, never grants
downstream authority, and keeps `durableStorageBacked=false`,
`lotusAiRuntimeExecuted=false`, and `supportedFeaturePromoted=false`.

Issue `#520` corrects the endpoint certification boundary after signed
attestation support. Production-like profiles accept workflow output only when
`producerRunId`, exact `producerExecutionOutput`, and a verified Lotus AI
`runAttestation` form one bound bundle. OpenAPI publishes separate named
local/test-fixture and verified-attested success examples. The endpoint
certification gate requires the verified response posture and exact HTTP
integration evidence, preventing the ledger from regressing to the former
reject-all description. Idea still does not call a provider, own AI runtime
infrastructure, grant downstream authority, or promote a supported feature.

Implementation files:

1. `src/app/api/idea_signals.py`: FastAPI DTOs, authorization mapping,
   product-safe errors, idempotency-conflict handling, OpenAPI examples, and
   route registration.
2. `src/app/api/missing_suitability_signals.py`: bounded missing
   suitability-context signal API over caller-supplied Advise policy-evaluation
   evidence with product-safe authorization, source-redacted response
   projection, OpenAPI examples, and operation events.
3. `src/app/api/missing_benchmark_signals.py`: bounded missing-benchmark
   signal API over caller-supplied Core benchmark-assignment evidence with
   product-safe authorization, source-redacted response projection, OpenAPI
   examples, and operation events.
4. `src/app/api/low_income_signals.py`: bounded low-income /
   liquidity-shortfall signal API over caller-supplied Core cashflow projection
   and cash movement evidence with product-safe authorization, source-redacted
   response projection, OpenAPI examples, and operation events.
5. `src/app/api/bond_maturity_signals.py`: bounded bond-maturity /
   reinvestment review signal API over caller-supplied Core
   `PortfolioMaturitySummary:v1` maturity evidence with product-safe
   authorization, source-redacted response projection, OpenAPI examples, and
   operation events.
6. `src/app/api/concentration_risk_signals.py` and
   `src/app/api/high_volatility_signals.py`: bounded Risk-backed signal APIs
   over caller-supplied Lotus Risk concentration and volatility evidence with
   shared product-safe authorization, source-redacted response projection,
   application-backed named OpenAPI examples, operation events, and no local
   risk-methodology authority. Capability-owned example and endpoint contract
   modules enforce caller/source success-mode parity without adding a runtime
   boundary.
7. `src/app/api/drawdown_review_signals.py`: bounded drawdown-review signal
   API over caller-supplied Lotus Risk drawdown analytics evidence with shared
   product-safe authorization, source-redacted response projection, OpenAPI
   examples, operation events, and no local Risk drawdown calculation or
   risk-methodology authority.
8. `src/app/api/allocation_drift_signals.py`: bounded allocation-drift /
   mandate-review signal API over caller-supplied Lotus Manage action-register
   and mandate-health source-ref posture with shared product-safe
   authorization, source-redacted response projection, OpenAPI examples,
   operation events, and no local drift calculation, mandate approval,
   rebalance action, order, or downstream authority.
9. `src/app/api/signal_api_support.py`: shared signal API route metadata,
   permission, source-authority, operation outcome, and product-safe 400/403
   `ProblemDetails` OpenAPI response metadata used by caller-supplied signal
   endpoints for design modularity without a new runtime service boundary.
10. `src/app/application/high_cash_signal.py`: application command and policy
   orchestration over framework-free domain evaluation and internal
   evaluate-and-persist behavior.
11. `src/app/domain/signal_evaluation.py`: existing deterministic high-cash
   domain policy reused by the endpoint.
12. `src/app/domain/persistence.py`: internal idempotency/audit repository used
   by the evaluate-and-persist and lifecycle transition API foundations.
13. `src/app/errors.py`: RFC-7807-shaped problem detail body with stable
    `type`, `status`, `code`, `title`, and `detail` fields.
14. `src/app/api/problem_details.py`: shared workflow/operator API
    `ProblemDetails` OpenAPI metadata and common product-safe permission and
    request-failure response helpers, used for design modularity without adding
    a runtime service boundary.
15. `docs/operations/endpoint-certification-ledger.json`: machine-readable
    endpoint certification evidence for the new route.
16. `src/app/api/review_workflow.py`: review-action and feedback DTOs,
    authorization/scope mapping, product-safe errors, idempotency-conflict
    handling, OpenAPI examples, and route registration.
17. `src/app/api/review_queue/`: audience-specific business queue routes,
    operator exception posture, request mapping, entitlement narrowing,
    product-safe errors, OpenAPI examples, and route registration.
18. `src/app/api/caller_headers.py`: shared API caller-header parsing used by
    signal and review routes.
19. `src/app/api/candidate_lifecycle.py`: lifecycle transition DTOs,
    authorization mapping, product-safe errors, idempotency-conflict handling,
    OpenAPI examples, and route registration.
20. `src/app/application/candidate_lifecycle.py`: application command and
    idempotency payload construction for lifecycle transitions.
21. `src/app/api/candidate_detail.py`: source-safe candidate detail DTOs,
    authorization and caller-scope mapping, redacted source projection,
    product-safe errors, OpenAPI examples, and route registration.
22. `src/app/application/candidate_detail.py`: persisted candidate snapshot
    lookup and access-scope matching through the governed repository port.
23. `src/app/api/candidate_evidence_replay.py`: evidence replay DTOs,
    authorization mapping, product-safe errors, OpenAPI examples, operation
    events, and route registration.
24. `src/app/application/candidate_evidence_replay.py`: command validation and
    replay orchestration through the governed repository port.
25. `src/app/api/ai_governance.py`: AI explanation DTOs, authorization
    mapping, redacted response projection, product-safe errors, OpenAPI
    examples, and route registration.
26. `src/app/application/ai_governance.py`: persisted candidate snapshot
    lookup plus deterministic fallback/verifier orchestration without provider
    execution or durable persistence claims.
27. `src/app/api/conversion_governance.py`: conversion intent/outcome DTOs,
    authorization mapping, product-safe errors, idempotency-conflict handling,
    OpenAPI examples, and route registration.
28. `src/app/application/conversion_workflow.py`: application commands,
    idempotency payload construction, repository precheck, and domain
    invocation for conversion intent/outcome workflow.
29. `tests/integration/test_review_workflow_api.py`: certified API behavior
   evidence for lifecycle transition, review action, feedback, and conversion
   foundations.
30. `tests/integration/test_review_queue_api.py`: certified API behavior
    evidence for advisor queue projection.
31. `tests/integration/test_candidate_detail_api.py`: certified API behavior
    evidence for source-safe detail projection, workflow summaries, permission,
    missing candidate, and no-authority promotion.
32. `tests/integration/test_candidate_evidence_replay_api.py`: certified API
    behavior evidence for matched, stale-source, hash-mismatch, permission,
    missing candidate, invalid request, and no-authority replay posture.
33. `tests/integration/test_ai_governance_api.py`: certified API behavior
    evidence for AI fallback, verifier acceptance, blocked output, permission,
    missing candidate, invalid state, and forbidden metadata.
34. `tests/integration/test_missing_suitability_signal_api.py`: certified API
    behavior evidence for candidate creation, blocked publication posture,
    permission denial, source-redacted response projection, and no-authority
    promotion.
35. `tests/integration/test_missing_benchmark_signal_api.py`: certified API
    behavior evidence for missing-benchmark candidate creation, ready-assignment
    not-eligible posture, stale-source blocking, permission denial,
    source-redacted response projection, and no-authority promotion.
36. `tests/integration/test_low_income_signal_api.py`: certified API behavior
    evidence for low-income / liquidity-shortfall candidate creation,
    above-threshold not-eligible posture, stale-source blocking, permission
    denial, source-redacted response projection, and no-authority promotion.
37. `tests/integration/test_bond_maturity_signal_api.py`: certified API
    behavior evidence for bond-maturity / reinvestment review candidate
    creation, outside-window not-eligible posture, stale-source blocking,
    permission denial, source-redacted response projection, and no-authority
    promotion.
38. `tests/integration/test_concentration_risk_signal_api.py` and
    `tests/integration/test_high_volatility_signal_api.py`: certified API
    behavior evidence for Risk-backed review candidate creation, duplicate
    suppression, below-threshold not-eligible posture, incomplete/stale/source
    blocking, source-backed non-candidate outcomes, runtime cleanup, permission
    denial, and no-authority promotion.
39. `tests/integration/test_drawdown_review_signal_api.py`: certified API
    behavior evidence for drawdown-review candidate creation, below-threshold
    not-eligible posture, non-ready source blocking, stale-source blocking,
    permission denial, and no-authority promotion.
40. `tests/integration/test_allocation_drift_signal_api.py`: certified API
    behavior evidence for allocation-drift / mandate-review candidate creation,
    below-threshold not-eligible posture, store-wide Manage supportability
    blocking, non-ready and stale source blocking, permission denial,
    source-redacted response projection, and no-authority promotion.
41. `tests/integration/test_api_operation_events.py`: bounded operation-event
    evidence for certified signal endpoint posture.
42. `scripts/endpoint_status_contracts.py` and
    `tests/integration/data_lifecycle/test_operation_events.py::test_data_lifecycle_api_emits_bounded_permission_event`:
    implementation-quality enforcement for public
    `implemented_not_certified` operations. The gate requires the same
    capability, caller-context, product-safe error, operation-event,
    integration-test, and OpenAPI evidence as certified operations, plus
    machine-readable external blockers and explicit not-certified,
    no-promotion success posture.

## Current Contract

The evaluate endpoint returns deterministic posture only:

1. `candidate_created` when all source evidence is current, entitlement is
   allowed, and the source-reported signal evidence satisfies the relevant
   policy threshold, review window, or evidence-gap policy,
2. `blocked` for stale/missing source evidence, missing source-reported metric,
   or entitlement denial,
3. `suppressed` for duplicate candidate evidence,
4. `not_eligible` when source-reported evidence is current but below the
   relevant policy threshold or outside the review window.

The evaluate endpoint is permissioned by advisor role and
`idea.signal.evaluate` capability. The evaluate-and-persist endpoint is permissioned by
`idea.candidate.persist` and requires `Idempotency-Key`. Validation,
permission, and idempotency-conflict failures return product-safe Problem
Details.

The review-action endpoint is permissioned by `idea.review.record` plus one
recognized review actor role. The feedback endpoint is permissioned by
`idea.feedback.record` plus one recognized review actor role. Both endpoints
require trusted platform caller-context tenant/book/portfolio/client
entitlement headers covering the persisted candidate scope. Request scope
fields are rejected; runtime governance evaluates persisted candidate access
scope against trusted caller entitlements.
Scope, permission, missing candidate, idempotency conflict, and invalid
candidate-state failures return product-safe Problem Details.

The advisor, portfolio-manager, and compliance review queue endpoints use
role-specific capabilities and select only their responsible review posture.
The advisor route requires a
timezone-aware `evaluatedAtUtc` query parameter, accepts optional
tenant/book/portfolio/client scope filters, applies platform caller-context
entitlement scope headers automatically when present, rejects query scopes
outside caller entitlements fail-closed, excludes persisted candidates outside
the effective scope with `access_scope_mismatch`, and uses candidate
`createdAtUtc` as the inclusive as-of visibility boundary. Page metadata
returns an opaque `snapshotToken`; continuation offsets require that token,
while malformed tokens return `400 invalid_review_queue_snapshot_token` and
changed visible queue state returns `409 review_queue_snapshot_conflict`.
Source business dates and evidence generation timestamps remain governed by
their source contracts rather than being reinterpreted as queue creation time.

The candidate detail endpoint is permissioned by
advisor/operator role plus `idea.candidate.detail.read` capability. It returns
source-safe details for an existing candidate only when any provided platform
caller-context entitlement scope matches the persisted candidate scope, and
returns product-safe Problem Details for permission, validation, out-of-scope,
or missing-candidate failures.

The candidate evidence replay endpoint is permissioned by
`idea.candidate.evidence.replay` plus operator role. It requires non-empty
`currentSourceRefs`, compares current source refs against persisted evidence
hash posture, returns product-safe replay status, and returns Problem Details
for permission, validation, or missing-candidate failures.

The AI explanation endpoint is permissioned by
`idea.ai-explanation.evaluate` and requires `Idempotency-Key`. It accepts a
governed workflow-pack reference, approved metadata, optional workflow output,
and a requested timestamp. If no workflow output is supplied, it returns
deterministic fallback. If workflow output is supplied, it verifies
source-product claim support and forbidden action policy, returning a blocked
posture for unsupported claims or prohibited actions. Same-key/same-request
submissions replay without duplicate lineage writes; same-key/different-request
reuse returns product-safe `409 idempotency_conflict`; distinct-key AI
request-id replay/conflict remains governed by the lineage store. Missing
candidates, permission failure, invalid request shape, missing/blank
`Idempotency-Key`, forbidden metadata, and invalid candidate lifecycle posture
return product-safe Problem Details.

The lifecycle transition endpoint is permissioned by
`idea.candidate.lifecycle.transition` and requires `Idempotency-Key`. It accepts
only target statuses allowed by the domain lifecycle graph and returns
product-safe Problem Details for validation, permission, missing candidate,
idempotency conflict, or invalid lifecycle transition failures.

The conversion-intent endpoint is permissioned by
`idea.conversion.intent.record` and requires `Idempotency-Key`. It accepts only
persisted candidates that are already approved for conversion and returns
product-safe Problem Details for validation, permission, missing candidate,
idempotency conflict, or invalid conversion-state failures.

The conversion-outcome endpoint is permissioned by
`idea.conversion.outcome.record` and requires `Idempotency-Key`. It records
downstream outcome posture only when the reporting `sourceSystem` matches the
conversion target source authority and returns product-safe Problem Details for
validation, permission, missing intent, idempotency conflict, or wrong-source
failures.

The source-ingestion run-once endpoint is permissioned by
`idea.source-ingestion.run` and operator role. It executes the bounded
high-cash source-ingestion batch foundation only when durable repository,
manifest, and Core source configuration are present. It returns aggregate
decision counts only and returns blocked posture without mutation when runtime
configuration is absent or invalid.

`supportedFeaturePromoted` is always `false` in these foundation endpoints.
`durableStorageBacked` follows the active repository provider for
repository-backed foundation endpoints: allowed `local`/`test` process-local
runtime reports `false`, and `LOTUS_IDEA_DATABASE_URL` runtime reports `true`.
Production-like profiles without durable storage fail closed before mutation. The endpoints are
certified as API foundations but are not supported business features because
source-worker certification beyond bounded live proof, Workbench proof,
data-product certification, runtime trust telemetry, downstream realization
proof, and supported-feature registration are not implemented yet. The bounded read-only Gateway
publication listed above is integration foundation only, not support.

## Required Work

1. Implement route families approved by prior slices.
2. Add complete OpenAPI descriptions, examples, error cases, degraded cases,
   unsupported-evidence cases, idempotency behavior, and entitlement behavior.
3. Update endpoint certification ledger.
4. Extend `lotus-gateway` contracts and routes without Gateway-side idea
   generation or ranking when additional read or workflow surfaces become
   implementation-backed.

## Remaining Work

1. Extend the current Core high-cash source-port and conservative HTTP adapter
   into live source contract proof once Core publishes an explicit
   source-reported cash-weight field; keep all official cash/holding
   calculations in `lotus-core`.
2. Extend Gateway coverage beyond the first read-only advisor queue and
   candidate detail publication where needed, preserving `lotus-idea` source
   authority and preventing Gateway-side ranking or generation.
3. Extend the bounded Workbench read-only review surface into full live,
   entitlement-denied, mutation, and demo proof before any supported UI or demo
   claim.
4. Add deployment and recovery proof for PostgreSQL-backed API state.
5. Add data-product trust telemetry, platform mesh certification, and
   supported-feature promotion only after runtime proof exists.
6. Add additional route families for evidence packs and supportability after
   their storage and orchestration slices are implementation-backed.

## Platform Follow-Up

The local slice exposed a reusable scaffold concern: FastAPI business route
registration must stay compatible with Prometheus instrumentation. The current
`lotus-idea` route is registered directly on the app before instrumentation.
Platform scaffold follow-up is tracked in
`sgajbi/lotus-platform#420`.

## Validation Evidence

Focused validation passed for the current foundation:

1. `python -m pytest tests/unit/test_high_cash_application.py tests/integration/test_high_cash_signal_api.py tests/unit/test_service_contract.py -q`
2. `python -m ruff check src/app/api/idea_signals.py src/app/application/high_cash_signal.py src/app/errors.py src/app/main.py tests/unit/test_high_cash_application.py tests/integration/test_high_cash_signal_api.py tests/unit/test_service_contract.py`
3. `python -m mypy --config-file mypy.ini`
4. `python scripts/openapi_quality_gate.py`
5. `python scripts/endpoint_certification_gate.py`
6. `.venv\Scripts\python.exe -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_service_contract.py -q` passed with `16 passed` after adding evaluate-and-persist API certification and blank idempotency-key hardening.
7. `make check` passed with `187` unit tests plus lint, format, typecheck,
   architecture, OpenAPI, supported-feature, endpoint-certification,
   data-mesh, and contract gates.
8. `make ci` passed with `19` integration tests, `2` e2e tests, `187` unit
   tests under coverage, coverage gate at `99.18%`, and dependency audit.
9. `.venv\Scripts\python.exe -m pytest tests\integration\test_review_workflow_api.py tests\unit\test_service_contract.py -q` passed with `17 passed` after adding review-action and feedback API certification.
10. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` passed
    after adding review-action and feedback route ledger evidence.
11. `.venv\Scripts\python.exe -m pytest tests\integration\test_review_queue_api.py -q`
    passed with `4 passed` after adding advisor review queue API certification.
12. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` passed
    after adding advisor review queue route ledger evidence.
13. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_service_contract.py tests\integration\test_review_workflow_api.py -q`
    passed with `29 passed` after adding lifecycle transition API
    certification.
14. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` and
    `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` passed after
    adding lifecycle transition route ledger evidence.
15. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `189` unit tests.
16. `make ci` passed with `39` integration tests, `2` e2e tests, `189` unit
    tests under coverage, coverage gate at `99.14%`, and dependency audit
    reporting no known vulnerabilities.
17. `make docker-build` passed for `backend-service:ci-test`.
18. `.venv\Scripts\python.exe -m pytest tests\unit\test_conversion_governance.py tests\unit\test_idea_persistence.py tests\integration\test_review_workflow_api.py -q`
    passed with `42 passed` after adding conversion intent/outcome API
    foundations, repository idempotency persistence, and outcome source
    authority enforcement.
19. `python -m pytest tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py`
    passed with `8 passed` after adding the AI explanation evaluator API
    foundation and operation-event coverage.
20. `python -m ruff check src/app/application/ai_governance.py src/app/api/ai_governance.py tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py`
    passed after adding the AI API route, DTOs, and tests.
21. `make ci` passed after adding the AI explanation API foundation with `59`
    integration tests, `2` e2e tests, `218` unit tests, coverage gate at
    `99.17%`, and dependency audit reporting no known vulnerabilities.
22. `python -m pytest tests/integration/test_candidate_detail_api.py tests/integration/test_api_operation_events.py tests/unit/test_service_contract.py -q`
    passed with `12 passed` after adding the candidate detail API foundation,
    source-redaction assertions, workflow summary assertions,
    permission/not-found behavior, endpoint-ledger contract, and bounded
    operation-event coverage.
23. `.venv\Scripts\python.exe -m pytest tests\integration\test_candidate_evidence_replay_api.py tests\integration\test_api_operation_events.py -q`
    passed with `9 passed` after adding the evidence replay API foundation,
    OpenAPI/ledger examples, matched/stale/hash-mismatch/not-found/permission
    behavior, and bounded `candidate_evidence_replay` operation-event coverage.
24. `lotus-gateway` PR #467 merged to main at
    `c32c7ebda5deac798a6c04675c35df63f36a79cb` with read-only Gateway
    publication for advisor queue and candidate detail. Gateway validation
    passed `make lint`, `make check`, Feature Lane, Quality Baseline, PR Merge
    Gate, Main Releasability, and wiki publication.
25. `.venv\Scripts\python.exe -m pytest tests/unit/test_review_queue_application.py tests/integration/test_review_queue_api.py tests/unit/test_postgres_repository.py`
    passed with `16 passed` after adding scope-aware advisor queue filtering,
    product-safe blank-scope validation, and PostgreSQL candidate-scope
    serialization evidence.
26. `.venv\Scripts\python.exe -m pytest tests\integration\test_low_income_signal_api.py tests\integration\test_api_operation_events.py tests\unit\test_service_contract.py -q`
    passed with `21 passed` after adding the low-income / liquidity-shortfall
    caller-supplied API foundation, endpoint ledger contract, and bounded
    signal-evaluation operation-event coverage.
27. `make endpoint-certification-gate`, `make openapi-gate`, and
    `make opportunity-archetype-contract-gate` passed after adding
    `POST /api/v1/idea-signals/low-income/evaluate`, API certification ledger
    evidence, and low-income archetype contract evidence.
28. `make lint`, `make typecheck`, `make documentation-contract-gate`,
    `make supported-features-gate`, `make test-integration`, `make test-e2e`,
    and `make check` passed after the low-income API slice. `make check`
    included `1774` unit tests; `make test-integration` passed with `163`
    integration tests and `5` PostgreSQL-runtime tests skipped; `make test-e2e`
    passed with `2` smoke tests.
29. `.venv\Scripts\python.exe -m pytest tests\unit\test_api_problem_details.py tests\integration\test_review_workflow_api.py -q`
    passed with `27 passed` after adding shared workflow/operator
    `ProblemDetails` OpenAPI metadata for lifecycle, review, feedback,
    conversion, and report evidence-pack routes.
30. `.venv\Scripts\python.exe -m ruff check src\app\api\problem_details.py src\app\api\candidate_lifecycle.py src\app\api\review_workflow.py src\app\api\conversion_governance.py src\app\api\report_evidence.py tests\unit\test_api_problem_details.py`,
    `.venv\Scripts\python.exe -m mypy --config-file mypy.ini`,
    `.venv\Scripts\python.exe scripts\openapi_quality_gate.py`,
    `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py`, and
    `.venv\Scripts\python.exe scripts\architecture_boundary_gate.py --mode blocking`
    passed for the shared API error-model polish.
31. `make test-coverage` passed with `1832` unit tests, `199` integration
    tests and `5` PostgreSQL-runtime tests skipped, `2` e2e tests, and
    coverage gate `99.00`.
32. `make ci` passed after the coverage fix, including repository contract
    gates, OpenAPI, endpoint certification, architecture boundary, migrations,
    integration/e2e/unit coverage, coverage gate `99.00`, and dependency audit
    with no known vulnerabilities.
33. Issue `#520` adds named OpenAPI success examples for local/test fixture and
    verified attested output, cites the attested API integration path in the
    endpoint ledger, and adds mutation-tested certification enforcement for
    `lotus_ai_attestation_verified`, `lotusAiRuntimeExecuted=true`,
    no downstream authority, and no supported-feature promotion.
34. Final `make check` and `make ci` pass with `4694` unit tests, `453`
    integration tests plus `31` declared environment-only PostgreSQL skips,
    `4` E2E tests, `99.01%` combined coverage over `27712` statements, strict
    MyPy over `941` source files, zero duplicate clusters across `2715`
    functions, and no known dependency vulnerabilities.
35. PR `#521` merged by rebase at exact-main SHA
    `da061fc65648e8224e9e1847ef9cf1e7772b365e`; Main Releasability
    `29506764366` and CodeQL `29506757015` passed. Release digest
    `sha256:37d4cf724e53791e30af1ad2ff58b9074706261586df03d9e3fd7bf0e068e5dc`
    has matching image/version metadata and release evidence. Wiki publication
    `5c9b740` has zero drift, issue `#520` is closed, and the implementation
    branch is absent locally and remotely.
36. Issue `#523` closes an implementation-quality bypass for
    `implemented_not_certified` public operations. The shared certification
    gate now enforces capability ownership, Gateway/Workbench boundaries,
    product-safe `403`, bounded operation events, integration and negative
    tests, and OpenAPI caller context for both implemented statuses.
    Capability-owned status contracts additionally require machine-readable
    external certification blockers and truthful not-certified/no-promotion
    success examples in the ledger and generated OpenAPI.
37. PR `#524` merged by rebase at exact-main SHA
    `92517e55833d2691497aa3307f6651870a3443d6`; Main Releasability
    `29510553267` and CodeQL `29510545264` passed. Release digest
    `sha256:f65ee9f606ba11a0dc20ec6d7e550b9f9c9865b6ba452c3e962aaacc4524c02d`
    has matching OCI and `/version` identity, scan, SBOM, signature,
    provenance and SBOM attestations, release manifest, and digest-pinned
    runtime smoke. Wiki publication `19358a8` has zero drift. Runtime behavior,
    API schema, persistence, Gateway/Workbench realization, and
    supported-feature posture did not change.
38. Issue `#526` removes a semantically stale AI explanation readiness
    Swagger example. The default success example now comes from the same
    deterministic application snapshot and API serializer as the runtime
    route. Complete-structure certification checks bind all control fields and
    blockers across the code-owned response, endpoint ledger, and generated
    OpenAPI; schema validity alone is no longer sufficient for this endpoint.
39. This increment is design modularity inside the existing deployable.
    Authorization, operation events, response schema, persistence, Lotus AI
    ownership, model-risk approval, Gateway/Workbench realization, and
    supported-feature posture remain unchanged. The wider example-shape
    inventory is retained for endpoint-by-endpoint review because alternate
    success modes and dynamic fields must not be bulk-normalized.
40. Final local validation for issue `#526` passed `make check` and
    `make ci`: `4,699` unit tests, `454` integration tests with `31`
    declared environment-only PostgreSQL skips, `4` E2E tests, `99.01%`
    combined coverage over `27,714` statements, MyPy over `942` source
    files, zero duplicate clusters across `2,716` functions, and no known
    dependency vulnerabilities.
41. PR `#527` merged by rebase at exact-main SHA
    `9e265cdc4d4fbaabf55079d649bfd6d1633cca61`; Main Releasability
    `29514317977` and CodeQL `29514310719` passed. Release digest
    `sha256:84159920866d5d05bc6b33df4c6bb6a6d3239d6ca2f7fd3413572330e7900a76`
    has matching OCI and `/version` identity, vulnerability scan, SBOM,
    keyless signature, provenance and SBOM attestations, release manifest,
    and digest-pinned runtime smoke. Strict wiki parity is zero and no
    closure-only wiki publication is needed. Issue `#526` is closed and its
    implementation branch is absent locally and remotely.
42. Issue `#529` extends complete response certification from the single-mode
    readiness diagnostic to every executable AI explanation evaluation success
    family. One DTO-validated factory now publishes complete local-fixture,
    verified-attested, deterministic-fallback, unsupported-claim,
    forbidden-action, and unsafe-action-content responses to both generated
    OpenAPI and the endpoint ledger. Certification requires exact serialized
    equality, including explicit nulls, grounding, retention, provenance, and
    no-authority fields.
43. FastAPI's generated schema omitted explicit nulls from route examples, so
    the application now applies a bounded post-generation injection from the
    same code-owned factory. Focused mutation tests reject missing named modes,
    missing control fields, grounding-policy drift, provider-authored blocked
    narrative, and fallback authority drift. Two legacy public verifier states
    with no executable constructor, route outcome, or behavioral test were
    removed. This is design modularity and contract hardening inside the
    existing deployable; persistence, runtime ownership, Gateway/Workbench,
    supported-feature posture, and service topology do not change.
44. Final local validation for issue `#529` passed `make check` and
    `make ci`: `4,702` unit tests, `454` integration tests with `31`
    declared environment-only PostgreSQL skips, `4` E2E tests, `99.01%`
    combined coverage over `27,742` statements, MyPy over `945` source
    files, zero duplicate clusters across `2,719` functions, and no known
    dependency vulnerabilities. Strict wiki parity is zero; README, wiki
    source, supported features, persistence, migrations, seed, Gateway,
    Workbench, central skills, and runtime topology remain unchanged by
    explicit scope decision.
45. PR `#530` merged by rebase at exact-main SHA
    `dab34f477572bd9ff0bba7e4fad4d9f22bfdd4cb`; Main Releasability
    `29518262581` and CodeQL `29518252754` passed. Release digest
    `sha256:e9219dbf98a13fa2cb9b76adf9eb1e893a94744c6ede1457d5b4c1c808e2d456`
    has matching OCI and `/version` identity, vulnerability scan, SBOM,
    keyless signature, provenance and SBOM attestations, release manifest,
    and digest-pinned runtime smoke. Strict wiki publication parity is zero,
    no publication change is required, issue `#529` is closed, and the
    implementation branch is absent locally and remotely.

PR merge-gate evidence remains required before merge.

## Acceptance Gate

1. OpenAPI quality gate passes for every exposed route.
2. Endpoint certification passes for every exposed route.
3. Gateway contract tests prove source-owned `lotus-idea` truth is preserved
   before each Gateway route is claimed implemented; the first bounded
   read-only advisor queue and candidate detail routes satisfy this foundation
   rule, including caller entitlement-scope forwarding. Workbench PR #391
   consumes those routes for bounded read-only rendering, but this does not
   complete full live Workbench proof or supported-feature promotion.
4. No alias or stale endpoint remains without explicit time-boxed justification.
5. Supported-feature promotion remains blocked until live runtime,
   Gateway/Workbench, data-product, docs/wiki, and certification evidence all
   exist.
