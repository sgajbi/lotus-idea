# Refactor Decisions

Record architecture, API, security, observability, testing, CI, and documentation decisions that
change the repository's bank-buyable posture.

Do not use this file for aspirational claims. Every entry should name code, tests, and validation
evidence or explicitly mark the item as planned.

## 2026-08-12: Opportunity Archetype Proof Application Scope Boundary

Issue `#994` applies the RFC-0002 Slice 16/18/19 maintainability lens to
`src/app/application/implementation_proof_opportunity_archetype_proofs.py::_apply_opportunity_archetype_proofs`.
After #991 closed, the report-only `make quality-baseline` inventory listed
this production-code proof-application helper as a `101` line hotspot.

Duplicate-check result: no existing focused issue owned the opportunity
archetype proof application keyword fan-out. The related RFC blockers for Core,
Workbench/Gateway runtime proof, data-mesh certification, client publication,
production identity/session-token authority, and final RFC closure remain
separate and must not be cleared by this internal refactor.

The branch refactor makes `apply_opportunity_archetype_proofs_from_scope(...)`
pass the proof scope directly into the existing proof-step descriptors instead
of manually unpacking and repacking every proof/ref pair. It separates:

1. source-ingestion runtime proof application,
2. opportunity proof-scope iteration,
3. payload/ref type filtering,
4. registered artifact-effect enforcement, and
5. current aggregate-proof validation before blocker clearing.

Focused local validation passed so far:

1. `.venv\Scripts\python.exe -m pytest tests\unit\implementation_proof\test_effect_enforcement.py -q`
   (`23` passed), and
2. `.venv\Scripts\ruff.exe check src\app\application\implementation_proof_opportunity_archetype_proofs.py tests\unit\implementation_proof\test_effect_enforcement.py`.

Merged-main evidence:

1. PR `#995` merged by rebase to Idea main
   `05dfb48ede9198a8b0a568122e5691a1589fb205` from PR head
   `57f0f0d7e29c6db3e3e1e7c32547d49f4e9f4797`.
2. Local validation passed `make test-unit` (`5,476` passed),
   `make typecheck`, `make lint`, `make quality-baseline`,
   `make maintainability-gate`, `make duplicate-implementation-gate`
   (`0` duplicate clusters), `make rfc0002-github-issue-execution-ledger-gate`,
   `make rfc0002-github-issue-learning-pattern-gate`,
   `make documentation-contract-gate`,
   `make rfc0002-github-issue-execution-state-audit`, and
   `make rfc0002-github-issue-execution-summary`.
3. GitHub validation passed Feature Lane, PR Merge Gate run `31573819143`,
   CodeQL, Queue Auto Merge, and exact-main Main Releasability Gate run
   `31574238002`.
4. No repo-authored wiki source changed. GitHub deleted the remote
   implementation branch and `git fetch --prune` removed the remote-tracking
   ref; local branch deletion remains pending patch-equivalence proof after the
   source-truth sync lands.
5. Source-sync PR `#996` merged to Idea main
   `c95217fd07cecd4dcb83c934167ad996ce1e69e0`. Exact-main Main
   Releasability Gate run `31575711931` passed for that SHA, including
   Docker image scan, SBOM generation, image signing, provenance/SBOM
   attestations, release metadata, and CI signal evidence. #994 was then
   closed with `Loop status: qa_passed_closed` while retaining
   `status/merged-main`; local implementation and source-sync branches were
   deleted after patch-equivalence proof.

The new focused tests prove both a valid source-ingestion plus
risk-concentration proof path and invalid scoped proof payload handling without
calling the validator. This preserves source-safe fail-closed behavior for
missing or incorrectly typed proof inputs.

No repo-authored wiki, README, supported-features, OpenAPI, migration, runtime
topology, Core, Workbench, Gateway, authentication, or authorization source
change is expected for this internal proof-application maintainability slice.

## 2026-08-12: Service Capacity Workload CLI Orchestration

Issue `#986` applies the RFC-0002 Slice 15/19 maintainability lens to
`scripts/run_service_capacity_workload.py::main`. After #983 closed, the
report-only `make quality-baseline` inventory listed this CLI entrypoint as the
next script hotspot at `102` lines.

Duplicate-check result: #345 and #814 remain the related capacity and canonical
downstream-capacity runtime-proof blockers, but neither owns this narrow
internal orchestration issue. This refactor must therefore keep #345/#814 open
and preserve every non-certifying capacity blocker.

The branch refactor moves reusable workload planning and downstream seed
validation into `src/app/application/service_capacity_workload_cli.py` and keeps
`scripts/run_service_capacity_workload.py` as the operator entrypoint. It
separates:

1. CLI timing validation,
2. downstream capacity seed and submission-path resolution,
3. paced workload measurement execution,
4. optional PostgreSQL/dependency/load/resource proof loading and attestation,
5. platform cost-attribution verification,
6. capacity baseline artifact construction, and
7. atomic JSON output.

Focused local validation passed so far:

1. `python -m pytest tests/unit/test_run_service_capacity_workload.py -q`
   (`34` passed),
2. `python -m pytest tests/unit/test_run_service_capacity_workload.py tests/unit/test_github_issue_execution_summary.py tests/unit/test_github_issue_execution_ledger_gate.py tests/unit/test_github_issue_learning_pattern_gate.py -q`
   (`83` passed),
3. `.venv/Scripts/ruff.exe check scripts/run_service_capacity_workload.py src/app/application/service_capacity_workload_cli.py tests/unit/test_run_service_capacity_workload.py`,
4. `.venv/Scripts/ruff.exe format --check scripts/run_service_capacity_workload.py src/app/application/service_capacity_workload_cli.py tests/unit/test_run_service_capacity_workload.py`,
5. `.venv/Scripts/mypy.exe scripts/run_service_capacity_workload.py src/app/application/service_capacity_workload_cli.py tests/unit/test_run_service_capacity_workload.py`,
6. `make quality-baseline`,
7. `make service-slo-capacity-contract-gate`,
8. RFC-0002 execution ledger gate,
9. live GitHub issue execution state audit,
10. RFC-0002 issue execution summary,
11. RFC-0002 issue learning-pattern gate,
12. `make maintainability-gate`,
13. `make duplicate-implementation-gate`,
14. `make documentation-contract-gate`,
15. `make implementation-truth-gate`, and
16. `make test-unit` (`5473` passed), and
17. `git diff --check`.

The service SLO/capacity source-of-truth contract now names
`baseline_workload_planning_policy` so the governed baseline runner and the
application-owned workload planning policy cannot drift.
The architecture-boundary report was regenerated because the new application
module changes the source-file count and import digest.

PR `#987` merged by rebase to `main` at
`830870721982d5d7a4968708bcba1723ef3620ea` from branch head
`34324318631988ea8c76413d981f4ecf25397ebc`. PR Merge Gate run
`31565751153`, Feature Lane run `31565748332`, PR CodeQL run `31565748721`,
Queue Auto Merge run `31565749694`, and merged-PR main releasability dispatch
run `31566091370` passed before merge. Exact-main Main Releasability Gate run
`31566095536` passed for the merged main SHA, including workflow lint,
lint/typecheck/security, unit, integration, e2e, PostgreSQL runtime proof,
combined coverage, Docker build/runtime smoke, image scan, dependency SBOM,
published digest proof, image signing, provenance and SBOM attestations,
release metadata, release image identity binding, release license binding, and
CI signal evidence.

No repo-authored wiki, README, supported-features, OpenAPI, migration, runtime
topology, Core, Workbench, Gateway, authentication, or authorization source
change is expected for this internal script-maintainability slice.
The remote implementation branch was deleted by GitHub and pruned locally; the
local branch was deleted after diff-equivalence proof because the repository
uses rebase merge.

## 2026-08-12: Candidate Detail API Boundary Orchestration

Issue `#988` applies the RFC-0002 Slice 10/11/15/19 maintainability lens to
`src/app/api/candidate_detail.py::get_idea_candidate_detail`. After #986
closed, the report-only `make quality-baseline` inventory listed this route as
a `101` line production API boundary hotspot.

Duplicate-check result: no focused existing issue owned the candidate-detail
route maintainability gap. Related Workbench/Gateway runtime proof issues
#685/#686/#687 remain separate because this refactor is internal Idea API
boundary hardening and cannot certify product-surface runtime proof.

The intended implementation should separate:

1. caller-context parsing and invalid-scope rejection,
2. role/capability authorization,
3. application command and repository execution,
4. access-scope denial mapping,
5. not-found mapping,
6. successful response projection and durable-storage posture, and
7. bounded operation-event emission.

The refactor must preserve route path, operation id, response model, OpenAPI
metadata, response schema, status codes, ProblemDetails codes/details,
authorization ordering, tenant/book/portfolio/client entitlement behavior,
source-safe redaction, and supported-feature non-promotion posture.

The local implementation now keeps the public route handler as a thin
orchestrator over named API-boundary helpers for caller construction,
authorization, application execution, result projection, ProblemDetails, and
operation-event emission. Focused local validation passed:

1. `.venv\Scripts\ruff.exe check src\app\api\candidate_detail.py tests\integration\test_candidate_detail_api.py tests\integration\test_api_operation_events.py tests\unit\test_candidate_detail_application.py tests\unit\test_candidate_detail_models.py`,
2. `.venv\Scripts\mypy.exe src\app\api\candidate_detail.py tests\integration\test_candidate_detail_api.py tests\integration\test_api_operation_events.py tests\unit\test_candidate_detail_application.py tests\unit\test_candidate_detail_models.py`,
3. `.venv\Scripts\python.exe -m pytest tests\integration\test_candidate_detail_api.py tests\integration\test_api_operation_events.py::test_candidate_detail_api_emits_bounded_operation_event tests\unit\test_candidate_detail_application.py tests\unit\test_candidate_detail_models.py -q`
   (`12` passed),
4. `make quality-baseline`,
5. `make maintainability-gate`, and
6. `make duplicate-implementation-gate`.

The route resolves the runtime repository once and passes it through the
application load and durable-storage posture projection so both decisions are
bound to the same repository instance. Broader validation then passed
`make typecheck`, `make lint`, and `make test-unit` (`5,473` passed). The
issue-execution summary unit tests were tightened to render fixed-local issues
from the ledger state machine instead of assuming that section is always empty.
PR #990 carries this implementation with neutral Keep-open wording for #988.
PR #990 then merged by rebase to Idea main
`2f727245685834d3e55de2aba5281c4467859bdb` from PR head
`eea7b79475615a45a328cdb321cc4395d926a1e2`. Feature Lane, PR
Merge Gate, CodeQL, Queue Auto Merge, and the merged-PR main releasability
dispatch completed successfully before merge. Exact-main Main Releasability
Gate run `31568912323` passed for the merged main SHA, including workflow
lint, lint/typecheck/security, unit, integration, e2e, PostgreSQL runtime
proof, combined coverage, Docker build/runtime smoke, image scan, dependency
SBOM, published digest proof, image signing, provenance and SBOM
attestations, release metadata, release image identity binding, release
license binding, and CI signal evidence.

The implementation branch was deleted remotely by GitHub and pruned locally.
The local branch was deleted after patch-equivalence and zero-diff proof
because the repository uses rebase merge. No repo-authored wiki source changed,
so wiki publication was not required. The source ledger now records #988 as
`closed_complete`; the GitHub issue lifecycle should be normalized with
`Loop status: qa_passed_closed` and retained `status/merged-main` evidence
after this closure-sync source truth merges.

No repo-authored wiki, README, supported-features, OpenAPI, migration, runtime
topology, Core, Workbench, Gateway, production IdP/session-token,
authentication, or authorization infrastructure source change is expected for
this internal API-maintainability slice unless implementation reveals real
behavioral or operator-facing truth changes.

## 2026-08-12: Bond Maturity Runtime-Evidence Qualification Blockers

Issue `#991` applies the RFC-0002 Slice 12/13/15/18 maintainability lens to
`src/app/application/bond_maturity_runtime_evidence/runtime_execution.py::_qualification_blockers`.
The current report-only `make quality-baseline` inventory lists this function
as a `101` line production-code hotspot in a source-authority proof path.

Duplicate-check result: no focused existing issue owned the bond-maturity
runtime-evidence qualification blocker maintainability gap. The issue was
created as https://github.com/sgajbi/lotus-idea/issues/991 with `status/ready`
because the work is writable in `lotus-idea` and does not require a Core code
change before the internal refactor can start.

The intended implementation should separate:

1. Core maturity source-ref authority checks,
2. Core holdings upstream source-ref authority checks,
3. caller entitlement posture,
4. maturity and holdings product identity checks,
5. response tenant/portfolio scope checks,
6. maturity-window start/end/horizon/projected semantics,
7. maturity basis supportability,
8. count validity and maturity fact consistency, and
9. Core supportability status.

The refactor must preserve the public payload schema, supported blocker
vocabulary, source-safe no-promotion posture, and deterministic blocker order
where that order is observable. It must not claim new Core runtime evidence,
Workbench/Gateway runtime proof, data-mesh certification, client publication,
supported-feature promotion, production identity/session-token authority,
schema or migration changes, deployment certification, production
certification, or final RFC-0002 closure.

The local implementation now keeps `_qualification_blockers` as a thin
orchestrator over named helpers for:

1. Core maturity source-ref authority,
2. Core holdings upstream source-ref authority,
3. entitlement posture,
4. product identity,
5. response tenant/portfolio scope,
6. maturity-window semantics,
7. maturity basis,
8. count validity and maturity fact consistency,
9. supportability status,
10. source identity,
11. source integrity, and
12. correlation binding.

Focused local validation passed:

1. `.venv\Scripts\ruff.exe check src\app\application\bond_maturity_runtime_evidence\runtime_execution.py tests\unit\bond_maturity_runtime_evidence\test_runtime_execution.py`,
2. `.venv\Scripts\mypy.exe src\app\application\bond_maturity_runtime_evidence\runtime_execution.py tests\unit\bond_maturity_runtime_evidence\test_runtime_execution.py`,
3. `.venv\Scripts\python.exe -m pytest tests\unit\bond_maturity_runtime_evidence\test_runtime_execution.py -q`
   (`66` passed),
4. `make quality-baseline`,
5. `make maintainability-gate`, and
6. `make duplicate-implementation-gate` (`0` duplicate clusters).

The focused test suite now includes an order-preservation case that exercises
every major blocker group without clearing the aggregate runtime blocker.
Same-pattern scan reviewed surrounding runtime-evidence `_qualification_blockers`
and blocker helper functions. No high-confidence sibling issue was folded into
this bounded branch; the credible adjacent blocker families are already
separate source-authority/runtime-proof issue areas and should not be bundled
without their own issue acceptance criteria.

PR `#992` merged by rebase to `main` at
`9123ae3583837da1dc40d4d72e8fd9bf6851a479` from branch head
`60f22a3d70e95b1759e6d59439f963e187b1400f`. The PR satisfied Feature Lane,
PR Merge Gate, CodeQL, and Queue Auto Merge checks. Exact-main Main
Releasability Gate run `31570863800` passed for the merge SHA, including
unit, integration, e2e, PostgreSQL runtime proof, coverage, Docker build,
image scan, provenance, SBOM, signing, attestations, release metadata, and CI
signal evidence.

No repo-authored wiki source changed. Issue `#991` was closed with
`Loop status: qa_passed_closed` after `status/merged-main` evidence was
recorded. GitHub deleted and pruned the remote implementation branch after the
merge; the corresponding local branch had patch-equivalence proof against
`origin/main` before cleanup. This closure remains an internal
source-authority proof maintainability hardening slice and does not claim new
Core runtime evidence, Workbench/Gateway runtime proof, supported-feature
promotion, or final RFC-0002 closure.

## 2026-08-12: Manage Intake Runtime Proof Generator Responsibilities

Issue `#983` applies the RFC-0002 Slice 12/13/18 maintainability lens to
`scripts/downstream_realization/generate_manage_intake_runtime_execution.py::_execute_manage_testclient`.
The current report-only quality baseline listed the helper as a `102` line
script hotspot in the Manage action-intake owner-runtime proof path.

The refactor preserves the bounded #689 Manage route receipt proof while
separating:

1. inline owner-app TestClient script construction,
2. local Manage environment construction,
3. subprocess execution,
4. JSON-object stdout decoding, and
5. source-safe receipt projection.

Focused and repo-level local validation passed:

1. `python -m pytest tests/unit/downstream_realization/test_manage_intake_runtime_execution.py -q`
   (`12` passed),
2. `.venv/Scripts/ruff.exe check scripts/downstream_realization/generate_manage_intake_runtime_execution.py tests/unit/downstream_realization/test_manage_intake_runtime_execution.py`,
3. `.venv/Scripts/ruff.exe format --check scripts/downstream_realization/generate_manage_intake_runtime_execution.py tests/unit/downstream_realization/test_manage_intake_runtime_execution.py`,
4. `.venv/Scripts/mypy.exe scripts/downstream_realization/generate_manage_intake_runtime_execution.py tests/unit/downstream_realization/test_manage_intake_runtime_execution.py`,
5. `make rfc0002-github-issue-execution-ledger-gate`,
6. `make rfc0002-github-issue-execution-state-audit`,
7. `make rfc0002-github-issue-execution-summary`,
8. `make rfc0002-github-issue-learning-pattern-gate`,
9. `make quality-baseline`,
10. `make maintainability-gate`,
11. `make duplicate-implementation-gate`,
12. `make documentation-contract-gate`,
13. `make implementation-truth-gate`,
14. `make typecheck`,
15. `make lint`,
16. `make test-unit` (`5472` passed),
17. `git diff --check`.

The generator now rejects non-object Manage stdout through
`_decode_manage_testclient_stdout(...)` before source-safe receipt projection.
`make quality-baseline` no longer lists `_execute_manage_testclient`; the next
script hotspot is `scripts/run_service_capacity_workload.py::main`.

PR `#984` merged by rebase to `main` at
`fea78cf18bf0f2c31fb95a27d9a0ee5abb3d1e89` from branch head
`9d699505df9183d1bc7368db7cdc11e14d62002b` after PR Merge Gate run
`31562370588`, Feature Lane run `31562368147`, CodeQL run `31562368715`, and
Queue Auto Merge run `31562369305` passed. Exact-main CodeQL run
`31562833226` and Main Releasability Gate run `31562838110` passed for the
merged `fea78cf18bf0f2c31fb95a27d9a0ee5abb3d1e89` main commit.

This is internal proof-generator maintainability only. It does not change the
proof payload schema, API/OpenAPI contracts, migrations, runtime topology,
downstream action-register persistence, rebalance/order authority, client
publication, production identity/authn/authz, supported-feature promotion,
owner runtime certification beyond the bounded Manage route receipt, or final
RFC-0002 closure. No repo-authored wiki source changed, so wiki publication is
not required for this source change.

## 2026-08-12: Canonical Opportunity Archetype Evidence-Pack Builder

Issue `#980` applies the RFC-0002 Slice 16/19 maintainability lens to
`src/app/application/opportunity_archetype_evidence_pack.py::build_canonical_opportunity_archetype_evidence_pack`.
The current report-only quality baseline listed the builder as a `103` line
production source hotspot in the canonical opportunity-archetype evidence-pack
proof path.

The refactor keeps the public builder and validator unchanged while extracting:

1. `_load_canonical_opportunity_archetype_contract(...)`,
2. `_canonical_archetype_evidence(...)`,
3. `_remaining_certification_blockers(...)`,
4. `_opportunity_archetype_evidence_pack_payload(...)`,
5. `_source_authority_boundary()`,
6. `_canonical_portfolio_scope()`,
7. `_claim_boundary()`,
8. `_source_of_truth(...)`,
9. `_pack_summary(...)`,
10. `_evidence_refs()`.

Focused local validation passed:

1. `python -m ruff check src/app/application/opportunity_archetype_evidence_pack.py tests/unit/test_opportunity_archetype_evidence_pack.py tests/unit/test_implementation_proof_readiness_opportunity_archetype_evidence_pack.py tests/unit/test_generate_implementation_proof_readiness_opportunity_archetype_evidence_pack.py`,
2. `python -m ruff format --check src/app/application/opportunity_archetype_evidence_pack.py tests/unit/test_opportunity_archetype_evidence_pack.py tests/unit/test_implementation_proof_readiness_opportunity_archetype_evidence_pack.py tests/unit/test_generate_implementation_proof_readiness_opportunity_archetype_evidence_pack.py`,
3. `python -m mypy src/app/application/opportunity_archetype_evidence_pack.py`,
4. `python -m pytest tests/unit/test_opportunity_archetype_evidence_pack.py tests/unit/test_implementation_proof_readiness_opportunity_archetype_evidence_pack.py tests/unit/test_generate_implementation_proof_readiness_opportunity_archetype_evidence_pack.py -q`
   (`12` passed),
5. `make quality-baseline`,
6. `make maintainability-gate`,
7. `make duplicate-implementation-gate`,
8. `make rfc0002-github-issue-execution-ledger-gate`,
9. `make rfc0002-github-issue-execution-state-audit`,
10. `make rfc0002-github-issue-execution-summary`,
11. `make rfc0002-github-issue-learning-pattern-gate`,
12. `make documentation-contract-gate`,
13. `make implementation-truth-gate`,
14. `make typecheck`,
15. `git diff --check`.

The public builder moved from `103` lines to `19` lines and no longer appears
in the largest source function list.

PR `#981` merged by rebase to exact Idea main
`ed895d35b3cda7d3e835a07c46f4a36abd0aced5`. PR evidence passed PR Merge
Gate run `31559901205`, Feature Lane run `31559897869`, CodeQL run
`31559898157`, and Queue Auto Merge run `31559899348`. Exact-main evidence
passed CodeQL run `31560260581` and Main Releasability Gate run
`31560267153`, including workflow lint, lint/typecheck/security, unit,
integration, e2e, PostgreSQL runtime proof, combined coverage, Docker
build/runtime smoke, image scan, SBOM, signed published image digest,
provenance/SBOM attestations, release metadata, release image identity binding,
release license evidence binding, and CI signal evidence. Issue `#980` was
closed with `Loop status: qa_passed_closed` evidence while retaining
`status/merged-main`. No repo-authored wiki source changed, so wiki publication
was not required. The remote implementation branch was deleted by GitHub and
pruned locally; local state returned cleanly to `main` tracking `origin/main`.

This is internal proof-builder maintainability only. It does not change payload
schema, API/OpenAPI contracts, migrations, runtime topology, Workbench/Gateway
proof, source-owner authority, client-ready publication, data-mesh
certification, supported-feature promotion, production identity/authn/authz,
demo certification, or final RFC-0002 closure.

## 2026-08-12: AI Workflow-Pack Registration Proof Builder

Issue `#977` applies the RFC-0002 Slice 19 maintainability lens to
`src/app/application/ai_workflow_pack_registration/source_contract_proof.py::build_ai_workflow_pack_registration_proof_payload`.
The refreshed quality baseline listed the builder as a `103` line production
source hotspot in the AI workflow-pack registration proof path.

The builder mixed:

1. generated-at timestamp awareness validation,
2. source-safe file and Make-target evidence checks,
3. Lotus AI sibling-repository source-contract evidence inspection,
4. evidence-class blocker clearing checks,
5. aggregate proof validity,
6. proof payload construction,
7. explicit false runtime/deployment/model-risk/Workbench/client-publication
   and supported-feature claims.

The refactor keeps the public builder and validator unchanged while extracting:

1. `AI_WORKFLOW_PACK_REGISTRATION_TRUE_PROOF_CHECKS`,
2. `AI_WORKFLOW_PACK_REGISTRATION_UNSUPPORTED_CLAIMS`,
3. `_ai_workflow_pack_registration_proof_checks(...)`,
4. `_registration_evidence_class_matches_blockers()`,
5. `_all_required_registration_proof_checks_pass(...)`,
6. `_unsupported_registration_claims()`,
7. `_unsupported_registration_claims_are_false(...)`.

Focused local validation passed:

1. `python -m ruff check src/app/application/ai_workflow_pack_registration/source_contract_proof.py tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py`,
2. `python -m ruff format --check src/app/application/ai_workflow_pack_registration/source_contract_proof.py tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py`,
3. `python -m mypy src/app/application/ai_workflow_pack_registration/source_contract_proof.py`,
4. `python -m pytest tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py -q`
   (`45` passed),
5. `make maintainability-gate`,
6. `make quality-baseline`.

PR `#978` merged by rebase to Idea main
`1630eb73a863f77cdf94da225d457810e8c0fb79` from PR head
`b6f6b983815217cbd5526e47ce415bc4c6c9ae35`. PR-side validation passed
PR Merge Gate run `31557536789`, Feature Lane run `31557534356`,
PR CodeQL run `31557535042`, and Queue Auto Merge run `31557535731`.
Exact-main CodeQL run `31557927299` and exact-main Main Releasability
Gate run `31557931974` passed for
`1630eb73a863f77cdf94da225d457810e8c0fb79`. Issue `#977` is closed
with `Loop status: qa_passed_closed` evidence. No repo-authored wiki
source changed, so wiki publication was not required. The implementation
branch was already deleted server-side and stale remote tracking was pruned
after patch-equivalence proof.

The refreshed quality baseline no longer lists
`build_ai_workflow_pack_registration_proof_payload` in the largest source
function list.

This is internal application-layer maintainability only. It does not change
payload schema, API/OpenAPI contracts, runtime proof authority, deployment
certification, model-risk dashboard/alert certification, Workbench product
proof, Gateway, Core, Lotus AI implementation, client-output publication
authority, supported-feature promotion, identity/authn/authz posture,
migrations, or final RFC-0002 closure.

## 2026-08-12: Candidate Lifecycle Transition API Boundary

Issue `#974` applies the RFC-0002 Slice 15/19 maintainability lens to
`src/app/api/candidate_lifecycle.py::record_candidate_lifecycle_transition`.
After #971 closed, the refreshed quality baseline listed the route as a `103`
line production API hotspot in the candidate lifecycle, idempotency,
repository durability, audit, and operation-event boundary.

The route mixed:

1. trusted caller construction from request headers,
2. lifecycle capability authorization,
3. idempotency-key validation,
4. durable repository selection and configuration checks,
5. event-lineage construction,
6. application command construction,
7. application execution,
8. exception and persistence Problem Details projection,
9. operation-event emission,
10. accepted/replayed response projection.

The refactor keeps `record_candidate_lifecycle_transition(...)` as the public
FastAPI handler while splitting review-sensitive responsibilities into named
API-boundary helpers:

1. `_caller_from_lifecycle_headers(...)`,
2. `_validate_lifecycle_request_authority(...)`,
3. `_lifecycle_repository_context_or_problem(...)`,
4. `_apply_lifecycle_transition(...)`,
5. `_lifecycle_transition_command(...)`,
6. `_candidate_lifecycle_response(...)`,
7. `_candidate_lifecycle_transition_summary(...)`.

Focused local validation passed:

1. `python -m ruff check src/app/api/candidate_lifecycle.py tests/unit/test_candidate_lifecycle_application.py tests/unit/test_api_request_validation.py tests/unit/test_service_contract.py tests/unit/api_examples/test_candidate_state_examples.py tests/integration/test_api_operation_events.py`,
2. `python -m ruff format --check src/app/api/candidate_lifecycle.py tests/unit/test_candidate_lifecycle_application.py tests/unit/test_api_request_validation.py tests/unit/test_service_contract.py tests/unit/api_examples/test_candidate_state_examples.py tests/integration/test_api_operation_events.py`,
3. `python -m mypy src/app/api/candidate_lifecycle.py`,
4. `python -m pytest tests/unit/test_candidate_lifecycle_application.py tests/unit/test_api_request_validation.py tests/unit/test_service_contract.py tests/unit/api_examples/test_candidate_state_examples.py tests/integration/test_api_operation_events.py -q`
   (`44` passed).

Broader implementation-branch validation passed:

1. `make quality-baseline`,
2. `make maintainability-gate`,
3. `make duplicate-implementation-gate`,
4. `make rfc0002-github-issue-execution-ledger-gate`,
5. `make rfc0002-github-issue-learning-pattern-gate`,
6. `make rfc0002-github-issue-execution-state-audit`,
7. `make rfc0002-github-issue-execution-summary`,
8. `make documentation-contract-gate`,
9. `make typecheck`,
10. `make lint`,
11. `git diff --check`,
12. `make check` (`5471` passed).

The refreshed quality baseline no longer lists
`record_candidate_lifecycle_transition` in the production API hotspot list.

PR `#975` merged the implementation to `lotus-idea` main
`290405c80f18c2accb05dee7f7e3da1cbbb7b6a8` from PR head
`2a1e45b72879b2859afc1b2fee48c122b3e61e7e`. PR Merge Gate run
`31553971359`, Feature Lane run `31553968230`, PR CodeQL run `31553970021`,
and Queue Auto Merge run `31553971522` passed before merge. Exact-main Main
Releasability Gate run `31554345807` and exact-main CodeQL push run
`31554335729` passed for the merged SHA, including Docker build/runtime smoke,
vulnerability scan, SBOM, image push, signing, provenance, release metadata,
image identity/license binding, and CI signal evidence.

The source-controlled RFC-0002 execution ledger now tracks #974 as
`closed_complete`, and the issue-learning pattern ledger retains it as related
evidence under operations/security/resilience certification so future
candidate-lifecycle API changes preserve the same no-claim boundary.

No repo-authored wiki source change is expected because this is internal API
structure hardening only. The implementation does not change public API or
OpenAPI contracts, persistence schema, migrations, authentication,
authorization infrastructure, production IdP/session-token authority, Core,
Gateway, Workbench, supported-feature posture, runtime topology, client
publication, legal/privacy/Archive/provider certification, or final RFC-0002
closure.

## 2026-08-12: Data Lifecycle Action API Boundary

Issue `#971` applies the RFC-0002 Slice 15/19 maintainability lens to
`src/app/api/data_lifecycle/__init__.py::post_data_lifecycle_action`. The
quality baseline listed the route as a `105` line production API hotspot in
the governed data-lifecycle, retention, legal-hold, erasure, purge, authority,
Archive posture, and replay boundary.

The route mixed:

1. trusted caller construction and tenant/capability authorization,
2. idempotency validation,
3. lifecycle-authority verification,
4. Archive lifecycle posture verification,
5. command construction with request event lineage,
6. durable repository selection and capability checks,
7. application execution,
8. response and ProblemDetails projection.

The refactor keeps `post_data_lifecycle_action(...)` as the public FastAPI
handler while splitting the review-sensitive responsibilities into named
API-boundary helpers:

1. `_caller_from_action_headers(...)`,
2. `_authorize_data_lifecycle_action(...)`,
3. `_command_for_data_lifecycle_action(...)`,
4. `_data_lifecycle_precondition_problem(...)`,
5. `_execute_data_lifecycle_action(...)`.

Focused local validation passed:

1. `python -m ruff check src/app/api/data_lifecycle/__init__.py tests/integration/test_data_lifecycle_api.py tests/integration/data_lifecycle/test_operation_events.py`,
2. `python -m ruff format --check src/app/api/data_lifecycle/__init__.py tests/integration/test_data_lifecycle_api.py tests/integration/data_lifecycle/test_operation_events.py`,
3. `python -m mypy src/app/api/data_lifecycle/__init__.py tests/integration/test_data_lifecycle_api.py tests/integration/data_lifecycle/test_operation_events.py`,
4. `python -m pytest tests/integration/test_data_lifecycle_api.py tests/integration/data_lifecycle/test_operation_events.py -q`
   (`14` passed),
5. `make quality-baseline`,
6. `make maintainability-gate`,
7. `make duplicate-implementation-gate`,
8. `make rfc0002-github-issue-execution-ledger-gate`,
9. `make rfc0002-github-issue-learning-pattern-gate`,
10. `make rfc0002-github-issue-execution-state-audit`,
11. `make rfc0002-github-issue-execution-summary`,
12. `make documentation-contract-gate`,
13. `make typecheck`,
14. `make lint`,
15. `git diff --check`.

The refreshed quality baseline no longer lists `post_data_lifecycle_action` in
the largest-function list; the next production API hotspot is
`src/app/api/candidate_lifecycle.py::record_candidate_lifecycle_transition` at
`103` lines.

PR `#972` merged the implementation to `lotus-idea` main
`4a68b6e0d55fe3ceec8251aca7e154aadbe3f935`. Exact-main Main Releasability
run `31551701446` and exact-main CodeQL push run `31551695891` passed for that
SHA. The source-controlled RFC-0002 execution ledger now tracks #971 as
`closed_complete`, and the issue-learning pattern ledger retains it as related
evidence under operations/security/resilience certification so future
data-lifecycle changes preserve the same no-claim boundary.

This is internal API maintainability only. It does not change API/OpenAPI
contracts, persistence schema, migrations, authentication, authorization
infrastructure, production IdP/session-token authority, legal/privacy
certification, Archive production conformance, Core, Gateway, Workbench,
supported-feature posture, runtime topology, wiki source, client publication,
or final RFC-0002 closure.

## 2026-08-12: Issue 681 Evidence-Sync Note Signatures

Issue `#956` applies the RFC-0002 Slice 18/19 maintainability lens to
`tests/unit/test_github_issue_execution_ledger_gate.py`. The quality baseline
listed
`test_rfc0002_github_issue_execution_ledger_records_issue_681_sync_note` as the
largest remaining function at `139` lines. The test protects the #681
source-sync note history, but the repeated inline `any(...)` assertions made
future evidence updates harder to review.

The refactor keeps every protected #681 note fragment, but moves the required
note signatures into `ISSUE_681_EVIDENCE_SYNC_NOTE_SIGNATURES` and verifies
them through `_assert_evidence_notes_contain_signatures(...)`. The public test
uses `_issue_by_number(...)` and remains a small orchestrator over the same
ledger evidence.

Focused local validation passed:

1. JSON validation for the RFC-0002 execution ledger, execution-ledger gate
   policy, and issue-learning-pattern contracts,
2. `python -m ruff check tests/unit/test_github_issue_execution_ledger_gate.py`,
3. `python -m ruff format --check tests/unit/test_github_issue_execution_ledger_gate.py`,
4. `python -m mypy tests/unit/test_github_issue_execution_ledger_gate.py`,
5. `python -m pytest tests/unit/test_github_issue_execution_ledger_gate.py -q`,
6. RFC-0002 execution ledger, live issue-state audit, execution summary, and
   issue-learning-pattern gates,
7. documentation-contract, quality-baseline, maintainability,
   duplicate-implementation, and git diff whitespace gates.

The refreshed quality baseline no longer lists the targeted test as a largest
function; the next largest function is
`tests/unit/test_proof_artifacts.py::_assert_configured_artifacts_are_bound` at
`126` lines. No repo-authored wiki source changed, so wiki publication was not
required for PR `#957`.

PR `#957` merged by rebase to Idea main at
`24841f43fd776672c9e19deb7b7e50dfe925060d` from PR head
`11a924f6c35166062c3a65f49f839fe7f8590777`. Exact-main Main Releasability
Gate run `31537452298` and exact-main CodeQL push run `31537443335` passed for
that SHA. PR `#958` synchronized merged-main source truth to Idea main at
`c28962222c64b4e2d57405f3bfa962bc77975deb`; exact-main Main Releasability
Gate run `31538823333` and exact-main CodeQL push run `31538817255` passed for
that source-sync SHA. GitHub deleted the implementation and source-sync remote
branches during merge, no local or remote `#956` branch remains after pruning,
and issue `#956` is closed with QA evidence.

This is test-support maintainability only. It does not change runtime code,
API/OpenAPI behavior, proof schemas, Core, Gateway, Workbench, authentication,
authorization, supported-feature posture, wiki source, or final RFC-0002
closure.

## 2026-08-12: Cross-Repo Issue Posture Count Test Fixtures

Issue `#953` applies the RFC-0002 Slice 18/19 maintainability lens to
`tests/unit/test_cross_repo_issue_posture.py`. The quality baseline listed
`test_cross_repo_issue_posture_counts_statuses_and_attention_issues` as the
largest function at `160` lines. The test protects cross-repo posture counts,
title-only RFC reference detection, blocker classification, and attention
ordering, but the inline fixture and expected-output blocks were too large for
reviewable future updates.

The refactor keeps production posture logic unchanged. The test fixture now
lives in `_cross_repo_posture_fixture_payload()`, while protected expected
outputs live in `EXPECTED_TITLE_ONLY_RFC0002_REFERENCES` and
`EXPECTED_WORKBENCH_BLOCKED_ISSUE`. The public test remains a small
orchestrator over the same cross-repo behavior.

Focused local validation passed:

1. JSON validation for the RFC-0002 execution ledger, execution-ledger gate
   policy, and issue-learning-pattern contracts,
2. `python -m ruff check tests/unit/test_cross_repo_issue_posture.py`,
3. `python -m ruff format --check tests/unit/test_cross_repo_issue_posture.py`,
4. `python -m mypy tests/unit/test_cross_repo_issue_posture.py`,
5. `python -m pytest tests/unit/test_cross_repo_issue_posture.py -q`
   (`14` passed),
6. RFC-0002 execution ledger, live issue-state audit, execution summary, and
   issue-learning-pattern gates,
7. documentation-contract, quality-baseline, maintainability,
   duplicate-implementation, and git diff whitespace gates.

The refreshed quality baseline no longer lists the targeted test as the largest
function; the next largest function is
`tests/unit/test_github_issue_execution_ledger_gate.py::test_rfc0002_github_issue_execution_ledger_records_issue_681_sync_note`
at `139` lines.

PR `#954` merged by rebase to Idea main at
`28c70b8b96f29d93ec7d1953419ee2fe6e3f4e6d`. Exact-main Main Releasability
Gate `31533477901` and exact-main Push on main `31533462119` passed for that
SHA. No repo-authored wiki source changed, so wiki publication was not
required. The remote branch was deleted by GitHub, and the local branch was
deleted after git cherry patch-equivalence proof.

This is test-support maintainability only. It does not change runtime code,
API/OpenAPI behavior, proof schemas, Core, Gateway, Workbench, authentication,
authorization, supported-feature posture, wiki source, or final RFC-0002
closure.

## 2026-08-12: Slice 18 Ledger Posture Evidence Test Fragments

Issue `#950` applies the RFC-0002 Slice 18/19 maintainability lens to
`tests/unit/test_github_issue_execution_ledger_gate.py`. The quality baseline
listed `test_rfc0002_github_issue_execution_ledger_tracks_slice18_posture_evidence`
as the largest function at `179` lines. The test protects #681 source-sync
evidence, but the inline assertion history was too large for reviewable future
updates.

The refactor keeps every #681 lifecycle assertion and required evidence
fragment, but moves the protected evidence strings into
`ISSUE_681_SLICE18_POSTURE_FRAGMENTS` and verifies them through
`_assert_closure_instruction_contains_fragments(...)`. The test remains a small
orchestrator over the same ledger contract.

Focused local validation passed:

1. JSON validation for the RFC-0002 execution ledger, execution-ledger gate
   policy, and issue-learning-pattern contracts,
2. `python -m ruff check tests/unit/test_github_issue_execution_ledger_gate.py`,
3. `python -m ruff format --check tests/unit/test_github_issue_execution_ledger_gate.py`,
4. `python -m mypy tests/unit/test_github_issue_execution_ledger_gate.py`,
5. `python -m pytest tests/unit/test_github_issue_execution_ledger_gate.py -q`
   (`36` passed),
6. RFC-0002 execution ledger, live issue-state audit, execution summary, and
   issue-learning-pattern gates,
7. documentation-contract, quality-baseline, maintainability,
   duplicate-implementation, and git diff whitespace gates.

The refreshed quality baseline no longer lists the targeted test as the largest
function; the next largest function is
`tests/unit/test_cross_repo_issue_posture.py::test_cross_repo_issue_posture_counts_statuses_and_attention_issues`
at `160` lines.

PR `#951` merged by rebase to exact Lotus Idea main
`a2632f02a940ca19fd627a471608fe8fa726a2f9`. Exact-main Main Releasability
Gate run `31529635948` and exact-main Push on main run `31529628828` both
passed. The remote PR branch was deleted by GitHub, and the local branch was
deleted after `git cherry` patch-equivalence proof.

This is test-support maintainability only. It does not change runtime code,
API/OpenAPI behavior, proof schemas, Core, Gateway, Workbench, authentication,
authorization, supported-feature posture, wiki source, or final RFC-0002
closure.

## 2026-08-12: Implementation Proof Consumption Registered-Proof Applier

Issue `#947` applies the RFC-0002 Slice 17/19 maintainability lens to
`src/app/application/implementation_proof_consumption.py`. The current
quality baseline keeps that module in the largest production-file list, and
inspection showed repeated local branches for the same application-layer proof
pattern:

1. validate the proof artifact is registered for the expected effect,
2. prove the artifact payload is valid and current,
3. apply a proof-specific capability update across readiness capabilities.

The refactor keeps `apply_available_proofs_from_scope(...)` and every
proof-specific capability applier as the stable behavior boundary. The shared
`_apply_registered_capability_proof_if_current(...)` helper now owns the
registered-proof validation plus capability-mapping pattern for storage,
runtime trust telemetry, AI, downstream realization, data-mesh, operator
workflow, and Workbench/Gateway proof families.

Focused local validation passed:

1. `python -m ruff check src/app/application/implementation_proof_consumption.py`,
2. `python -m pytest tests/unit/implementation_proof tests/unit/ai_model_risk_operations/test_readiness_consumption.py tests/unit/operator_workflows_operations/test_readiness_consumption.py tests/integration/test_implementation_proof_readiness_api.py -q`
   (`72` passed).

PR `#948` merged by rebase to exact Lotus Idea main
`3b61fb49ff3a3f7457b5ebf73a68b3f6b4ab15bf`. Exact-main Main
Releasability Gate run `31525892622` and exact-main CodeQL run
`31525872690` both passed. The remote PR branch was deleted by GitHub, and
the local branch was deleted after `git cherry` patch-equivalence proof.

This is internal application maintainability only. It does not change
API/OpenAPI behavior, proof artifact schemas, persistence, migrations,
authentication or authorization, Core, Gateway, Workbench, runtime topology,
supported-feature truth, wiki source, or final RFC-0002 closure. No wiki
publication is required for the current local source diff because repo-authored
wiki source did not change.

## 2026-08-11: RFC-0002 Issue State Audit Fetch Completeness

Issue `#944` hardens `scripts/github_issue_execution_state_audit.py` after the
live state audit omitted older ledger-tracked issue `#340` from the initial
`gh issue list` result window. GitHub and the source ledger both showed `#340`
closed with `status/merged-main`; the failure was incomplete audit input, not
issue lifecycle drift.

The audit still fails on missing GitHub state and missing RFC-label coverage.
The fetch path now recovers every source-ledger issue omitted by the initial
list response through targeted `gh issue view` calls before running the strict
audit. This keeps the gate deterministic as the RFC-0002 issue ledger grows
without weakening validation.

Focused validation passed:

1. Ruff format/check over the touched audit script and unit test,
2. MyPy over the touched audit script and unit test,
3. `python -m pytest tests/unit/test_github_issue_execution_state_audit.py -q`
   (`11` passed).

PR `#945` merged this hardening by rebase to exact-main SHA
`8329c2911e38e5f4761396565de50f8dbb8e1f78`. Exact-main Main
Releasability Gate run `31520663608` and CodeQL run `31520653759` passed
for that SHA. No repo-authored wiki source changed, and the implementation
branch was deleted remotely and locally after patch-equivalence proof.

This is internal governance-gate reliability only. It does not change GitHub
lifecycle labels, application runtime behavior, Gateway/Workbench proof,
production identity/session-token authority, supported-feature promotion, or
final RFC-0002 closure.

## 2026-08-11: Downstream Realization Readiness Proof Application Boundary

Issue `#943` applies the RFC-0002 Slice 12/13/19 maintainability lens to
`src/app/application/downstream_realization_readiness.py`. The current
`make quality-baseline` report listed the file at `1196` lines, one small
change below the source-file maintainability cap.

The module mixed:

1. readiness DTOs and immutability normalization,
2. static Advise/Manage/Report capability and contract catalog construction,
3. repository summary projection,
4. source-contract supporting-evidence proof application,
5. runtime-execution blocker-clearing proof application,
6. blocker aggregation and issue-reference merging,
7. final readiness snapshot assembly.

`build_downstream_realization_readiness_snapshot(...)` remains the stable
public application entry point. Readiness DTOs now live in
`src/app/application/downstream_realization_readiness_models.py`, static
capability/contract construction lives in
`src/app/application/downstream_realization_readiness_catalog.py`, and
source-contract/runtime-execution proof application lives in
`src/app/application/downstream_realization_readiness_proofs.py`.

Focused validation passed:

1. Ruff check and format over touched source/test files,
2. MyPy over touched source/test files,
3. `python -m pytest tests/unit/test_downstream_realization_readiness.py tests/integration/test_downstream_realization_readiness_api.py -q`
   (`19` passed).

The focused unit suite now proves Advise route source-contract evidence and
Advise intake runtime-execution evidence compose without clearing Manage or
owner-authority blockers.

PR `#945` merged this refactor by rebase to exact-main SHA
`8329c2911e38e5f4761396565de50f8dbb8e1f78`. Exact-main Main
Releasability Gate run `31520663608` and CodeQL run `31520653759` passed
for that SHA. No repo-authored wiki source changed, and the implementation
branch was deleted remotely and locally after patch-equivalence proof.

This is internal application-layer maintainability only. It does not change
API/OpenAPI behavior, persistence schema, migrations, Core/Gateway/Workbench
behavior, production IdP/session-token authority, supported-feature promotion,
runtime topology, wiki source, client publication, or final RFC-0002 closure.

## 2026-08-11: Advise Intake Runtime Proof Generator Boundary

Issue `#941` applies the RFC-0002 Slice 12/13/19 maintainability lens to
`scripts/downstream_realization/generate_advise_intake_runtime_execution.py`.
The current quality baseline listed `_execute_advise_testclient(...)` as a
`107` line script helper in the Advise intake runtime-execution proof path.

The helper mixed owner-app test-client script construction, environment
defaults, subprocess execution, JSON decoding, scenario receipt projection,
and no-claim posture. The refactor keeps the generated proof contract and CLI
behavior stable while moving those responsibilities behind named helpers. The
coordinator is now short enough to review against the proof contract directly.

Focused validation passed:

1. Ruff check and format-check over the touched generator script and tests,
2. MyPy over the touched generator script and tests,
3. `python -m pytest tests/unit/downstream_realization/test_generate_advise_intake_runtime_execution.py tests/unit/downstream_realization/test_advise_intake_runtime_execution.py -q`
   (`13` passed).

Broader local validation passed quality-baseline, maintainability,
duplicate-implementation, RFC-0002 execution ledger, live state audit,
execution summary, issue-learning-pattern, documentation-contract, full
`make lint`, and git diff check. PR `#942` merged by rebase to exact-main SHA
`ddafd313ec0606e795838fca4fddc3c9037c2306`; exact-main Main Releasability
Gate run `31517388895` and CodeQL run `31517379659` passed for that SHA. No
repo-authored wiki source changed, and the implementation branch is absent
locally and remotely after cleanup.

This is internal script maintainability only. It does not clear `#379`,
`#676`, `#691`, `#685`, `#686`, `#687`, or `#699`; does not change
API/OpenAPI behavior, persistence schema, migrations, Core/Gateway/Workbench
behavior, production IdP/session-token authority, supported-feature
promotion, runtime topology, wiki source, client publication, or final
RFC-0002 closure.

## 2026-08-11: Low-Income Signal Evaluation Domain Boundary

Issue `#932` applies the RFC-0002 Slice 05 and Slice 19 maintainability lens to
`src/app/domain/low_income_signal.py::evaluate_low_income_signal(...)`. The
current `make quality-baseline` report listed the function as a `107` line
production-domain hotspot in the low-income cashflow-pressure evaluator.

The evaluator mixed:

1. evaluation-time validation,
2. temporal, entitlement, missing-source, and freshness blockers,
3. duplicate suppression,
4. cash-movement count and projected cashflow source-value validation,
5. materiality threshold evaluation,
6. stable identity construction,
7. signal, lineage, evidence-packet, score, and candidate assembly.

`src/app/domain/low_income_signal.py` now keeps `LowIncomeSignalPolicy`,
`LowIncomeSignalInput`, and `evaluate_low_income_signal(...)` public behavior
stable while extracting named helpers for blocking posture, source cashflow
materiality, candidate-result assembly, signal construction, evidence-packet
construction, candidate construction, and missing-source accounting. The
evaluator now uses the shared timezone and blocked-result helpers used by
sibling RFC-0002 signal evaluators.

Focused validation passed:

1. `python -m ruff check src/app/domain/low_income_signal.py tests/unit/test_low_income_signal_evaluation.py`,
2. `python -m ruff format --check src/app/domain/low_income_signal.py tests/unit/test_low_income_signal_evaluation.py`,
3. `python -m mypy src/app/domain/low_income_signal.py tests/unit/test_low_income_signal_evaluation.py`,
4. `python -m pytest tests/unit/test_low_income_signal_evaluation.py tests/unit/test_low_income_application.py tests/unit/api_examples/test_low_income_signal_examples.py -q`
   (`20` passed).

Broader local validation also passed: JSON contract validation, `make
maintainability-gate`, `make duplicate-implementation-gate`, `make
quality-baseline`, `make rfc0002-github-issue-execution-ledger-gate`, `make
rfc0002-github-issue-learning-pattern-gate`, `make
rfc0002-github-issue-execution-state-audit`, `make
rfc0002-github-issue-execution-summary`, `make documentation-contract-gate`,
full `make typecheck`, full `make lint`, and `git diff --check`. The refreshed
quality baseline no longer lists `evaluate_low_income_signal(...)`.

The focused unit suite now includes an access-scope identity regression proving
that two private-banking review scopes with identical source evidence produce
different candidate identities and preserve their candidate access scopes.

PR `#933` merged to main at
`c56c4aa0e7a558a6110b7ab81465b890bda563c6` from PR head
`4af3d9373c6ac4fd3fdb8166bd14bae4e1625142`. Stable implementation commit
`fba81c2f48080381f958eb90308df90793798a11` is in the merged history.
PR #933 passed Feature Lane, PR Merge Gate, Queue Auto Merge, and CodeQL before
merge; exact-main Main Releasability run `31501670883` and exact-main Push on
main run `31501662661` passed for
`c56c4aa0e7a558a6110b7ab81465b890bda563c6`.

This is internal domain maintainability only. It does not change API/OpenAPI
behavior, Core cashflow or cash-movement source authority, persistence schema,
migrations, authentication or authorization infrastructure, production
IdP/session-token authority, Gateway, Workbench, supported-feature promotion,
runtime topology, wiki source, client publication, or final RFC-0002 closure.

## 2026-08-11: Manage Mandate Runtime Receipt Reconciliation Boundary

Issue `#926` applies the RFC-0002 Slice 12/13 and Slice 19
maintainability lens to
`src/app/application/manage_mandate_runtime_evidence/contract.py::_receipts_reconcile(...)`.
The current `make quality-baseline` report listed the function as a `108` line
production hotspot in the closed v3 Lotus Manage mandate runtime-evidence
contract.

The validator mixed:

1. Idea request scope and evaluated-at reconciliation,
2. Manage temporal receipt identity reconciliation,
3. Performance and Risk mandate-health source receipt qualification,
4. upstream and aggregate source-ref digest reconstruction,
5. action-register supportability and count checks,
6. allocation-drift outcome and candidate-identity rules.

`src/app/application/manage_mandate_runtime_evidence/contract.py` now keeps the
public `manage_mandate_runtime_execution_is_valid(...)` behavior and schema
stable while extracting named helpers for request scope, action temporal
identity, source receipt qualification, source-ref digest reconciliation,
action-register supportability, and allocation-drift outcome validation. The
original receipt reconciliation function is now a short coordinator over those
proof-contract responsibilities.

Focused validation passed:

1. `python -m ruff check src/app/application/manage_mandate_runtime_evidence/contract.py tests/unit/manage_mandate_runtime_evidence/test_runtime_execution.py`,
2. `python -m ruff format --check src/app/application/manage_mandate_runtime_evidence/contract.py tests/unit/manage_mandate_runtime_evidence/test_runtime_execution.py`,
3. `python -m mypy src/app/application/manage_mandate_runtime_evidence/contract.py`,
4. `python -m pytest tests/unit/manage_mandate_runtime_evidence/test_runtime_execution.py -q`
   (`58` passed).

Broader validation also passed: `make maintainability-gate`,
`make duplicate-implementation-gate`, `make quality-baseline`,
`make rfc0002-github-issue-execution-ledger-gate`,
`make rfc0002-github-issue-execution-state-audit`,
`make rfc0002-github-issue-execution-summary`, `make documentation-contract-gate`,
`make typecheck`, full `make lint`, PR text gate, and `git diff --check`.
PR `#927` merged by rebase to exact-main SHA
`17aba428572ef38fb30b8a0bec16e2b77eaae85b`; exact-main Main Releasability
`31493352525` and Push on main `31493345202` passed for that SHA.

This is internal proof-contract maintainability only. It does not change
API/OpenAPI behavior, persistence schema, migrations, authentication or
authorization infrastructure, production IdP/session/token-claims authority,
Core, Gateway, Workbench, downstream live certification, Report/Render/Archive
authority, supported-feature promotion, client publication, runtime topology,
wiki source, or final RFC-0002 closure. Issue `#379` remains the live
downstream certification authority.

## 2026-08-11: Outbox Delivery Application Orchestration Boundary

Issue `#914` applies the RFC-0002 Slice 15 maintainability lens to
`src/app/application/outbox/delivery.py::run_outbox_delivery_once(...)`.
The current `make quality-baseline` report listed the function as a `109` line
production hotspot in an operator-facing outbox delivery path.

The use case mixed:

1. input, UTC, and capacity validation,
2. lease-owner, lease-attempt, and operator-run identity construction,
3. idempotency replay and conflict handling,
4. outbox event claim-window construction,
5. publisher execution and source-safe failure mapping,
6. repository publish/fail/dead-letter decision mapping,
7. final operator summary aggregation.

`src/app/application/outbox/delivery.py` now keeps the public
`run_outbox_delivery_once(...)` signature and behavior stable while extracting
named helpers for run context construction, idempotency status handling, event
claiming, batch delivery, single-event publisher/repository result
classification, and final summary assembly. The public use case is now a
short coordinator over those application-layer boundaries.

Focused validation passed:

1. `.venv\Scripts\python.exe -m pytest tests\unit\outbox\test_outbox_delivery.py -q`
   (`17` passed),
2. `.venv\Scripts\python.exe -m ruff check src\app\application\outbox\delivery.py tests\unit\outbox\test_outbox_delivery.py`,
3. `.venv\Scripts\python.exe -m ruff format --check src\app\application\outbox\delivery.py tests\unit\outbox\test_outbox_delivery.py`,
4. `.venv\Scripts\python.exe -m mypy src\app\application\outbox\delivery.py tests\unit\outbox\test_outbox_delivery.py`,
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate` (`0` duplicate clusters),
7. `make quality-baseline`.

The focused outbox delivery test suite now includes a repository-race
regression proving a failed publisher attempt whose repository failure mark
loses the lease is counted as skipped, not failed or dead-lettered, while still
preserving the bounded `publisher_rejected` failure reason.

This is internal application-layer maintainability only. It does not change
API/OpenAPI behavior, persistence schema, migrations, authentication or
authorization infrastructure, external broker runtime certification,
platform-mesh publication, Gateway/Workbench behavior, supported-feature
promotion, client publication, runtime topology, wiki source, or final
RFC-0002 closure. No wiki publication is required because no operator-facing
command or published wiki truth changed.

## 2026-08-11: Downstream Proof Application Helper Boundary

Issue `#911` applies the RFC-0002 Slice 12/13 maintainability lens to
`src/app/application/downstream_realization_readiness.py::_apply_available_downstream_proofs(...)`.
After the Slice 12/13 public builder split in issue `#894`, the report-only
quality baseline still listed `_apply_available_downstream_proofs(...)` as a
`109` line production hotspot.

The helper mixed:

1. Advise, Manage, and Report source-contract supporting-evidence checks,
2. Advise, Manage, and Report runtime-execution blocker-clearing checks,
3. proof-artifact registry effect validation,
4. aggregate proof freshness validation,
5. route-foundation updates,
6. live-intake and materialization blocker reduction.

`src/app/application/downstream_realization_readiness.py` now keeps the public
`build_downstream_realization_readiness_snapshot(...)` signature and readiness
behavior stable while introducing
`_apply_source_contract_proofs_if_valid(...)`,
`_apply_runtime_execution_proofs_if_valid(...)`,
`_apply_advise_intake_proof_if_valid(...)`. This keeps source-contract
supporting evidence separate from runtime-execution blocker-clearing evidence.
The generic proof input and proof-effect/freshness guard logic now lives in
`src/app/application/downstream_realization_proof_application.py` as
`DownstreamProofInputs`, `supporting_source_contract_proof_is_valid(...)`, and
`current_blocker_clearing_proof_is_valid(...)`, keeping the readiness module
under the maintainability line-count cap.

The focused downstream-realization readiness test suite now includes
`test_report_intake_runtime_execution_clears_only_live_intake_blocker`. The test
proves a current Report intake runtime receipt clears only
`lotus_report_live_intake_route_proof_missing`, keeps materialization, render,
archive, and client-publication blockers intact, keeps readiness blocked and
supportability not certified, and preserves the no-route-promotion boundary by
leaving `target_route` on the planned route while setting
`route_fit_status` to `route_foundation_proven_not_certified`.

Focused validation passed:

1. `.venv\Scripts\python.exe -m ruff check src\app\application\downstream_realization_readiness.py src\app\application\downstream_realization_proof_application.py tests\unit\test_downstream_realization_readiness.py`,
2. `.venv\Scripts\python.exe -m ruff format --check src\app\application\downstream_realization_readiness.py src\app\application\downstream_realization_proof_application.py tests\unit\test_downstream_realization_readiness.py`,
3. `.venv\Scripts\python.exe -m mypy src\app\application\downstream_realization_readiness.py src\app\application\downstream_realization_proof_application.py tests\unit\test_downstream_realization_readiness.py`,
4. `.venv\Scripts\python.exe -m pytest tests\unit\test_downstream_realization_readiness.py -q`
   (`14` passed).

This is internal application-layer maintainability only. It does not change
API/OpenAPI behavior, persistence schema, migrations, authentication or
authorization infrastructure, Gateway/Workbench runtime proof, Advise, Manage,
Report, Render, or Archive live certification, production
identity/session-token authority, supported-feature promotion, client
publication, runtime topology, wiki source, or final RFC-0002 closure. No wiki
publication is required because no operator-facing command or published wiki
truth changed.

## 2026-08-11: Underperformance Signal Evaluator Boundary

Issue `#908` applies the RFC-0002 Slice 19 maintainability lens to the
underperformance signal evaluator while preserving the Slice 04/16
underperformance opportunity signal semantics. The report-only quality baseline
listed `src/app/domain/signal_evaluation.py::evaluate_underperformance_signal`
at `110` lines.

The evaluator mixed:

1. evaluation-time validation,
2. entitlement and Performance source-reference gating,
3. source temporal and freshness checks,
4. benchmark-context gating,
5. duplicate suppression,
6. active-return validation and materiality,
7. signal, lineage, evidence-packet, and candidate construction,
8. final evaluation-result assembly.

`src/app/domain/signal_evaluation.py` now keeps the public
`evaluate_underperformance_signal(...)` signature and behavior stable while
extracting named helpers for pre-source gating, source-readiness gating,
materiality evaluation, bounded active-return validation, source refs, signal
construction, lineage construction, evidence packet construction, candidate
construction, and final result assembly. The public evaluator is now `15` lines;
the extracted helper boundaries are `4`, `16`, `31`, `26`, `28`, `4`, `12`,
`9`, `17`, `23`, and `4` lines.

Focused validation passed:

1. `.venv/Scripts/python.exe -m pytest tests/unit/test_underperformance_signal_evaluation.py -q`
   (`14` passed),
2. `.venv/Scripts/python.exe -m ruff check src/app/domain/signal_evaluation.py tests/unit/test_underperformance_signal_evaluation.py`,
3. `.venv/Scripts/python.exe -m ruff format --check src/app/domain/signal_evaluation.py tests/unit/test_underperformance_signal_evaluation.py`,
4. `.venv/Scripts/python.exe -m mypy src/app/domain/signal_evaluation.py`,
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate` (`0` duplicate clusters),
7. `make quality-baseline`.

The positive-case unit test now asserts the source refs, evidence packet,
lineage, signal, and candidate retain one stable source-backed identity. Existing
fail-closed tests continue to prove entitlement denial, missing Performance
source refs, stale source evidence, missing benchmark context, missing active
return, out-of-range active return, duplicate suppression, and below-materiality
behavior.

This is internal domain maintainability only. It does not change API/OpenAPI
behavior, source-authority contracts, Performance/Core/Gateway/Workbench
runtime evidence, persistence, migrations, authentication or authorization
infrastructure, wiki source, supported-feature posture, data-mesh certification,
client publication, or final RFC-0002 closure. No wiki publication is required
because no operator-facing command or published readiness truth changed.

## 2026-08-11: Downstream Realization Readiness Composition Boundary

Issue `#894` applies the RFC-0002 Slice 12/13 maintainability lens to the
downstream-realization readiness application boundary. The report-only quality
baseline listed `src/app/application/downstream_realization_readiness.py` at
`1,186` lines and
`build_downstream_realization_readiness_snapshot(...)` at `113` lines.

The public readiness builder mixed:

1. repository readiness-summary loading,
2. capability and contract-plan construction,
3. available proof application,
4. blocker aggregation,
5. source-of-truth mapping,
6. final response snapshot assembly.

`src/app/application/downstream_realization_readiness.py` now keeps the public
`build_downstream_realization_readiness_snapshot(...)` signature and behavior
stable while extracting named helpers for initial capability/contract
construction, blocker aggregation, final snapshot assembly, and source-of-truth
mapping. The public builder is now `63` lines; the extracted helper boundaries
are `13`, `11`, `31`, and `24` lines. The file remains within the source
maintainability threshold at `1,198` lines.

Focused validation passed:

1. `.venv/Scripts/python.exe -m ruff format src/app/application/downstream_realization_readiness.py tests/unit/test_downstream_realization_readiness.py`,
2. `.venv/Scripts/python.exe -m ruff check src/app/application/downstream_realization_readiness.py tests/unit/test_downstream_realization_readiness.py`,
3. `.venv/Scripts/python.exe -m mypy src/app/application/downstream_realization_readiness.py tests/unit/test_downstream_realization_readiness.py`,
4. `.venv/Scripts/python.exe -m pytest tests/unit/test_downstream_realization_readiness.py -q`
   (`13` passed),
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate` (`0` duplicate clusters),
7. `make architecture-boundary-gate`,
8. `make rfc0002-github-issue-execution-ledger-gate`,
9. `make rfc0002-github-issue-learning-pattern-gate`,
10. `make rfc0002-github-issue-execution-summary`.

The focused regression tests now assert the source-of-truth map values that
were moved behind the named helper, while preserving existing projection-only
repository use, blocker aggregation, source-contract non-clearing posture, and
runtime-proof blocker-clearing boundaries.

This is internal application-layer maintainability only. It does not change
API/OpenAPI behavior, downstream readiness response semantics, blocker
vocabulary, evidence refs, issue refs, source-owner authority, persistence,
migrations, authentication or authorization infrastructure, Gateway,
Workbench, runtime topology, wiki source, supported features, data-mesh
certification, client publication, or supported-feature promotion. No wiki
publication is required because no operator-facing command or readiness truth
changed.

## 2026-08-11: Review Queue API Route Composition Boundary

Issue `#897` applies the RFC-0002 Slice 08/10/11 maintainability lens to the
review-queue API route boundary. The report-only quality baseline listed
`src/app/api/review_queue/routes.py::_get_business_review_queue` at `112`
lines, making it the largest measured source API/application function.

The route helper mixed:

1. caller-context construction,
2. role/capability authorization,
3. evaluation-time defaulting and timezone validation,
4. requested scope validation,
5. caller entitlement-scope intersection,
6. repository/provider selection,
7. queue command construction,
8. snapshot-token Problem Details mapping,
9. operation-event emission,
10. response projection.

`src/app/api/review_queue/routes.py` now keeps the public advisor, portfolio
manager, and compliance route behavior stable while extracting named helpers
for authorized caller resolution, evaluation-time validation, effective access
scope resolution, and review-queue command construction. The public helper is
now `56` lines; the extracted helpers are `42`, `7`, `40`, and `15` lines.
The refreshed `make quality-baseline` report no longer lists
`_get_business_review_queue` in the top-10 largest functions.

Focused validation passed:

1. `.venv/Scripts/python.exe -m ruff format src/app/api/review_queue/routes.py`,
2. `.venv/Scripts/python.exe -m ruff check src/app/api/review_queue/routes.py`,
3. `.venv/Scripts/python.exe -m mypy src/app/api/review_queue/routes.py`,
4. `.venv/Scripts/python.exe -m pytest tests/integration/test_review_queue_api.py tests/integration/test_api_operation_events.py -q`
   (`51` passed),
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate` (`0` duplicate clusters),
7. `make architecture-boundary-gate`,
8. `make documentation-contract-gate`,
9. `make rfc0002-github-issue-execution-ledger-gate`,
10. `make rfc0002-github-issue-learning-pattern-gate`,
11. `make rfc0002-github-issue-execution-state-audit`,
12. `make rfc0002-github-issue-execution-summary`,
13. `make quality-baseline`.

The source-controlled RFC-0002 issue ledger now tracks `#897` as
`open_in_progress`, the gate-policy contract includes the required open-issue
evidence fragments, and the learning-pattern ledger records that review-queue
route refactors must keep caller-context, role/capability, entitlement-scope,
snapshot-token, operation-event, and response-projection boundaries explicit
without converting route maintainability into Workbench/Gateway runtime proof
or supported-feature claims.

This is internal API-boundary maintainability only. It does not change route
paths, OpenAPI metadata, response schemas, persistence, migrations,
authentication or authorization infrastructure, production identity or
session/token-claims authority, Gateway, Workbench, data-product
certification, runtime topology, wiki source, supported features, client
publication, or supported-feature promotion. No wiki publication is required
because no operator-facing command, public route behavior, or wiki truth
changed.

## 2026-07-19: Outbox Dead-Letter Recovery Policy Boundary

Issue `#670` applies the Slice 19 report-only quality-baseline lens to the
outbox dead-letter recovery domain policy. After issue `#668`,
`make quality-baseline` listed
`src/app/domain/outbox/recovery.py::claim_dead_letter_for_recovery` at `117`
lines, tied for the largest remaining production function.

The function mixed:

1. idempotent replay and conflict classification,
2. support-reference lookup,
3. event state classification,
4. event-family and schema eligibility,
5. recovery-attempt limit checking,
6. recovery audit construction,
7. lease fencing and accepted mutation.

`src/app/domain/outbox/recovery.py` keeps the public
`claim_dead_letter_for_recovery(...)` policy entry point stable while extracting
idempotency lookup, opaque support-reference event lookup, recoverability
classification, attempt counting, rejected-result construction, and
accepted-claim mutation into named helpers. Recovery decisions, blockers, audit
fields, support-reference behavior, lease fencing, replay/conflict behavior,
and max-attempt behavior are preserved. The current quality baseline no longer
lists `claim_dead_letter_for_recovery` in the largest-function table.

Focused validation passed:

1. `.venv/Scripts/ruff.exe format src/app/domain/outbox/recovery.py tests/unit/outbox/test_outbox_recovery.py`,
2. `.venv/Scripts/ruff.exe check src/app/domain/outbox/recovery.py tests/unit/outbox/test_outbox_recovery.py`,
3. `.venv/Scripts/python.exe -m mypy src/app/domain/outbox/recovery.py tests/unit/outbox/test_outbox_recovery.py`,
4. `.venv/Scripts/python.exe -m pytest tests/unit/outbox/test_outbox_recovery.py`
   (`13` passed),
5. `make maintainability-gate`,
6. `make quality-baseline`.

Broader release evidence passed through PR `#671`, which merged by rebase to
exact-main SHA `0c8b12666731ce60484ee8729e21535821752c89`. Local `make lint`
and `make check` passed, with `make check` reporting `4918` tests. Feature
Lane, PR Merge Gate, exact-main Main Releasability `29673780613`, and
exact-main CodeQL `29673778769` passed. Issue `#670` is closed with
`status/merged-main`; no wiki source changed, the remote feature branch was
pruned, and the local worktree returned to clean `main`.

The same-pattern scan used duplicate searches for
`claim_dead_letter_for_recovery`, `outbox recovery maintainability`, and
`dead-letter recovery domain policy maintainability`. Closed issue `#337` owns
the implemented recovery capability, and closed issue `#655` owns the
PostgreSQL recovery proof-test refactor; neither owns this domain policy
maintainability boundary.

This is domain-policy maintainability only. It does not change API/OpenAPI
behavior, persistence schema, migrations, authentication or authorization
infrastructure, external broker behavior, Gateway, Workbench, data-mesh
certification, runtime topology, wiki source, README, supported features, or
supported-feature promotion. No wiki publication is required unless later
PR/mainline evidence changes repo-authored wiki truth.

## 2026-07-19: AI Explanation Repository Evaluation Boundary

Issue `#668` applies the Slice 19 report-only quality-baseline lens to the
AI explanation repository evaluation application boundary. After issue `#666`,
`make quality-baseline` listed
`src/app/application/ai_governance.py::evaluate_ai_explanation_to_repository`
at `117` lines, making it the largest production-code hotspot.

The function mixed:

1. candidate lookup and entitlement validation,
2. deterministic request construction,
3. Lotus AI run-attestation infrastructure checks,
4. run-attestation and provider-retention verification,
5. attested output mapping,
6. deterministic fallback and local/test output evaluation,
7. lineage persistence,
8. idempotency-conflict response mapping.

`src/app/application/ai_governance.py` keeps the public
`evaluate_ai_explanation_to_repository(...)` entry point stable while extracting
candidate resolution, entitlement validation, attested evaluation,
fallback/local-output evaluation, provider-retention verification, and lineage
persistence mapping into named helpers. The public function is now `28` lines;
the attested subflow is bounded at `54` lines. Idempotency, persistence
receipts, provider-retention receipts, fallback behavior, entitlement failure,
not-found posture, and untrusted-output failure semantics are preserved.

Focused validation passed:

1. `.venv/Scripts/ruff.exe format src/app/application/ai_governance.py tests/unit/test_ai_governance.py tests/unit/test_attested_ai_explanation_application.py`,
2. `.venv/Scripts/ruff.exe check src/app/application/ai_governance.py tests/unit/test_ai_governance.py tests/unit/test_attested_ai_explanation_application.py`,
3. `.venv/Scripts/python.exe -m mypy src/app/application/ai_governance.py tests/unit/test_ai_governance.py`,
4. `.venv/Scripts/python.exe -m pytest tests/unit/test_ai_governance.py tests/unit/test_attested_ai_explanation_application.py`
   (`23` passed),
5. `make maintainability-gate`,
6. `make quality-baseline`.

The same-pattern scan used duplicate searches for
`evaluate_ai_explanation_to_repository` and `ai_governance maintainability`.
Existing issue `#340` owns external Lotus AI attestation/runtime certification,
and closed issue `#268` owns AI explanation lineage idempotency; neither owns
this application-layer maintainability root cause. This slice records a
no-wiki-change decision because operator-facing AI governance behavior and
commands are unchanged.

This is application-layer maintainability only. It does not change API/OpenAPI
contracts, persistence schema, migrations, authentication or authorization
infrastructure, live `lotus-ai` runtime execution, provider certification,
Gateway, Workbench, data-mesh certification, runtime topology,
external-publication authority, supported features, or supported-feature
promotion. Broader branch gates, PR checks, exact-main Main
Releasability/CodeQL, wiki parity/no-change evidence, issue closure, and branch
cleanup completed through PR `#669`, which merged by rebase to exact-main SHA
`11424e8c9a7d395701ced98c1d05b598ae3b631d`. Main Releasability
`29672745987` and CodeQL `29672742015` passed on that SHA. No wiki source
changed, the issue is closed with `status/merged-main`, the remote feature
branch was pruned, and local state returned to clean `main`.

## 2026-07-19: Drawdown-Review Signal Evaluation Boundary

Issue `#661` applies the Slice 19 report-only quality-baseline lens to the
drawdown-review signal evaluator. After issue `#659`, `make quality-baseline`
listed `src/app/domain/signal_evaluation.py::evaluate_drawdown_review_signal`
at `118` lines.

The function mixed:

1. evaluation-time validation,
2. entitlement and source-readiness blockers,
3. temporal, freshness, and supportability checks,
4. duplicate suppression,
5. drawdown materiality validation,
6. stable identity, signal, lineage, evidence packet, candidate, and result
   assembly.

`src/app/domain/signal_evaluation.py` keeps the public
`evaluate_drawdown_review_signal` export, while
`src/app/domain/drawdown_review_evaluation.py` now owns the drawdown-review
domain evaluator. `src/app/domain/signal_evaluation_common.py` owns the shared
blocked/temporal result helpers used by signal evaluators. Drawdown-review
outcome ordering, family compatibility, source refs, unsupported evidence
reasons, candidate identity, evidence packet reason codes, and source-authority
semantics are preserved.

Focused validation passed:

1. `python -m ruff check src/app/domain/signal_evaluation.py src/app/domain/drawdown_review_evaluation.py src/app/domain/signal_evaluation_common.py tests/unit/test_drawdown_review_signal_evaluation.py`,
2. `python -m ruff format --check src/app/domain/signal_evaluation.py src/app/domain/drawdown_review_evaluation.py src/app/domain/signal_evaluation_common.py tests/unit/test_drawdown_review_signal_evaluation.py`,
3. `python -m mypy src/app/domain/signal_evaluation.py src/app/domain/drawdown_review_evaluation.py src/app/domain/signal_evaluation_common.py`,
4. `python -m pytest tests/unit/test_drawdown_review_signal_evaluation.py tests/unit/test_drawdown_review_application.py tests/integration/test_drawdown_review_signal_api.py -q`
   (`30` passed),
5. `python -m pytest tests/unit/test_source_temporal_contract_gate.py tests/unit/test_opportunity_family_compatibility.py -q`
   (`4` passed),
6. `make quality-baseline`,
7. `make maintainability-gate`,
8. `make duplicate-implementation-gate` (`0` duplicate clusters across `3,017`
   source/script functions).

This is internal domain modularity only. It does not change API/OpenAPI
behavior, source-authority contracts, Lotus Risk methodology, persistence,
migrations, authentication or authorization infrastructure, Core, Gateway,
Workbench, runtime topology, wiki source, README, supported-features, data-mesh
certification, external-publication authority, or supported-feature promotion.
Adjacent `evaluate_high_volatility_signal` remains a measured risk-domain
sibling at `117` lines and should be handled by a separate issue-backed slice.
Broader local gates, PR checks, exact-main Main Releasability/CodeQL, wiki
parity, issue closure, and branch cleanup remain pending for the tranche.

## 2026-07-19: Implementation Proof Consumption Scope Dispatcher Boundary

Issue `#659` applies the Slice 19 report-only quality-baseline lens to the
implementation-proof consumption dispatcher. After issue `#658`,
`make quality-baseline` listed
`src/app/application/implementation_proof_consumption.py::_apply_available_proofs`
at `119` lines.

The function mixed:

1. a mirrored keyword-only signature for the whole proof-scope mapping,
2. storage/runtime proof dispatch,
3. AI proof dispatch,
4. downstream proof dispatch,
5. platform/surface/operator proof dispatch,
6. opportunity-archetype proof dispatch.

`src/app/application/implementation_proof_consumption.py` now keeps
`apply_available_proofs_from_scope(capabilities, scope)` as the public entry
point, but `_apply_available_proofs(...)` consumes the existing proof scope
directly and delegates through typed extraction helpers plus family-specific
scope adapters. Proof validation, registered effect matching, evidence refs,
blocker clearing, and supported-feature non-promotion semantics are preserved.

Focused validation passed:

1. `python -m ruff check src/app/application/implementation_proof_consumption.py`,
2. `python -m ruff format --check src/app/application/implementation_proof_consumption.py`,
3. `python -m mypy src/app/application/implementation_proof_consumption.py`,
4. `python -m pytest tests/unit/test_implementation_proof_readiness.py tests/unit/implementation_proof/test_effect_enforcement.py tests/integration/test_implementation_proof_readiness_api.py -q`
   (`42` passed).

This is application-layer maintainability only. It does not change readiness
behavior, proof-artifact contract behavior, API/OpenAPI, persistence,
migrations, authentication or authorization infrastructure, Core, Gateway,
Workbench, runtime topology, wiki source, README, supported-features, data-mesh
certification, external-publication authority, or supported-feature promotion.
Broader local gates, PR checks, exact-main Main Releasability/CodeQL, wiki
parity, issue closure, and branch cleanup remain pending for the tranche.

## 2026-07-19: CI Release Evidence Target Validator Boundary

Issue `#658` applies the Slice 19 report-only quality-baseline lens to the
CI release evidence target validator. After issue `#656`,
`make quality-baseline` listed
`scripts/ci_release_evidence_contract.py::validate_release_evidence_targets` at
`119` lines.

The public validator mixed:

1. release image defaults and CI-only image publication policy,
2. docker-build provenance arguments,
3. container runtime smoke wiring,
4. release image identity wiring,
5. reproducible SBOM target checks,
6. container-image scan policy and pinned Trivy wiring.

`scripts/ci_release_evidence_contract.py` now keeps
`validate_release_evidence_targets(makefile)` as the public entry point, but it
delegates to named helpers for release image defaults, docker-build target
provenance, existing smoke/identity checks, release SBOM, and container-image
scan policy. Error strings and ordering are preserved.

Focused validation passed:

1. `python -m ruff check scripts/ci_release_evidence_contract.py`,
2. `python -m ruff format --check scripts/ci_release_evidence_contract.py`,
3. `python -m mypy scripts/ci_release_evidence_contract.py`,
4. `python -m pytest tests/unit/test_ci_release_evidence_contract.py tests/unit/test_ci_enforcement_contract.py -q`
   (`82` passed).

This is CI/release-evidence maintainability only. It does not change Makefile
behavior, CI workflow behavior, Dockerfile behavior, release evidence semantics,
image publication policy, runtime topology, wiki source, README,
supported-features, API/OpenAPI, persistence, migrations, authentication or
authorization infrastructure, Core, Gateway, Workbench, data-mesh
certification, external-publication authority, or supported-feature promotion.
Broader local gates, PR checks, exact-main Main Releasability/CodeQL, wiki
parity, issue closure, and branch cleanup remain pending for the tranche.

## 2026-07-19: Implementation Proof Readiness API Artifact Setup Boundary

Issue `#656` applies the Slice 19 report-only quality-baseline lens to the
implementation-proof readiness API configured-artifact setup. After issue
`#655`, `make quality-baseline` listed
`tests/integration/test_implementation_proof_readiness_api.py::_configure_readiness_proof_artifacts`
at `121` lines.

The helper mixed:

1. aggregate proof provenance binding,
2. configured proof-artifact path construction,
3. source-ingestion, durable repository, telemetry, AI, Workbench, Report, and
   bond-maturity proof payload writing,
4. environment-variable binding for the readiness API integration path.

`tests/integration/test_implementation_proof_readiness_api.py` now keeps the
same configured-artifact readiness API proof, but `_configure_readiness_proof_artifacts(...)`
is a short orchestrator over named helpers for provenance, typed paths, payload
writes, and environment binding. Artifact filenames, payload builders, env vars,
readiness blockers, source-safe evidence refs, and supported-feature
non-promotion assertions are preserved.

Focused validation passed:

1. `python -m ruff check tests/integration/test_implementation_proof_readiness_api.py`,
2. `python -m ruff format --check tests/integration/test_implementation_proof_readiness_api.py`,
3. `python -m mypy tests/integration/test_implementation_proof_readiness_api.py`,
4. `python -m pytest tests/integration/test_implementation_proof_readiness_api.py -q`
   (`8` passed).

This is test-support maintainability only. It does not change production
readiness behavior, proof-artifact contract behavior, API/OpenAPI, persistence,
migrations, authentication or authorization infrastructure, Core, Gateway,
Workbench, runtime topology, wiki source, README, supported-features, data-mesh
certification, external-publication authority, or supported-feature promotion.
Broader local gates, PR checks, exact-main Main Releasability/CodeQL, wiki
parity, issue closure, and branch cleanup remain pending for the tranche.

## 2026-07-19: PostgreSQL Outbox Recovery Workflow Proof Boundary

Issue `#655` applies the Slice 19 report-only quality-baseline lens to the
PostgreSQL outbox recovery workflow proof. After issue `#654`,
`make quality-baseline` listed
`tests/unit/outbox/test_postgres_delivery_adapter.py::test_postgres_outbox_recovery_is_durable_idempotent_and_lease_fenced`
at `125` lines.

The test mixed:

1. candidate/outbox dead-letter setup,
2. newer pending event fan-out,
3. support-reference and recovery claim construction,
4. accepted, replayed, and competing lease-conflict recovery decisions,
5. recovery audit and source-safe row assertions,
6. support-reference lookup SQL-shape assertions,
7. invalid delivery input validation assertions.

`tests/unit/outbox/test_postgres_delivery_adapter.py` now keeps one externally
visible durable/idempotent/lease-fenced recovery proof, but the public test is
a short orchestrator over named helpers for each proof boundary. Event states,
support references, idempotency keys, lease attempts, failure reasons,
SQL-shape assertions, validation errors, and recovery decisions are preserved.

Focused validation passed:

1. `python -m ruff check tests/unit/outbox/test_postgres_delivery_adapter.py`,
2. `python -m ruff format --check tests/unit/outbox/test_postgres_delivery_adapter.py`,
3. `python -m mypy tests/unit/outbox/test_postgres_delivery_adapter.py`,
4. `python -m pytest tests/unit/outbox/test_postgres_delivery_adapter.py -q`
   (`9` passed).

This is test-support maintainability only. It does not change production
outbox delivery/recovery behavior, PostgreSQL repository implementation,
API/OpenAPI, persistence, migrations, authentication or authorization
infrastructure, Core, Gateway, Workbench, runtime topology, wiki source,
README, supported-features, data-mesh certification, external-publication
authority, or supported-feature promotion. Broader local gates, PR checks,
exact-main Main Releasability/CodeQL, wiki parity, issue closure, and branch
cleanup remain pending for the tranche.

## 2026-07-19: Data Lifecycle Fake PostgreSQL Cursor Dispatcher Boundary

Issue `#654` applies the Slice 19 report-only quality-baseline lens to the
data-lifecycle PostgreSQL policy fake cursor. After issue `#653`,
`make quality-baseline` listed
`tests/unit/data_lifecycle/test_postgres_policy.py::execute` at `127` lines.
Inspection showed this is `LifecycleCursor.execute(...)`, the fake PostgreSQL
cursor dispatcher.

The dispatcher mixed:

1. SQL normalization and execution recording,
2. advisory lock no-op handling,
3. lifecycle operation lookup by idempotency key, authority receipt, and
   archive receipt,
4. candidate and lifecycle-control row loading,
5. active outbox and downstream submission count loading,
6. linked report evidence-pack row loading,
7. lifecycle-control update mutation,
8. lifecycle-operation insert recording.

`tests/unit/data_lifecycle/test_postgres_policy.py` now keeps the same fake
cursor behavior, but `LifecycleCursor.execute(...)` is a dispatcher over named
SQL-family helpers. Stable column tuples replace embedded update/insert key
lists. SQL matching behavior, rows, rowcount, operation-map updates, control
updates, commit/rollback tests, and assertion semantics are preserved.

Focused validation passed:

1. `python -m ruff check tests/unit/data_lifecycle/test_postgres_policy.py`,
2. `python -m ruff format --check tests/unit/data_lifecycle/test_postgres_policy.py`,
3. `python -m mypy tests/unit/data_lifecycle/test_postgres_policy.py`,
4. `python -m pytest tests/unit/data_lifecycle/test_postgres_policy.py -q`
   (`16` passed).

This is test-support maintainability only. It does not change production
data-lifecycle policy behavior, PostgreSQL repository implementation,
API/OpenAPI, persistence, migrations, authentication or authorization
infrastructure, Core, Gateway, Workbench, runtime topology, wiki source,
README, supported-features, data-mesh certification, external-publication
authority, or supported-feature promotion. Broader local gates, PR checks,
exact-main Main Releasability/CodeQL, wiki parity, issue closure, and branch
cleanup remain pending for the tranche.

## 2026-07-19: Implementation Proof Readiness Capability Assertion Boundary

Issue `#653` applies the Slice 19 report-only quality-baseline lens to the
implementation-proof readiness source-safe capability test. After issue `#652`,
`make quality-baseline` listed
`tests/unit/test_implementation_proof_readiness.py::test_implementation_proof_readiness_capabilities_are_source_safe`
at `138` lines.

The test mixed:

1. expected capability inventory assertions,
2. repeated capability lookup,
3. runtime trust telemetry evidence and blocker assertions,
4. outbox delivery evidence and blocker assertions,
5. source-ingestion evidence and blocker assertions,
6. opportunity archetype evidence, blocker, readiness, supportability, and
   supported-feature non-promotion assertions,
7. downstream realization evidence and blocker assertions,
8. AI explanation evidence and model-risk blocker assertions,
9. serialized no-leak posture assertions.

`tests/unit/test_implementation_proof_readiness.py` now keeps one externally
visible source-safe readiness capability proof, but the public test is a short
snapshot-building orchestrator over named helpers for capability inventory,
capability lookup, each capability-family assertion, and serialized no-leak
posture. Capability IDs, evidence refs, blocker checks, readiness/supportability
assertions, supported-feature non-promotion assertions, and no-leak assertions
are preserved.

Focused validation passed:

1. `python -m ruff check tests/unit/test_implementation_proof_readiness.py`,
2. `python -m ruff format --check tests/unit/test_implementation_proof_readiness.py`,
3. `python -m mypy tests/unit/test_implementation_proof_readiness.py`,
4. `python -m pytest tests/unit/test_implementation_proof_readiness.py -q`
   (`28` passed).

This is test-support maintainability only. It does not change production
readiness behavior, proof-artifact semantics, API/OpenAPI, persistence,
migrations, authentication or authorization infrastructure, Core, Gateway,
Workbench, runtime topology, wiki source, README, supported-features,
data-mesh certification, external-publication authority, or supported-feature
promotion. Broader local gates, PR checks, exact-main Main
Releasability/CodeQL, wiki parity, issue closure, and branch cleanup remain
pending for the tranche.

## 2026-07-19: Configured Proof Artifacts Source-Safe Ref Test Boundary

Issue `#652` applies the Slice 19 report-only quality-baseline lens to the
configured implementation-proof artifact source-safe refs test. After issue
`#650`, `make quality-baseline` listed
`tests/unit/test_proof_artifacts.py::test_configured_implementation_proof_artifacts_loads_relative_source_safe_refs`
at `146` lines.

The test mixed:

1. proof-artifact path construction,
2. fixture artifact writing,
3. relative environment variable binding,
4. configured proof-artifact loading,
5. durable repository proof assertions,
6. source-ingestion, runtime trust telemetry, AI, Workbench/Gateway, outbox,
   platform catalog, bond-maturity, and low-income proof-family assertions,
7. aggregate-proof provenance assertions.

`tests/unit/test_proof_artifacts.py` now keeps one externally visible
configured-artifacts proof, but the public test is a short setup/load/assert
orchestrator over named helpers for configured artifact paths, artifact fixture
writing, relative environment binding, and typed proof-family assertions.
Artifact names, environment variables, relative refs, provenance assertions,
and non-object rejection behavior are preserved.

Focused validation passed:

1. `python -m ruff check tests/unit/test_proof_artifacts.py`,
2. `python -m ruff format --check tests/unit/test_proof_artifacts.py`,
3. `python -m mypy tests/unit/test_proof_artifacts.py`,
4. `python -m pytest tests/unit/test_proof_artifacts.py -q` (`2` passed).

This is test-support maintainability only. It does not change proof-artifact
runtime behavior, production API behavior, API/OpenAPI, persistence,
migrations, authentication or authorization infrastructure, Core, Gateway,
Workbench, runtime topology, wiki source, README, supported-features,
data-mesh certification, external-publication authority, or supported-feature
promotion. Broader local gates, PR checks, exact-main Main
Releasability/CodeQL, wiki parity, issue closure, and branch cleanup remain
pending for the tranche.

## 2026-07-19: Critical Idea Workflow E2E Authority Boundary Test Boundary

Issue `#650` applies the Slice 19 report-only quality-baseline lens to the
critical Idea workflow E2E authority-boundary proof. After issue `#648`,
`make quality-baseline` listed
`tests/e2e/test_critical_idea_workflow.py::test_critical_idea_workflow_preserves_authority_boundaries`
at `153` lines.

The test mixed:

1. high-cash candidate creation and persistence,
2. advisor queue visibility and ranked review posture,
3. lifecycle transitions to review-ready,
4. review approval without downstream authority,
5. conversion intent with Report-owned `intent_only` posture,
6. report evidence-pack request semantics without render/archive/publication
   authority,
7. client-ready publication rejection without portfolio identity leakage,
8. candidate detail replay with durable-storage and supported-feature
   non-promotion proof.

`tests/e2e/test_critical_idea_workflow.py` now keeps one externally visible
E2E workflow proof, but the public test is a short orchestrator over named
helpers for each domain step and authority-boundary assertion. All routes,
payloads, headers, status codes, and assertions are preserved.

Focused validation passed:

1. `python -m ruff check tests/e2e/test_critical_idea_workflow.py`,
2. `python -m ruff format --check tests/e2e/test_critical_idea_workflow.py`,
3. `python -m mypy tests/e2e/test_critical_idea_workflow.py`,
4. `python -m pytest tests/e2e/test_critical_idea_workflow.py -q` (`1`
   passed).

This is test-support maintainability only. It does not change production API
behavior, OpenAPI, persistence, migrations, authentication or authorization
infrastructure, Core, Gateway, Workbench, runtime topology, wiki source,
README, supported-features, data-mesh certification, external-publication
authority, or supported-feature promotion. Broader local gates, PR checks,
exact-main Main Releasability/CodeQL, wiki parity, issue closure, and branch
cleanup remain pending for the tranche.

## 2026-07-19: PostgreSQL Runtime Workflow Integration Test Boundary

Issue `#648` applies the Slice 19 report-only quality-baseline lens to the
PostgreSQL runtime workflow integration proof. After issue `#645`,
`make quality-baseline` listed
`tests/integration/test_postgres_runtime_integration.py::test_postgres_runtime_provider_persists_review_conversion_and_report_workflow`
at `174` lines.

The test mixed:

1. high-cash persisted API setup,
2. advisor queue durable reload proof,
3. lifecycle transition to review-ready,
4. review action persistence and replay,
5. feedback persistence,
6. conversion intent persistence and replay,
7. conversion outcome persistence,
8. report evidence-pack persistence and replay,
9. table-count verification,
10. SQL outbox query and lineage assertions.

`tests/integration/test_postgres_runtime_integration.py` now keeps one
externally visible PostgreSQL-backed integration scenario, but the public test
is a short orchestrator over named helpers for candidate persistence, advisor
queue reload, review/replay, feedback, conversion/replay, outcome,
report/replay, table counts, and outbox-lineage proof. The refactored workflow
test no longer appears in the report-only top-function list; the new largest
function is the E2E authority-boundary test at `153` lines.

Focused validation passed:

1. `python -m ruff check tests/integration/test_postgres_runtime_integration.py`,
2. `python -m ruff format --check tests/integration/test_postgres_runtime_integration.py`,
3. `python -m mypy tests/integration/test_postgres_runtime_integration.py`.

The focused PostgreSQL test command
`python -m pytest tests/integration/test_postgres_runtime_integration.py::test_postgres_runtime_provider_persists_review_conversion_and_report_workflow -q`
was source-collected and skipped because the local PostgreSQL integration
fixture was not active. Broader local quality gates passed:

1. `make quality-baseline`,
2. `make maintainability-gate`,
3. `make duplicate-implementation-gate` with zero duplicate clusters across
   `3,004` source/script functions.

The same-pattern scan covered
#601/#603/#606/#609/#618/#620/#623/#625/#630/#633/#636/#638/#640/#642/#645
maintainability evidence, current `quality/baseline_report.md`, GitHub
duplicate searches for
`test_postgres_runtime_provider_persists_review_conversion_and_report_workflow`,
`review conversion report workflow quality baseline`,
`test_postgres_runtime_integration.py maintainability`, and
`PostgreSQL runtime integration workflow`, the codebase review ledger, the
issue closure matrix, RFC Slice 19, and issue-discovery ledger `#225`.

This is test-support maintainability only. It does not change production
PostgreSQL adapters, schema, migrations, API/OpenAPI behavior, authentication
or authorization infrastructure, Core, Gateway, Workbench, data-product
support, external-publication authority, runtime topology, wiki source,
README, supported features, or supported-feature promotion.

PR `#649` merged by rebase to exact-main SHA
`af95892e53243396441c81796cf2e61af2d2e7ad`. Exact-main Main Releasability
`29663395035` and CodeQL `29663391657` passed on that SHA, including
PostgreSQL runtime proof, combined coverage, Docker build, image scan,
digest-bound runtime smoke, signing, provenance, SBOM attestation, release
metadata, image identity binding, license binding, and CI signal evidence.
Strict wiki parity passed with `DiffCount 0`; no wiki publication was needed
because no wiki source changed. The implementation branch was deleted locally
after patch-equivalence verification and remotely by GitHub.

## 2026-07-19: PostgreSQL Mutating Workflow Test Boundary

Issue `#645` applies the Slice 19 report-only quality-baseline lens to the
PostgreSQL repository mutating workflow regression. After issue `#642`,
`make quality-baseline` listed
`tests/unit/test_postgres_repository.py::test_postgres_repository_round_trips_mutating_workflow_details`
at `178` lines.

The test mixed:

1. review-ready and approved candidate setup,
2. lifecycle transition persistence,
3. review action and feedback persistence,
4. conversion intent and outcome persistence,
5. report evidence-pack persistence,
6. evidence replay and idempotency prechecks,
7. conversion/report lookup assertions,
8. recovered snapshot and outbox ordering assertions,
9. replacement snapshot round-trip assertions.

The regression now lives in
`tests/unit/test_postgres_repository_mutating_workflow.py`. Its public test is
a short orchestrator over named test-support helpers for seed candidates,
workflow mutation execution, persistence decisions, replay/precheck evidence,
lookup evidence, recovered snapshot assertions, and replacement snapshot
round-trip proof. `tests/unit/test_postgres_repository.py` moved from `1,179`
to `992` lines, and the focused workflow module is `334` lines.

Focused validation passed:

1. `python -m ruff format --check tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py`,
2. `python -m ruff check tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py`,
3. `python -m mypy tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py`,
4. `python -m pytest tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py -q`
   with `19` tests,
5. `make quality-baseline`,
6. `make maintainability-gate`,
7. `make duplicate-implementation-gate` with zero duplicate clusters across
   `3,004` source/script functions.

The same-pattern scan covered
#601/#603/#606/#609/#618/#620/#623/#625/#630/#633/#636/#638/#640/#642
maintainability evidence, current `quality/baseline_report.md`, GitHub
searches for `test_postgres_repository_round_trips_mutating_workflow_details`,
`postgres repository workflow details maintainability`, and
`mutating workflow details quality baseline`, the codebase review ledger, the
issue closure matrix, RFC Slice 19, and issue-discovery ledger `#225`. Closed
issue `#222` owned production row-scoped PostgreSQL writes, not this
test-support decomposition.

This is test-support maintainability only. It does not change production
PostgreSQL adapters, schema, migrations, API/OpenAPI behavior, authentication
or authorization infrastructure, Core, Gateway, Workbench, data-product
support, external-publication authority, runtime topology, wiki source, README,
supported features, or supported-feature promotion.

## 2026-07-19: PostgreSQL Runtime Trust Telemetry Loader Boundary

Issue `#642` applies the Slice 19 report-only quality-baseline lens to the
PostgreSQL runtime trust telemetry projection loader. After issue `#640`,
`make quality-baseline` listed
`src/app/infrastructure/postgres_runtime_trust_telemetry.py::load_runtime_trust_telemetry_summary`
at `120` lines.

The loader mixed:

1. PostgreSQL cursor orchestration and summary query execution,
2. repeated count-map SQL for source authority, freshness, supportability,
   lifecycle, and data-lifecycle states,
3. row decoding/defaulting for source dates, generated-at timestamps, booleans,
   and integers,
4. `RuntimeTrustTelemetryRepositorySummary` DTO assembly.

The public loader now stays as a `7` line orchestrator and delegates to
infrastructure-owned row loading, count-map, DTO-projection, and defaulting
helpers. The SQL comments remain stable so fake PostgreSQL projection tests and
operator evidence can continue to bind query ownership.

This is design modularity inside the existing `lotus-idea` service. It does
not create a telemetry service, change runtime trust telemetry semantics,
certify a data product, change API/OpenAPI behavior, alter migrations, promote
supported features, or prove Gateway/Workbench/client-publication readiness.
README, wiki source, supported features, central context, and central skills
are unchanged by explicit scope decision.

## 2026-07-19: Bond-Maturity Runtime Proof Validator Boundary

Issue `#640` applies the Slice 19 report-only quality-baseline lens to the
Core bond-maturity runtime proof contract. After issue `#638`,
`make quality-baseline` listed
`src/app/application/bond_maturity_runtime_evidence/contract.py::bond_maturity_runtime_execution_is_valid`
at `120` lines.

The validator mixed:

1. top-level proof envelope and source-authority checks,
2. non-proof claim boundary validation,
3. request and source receipt shape validation,
4. Core `PortfolioMaturitySummary:v1` and upstream `HoldingsAsOf:v1`
   product posture checks,
5. horizon, window, temporal, reconciliation, and supportability checks,
6. source hash, digest, request fingerprint, and upstream holdings identity
   checks,
7. maturity fact posture for empty-window versus opportunity-detected outputs,
8. blocker, evidence-ref, and runtime-evidence clearing.

This slice preserves the public
`bond_maturity_runtime_execution_is_valid(payload)` contract while extracting
proof-owned helpers for runtime-execution parts, non-proof claims, request
receipts, source receipts, source scope, source product posture, temporal/window
posture, source hash identity, required source strings, execution closure, and
maturity fact posture. The public validator moved from `120` lines to `13`
lines; every extracted helper is `39` lines or smaller.

Validation:

1. `python -m pytest tests/unit/bond_maturity_runtime_evidence/test_runtime_execution.py tests/unit/bond_maturity_runtime_evidence/test_generator.py -q`
   passed with `69` tests.
2. `python -m ruff check`, `python -m ruff format --check`, and
   `python -m mypy src/app/application/bond_maturity_runtime_evidence/contract.py`
   passed for the touched Python scope.
3. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed; duplicate inventory reported
   `0` duplicate clusters across `2,995` source/script functions.

No-claim decision: this is internal proof-contract modularity only. It does
not implement Core changes, Core issue `sgajbi/lotus-core#792`, live Core
certification, authentication or authorization infrastructure, Gateway,
Workbench, data-mesh certification, external-publication authority, runtime
topology changes, migrations, OpenAPI behavior changes, or supported-feature
promotion. README, wiki, supported-features, OpenAPI, migrations, central
context, and central skills are unchanged by explicit scope decision unless
final validation changes repo-authored truth.

## 2026-07-19: AI Explanation Evaluation API Boundary

Issue `#638` applies the Slice 19 report-only quality-baseline lens to the
AI explanation evaluation route. After issue `#636`, `make quality-baseline`
listed `src/app/api/ai_governance.py::evaluate_ai_explanation` at `120`
lines.

The route mixed:

1. trusted caller-context parsing and capability authorization,
2. idempotency validation,
3. request DTO to application-command mapping,
4. durable repository configuration checks,
5. application use-case execution,
6. exception-to-ProblemDetails mapping and operation-event emission,
7. lineage persistence and response DTO projection.

This slice preserves the public `evaluate_ai_explanation(...)` FastAPI route,
response model, status/error codes, idempotency semantics, entitlement checks,
durable-write fail-closed behavior, Lotus AI provenance and metadata
validation, and operation-event semantics while extracting API-boundary helpers
for caller binding, command construction, durable-write problem mapping,
exception/problem mapping, and success/result response assembly. The public
route moved from `120` lines to `54` lines; the exception dispatcher is `14`
lines and each extracted problem helper is `13` lines or smaller.

Validation:

1. `python -m py_compile src/app/api/ai_governance.py` passed.
2. `python -m pytest tests/unit/test_ai_governance.py tests/unit/test_ai_governance_api_contract.py tests/unit/test_ai_lineage_idempotency.py tests/unit/test_attested_ai_explanation_application.py tests/integration/test_ai_governance_api.py -q`
   passed with `60` tests.
3. `python -m ruff check`, `python -m ruff format --check`, and
   `python -m mypy src/app/api/ai_governance.py` passed for the touched Python
   scope.
4. The focused AI governance plus closure-matrix suite passed with `114`
   tests.
5. `make quality-baseline`, `make maintainability-gate`,
   `make duplicate-implementation-gate`, `make github-issue-closure-matrix-gate`,
   and `make documentation-contract-gate` passed.
6. `make lint` and `make check` passed; the full unit suite reported `4,878`
   passed tests.

No-claim decision: this is internal API-boundary modularity only. It does not
implement authentication or authorization infrastructure, Lotus AI
runtime/provider certification, API/OpenAPI behavior changes, migrations,
runtime topology, Core, Gateway, Workbench, data-mesh certification,
external-publication authority, or supported-feature promotion. README, wiki,
supported-features, OpenAPI, migrations, and central skills are unchanged by
explicit scope decision unless final validation changes repo-authored truth.

## 2026-07-19: Core Portfolio-State Runtime Proof Validator Boundary

Issue `#636` applies the Slice 19 report-only quality-baseline lens to the
Core portfolio-state runtime proof contract. After issue `#633`,
`make quality-baseline` listed
`src/app/application/core_portfolio_state_runtime_evidence/contract.py::core_portfolio_state_runtime_execution_is_valid`
at `121` lines.

The validator mixed:

1. top-level proof envelope and source-authority checks,
2. non-proof claim boundary validation,
3. request and source receipt shape validation,
4. Core `PortfolioStateSnapshot:v1` source scope and product posture checks,
5. temporal currentness and latest-evidence checks,
6. source hash, digest, and receipt identity checks,
7. diagnostic, blocker, evidence-ref, and runtime-evidence clearing.

This slice preserves the public `core_portfolio_state_runtime_execution_is_valid(payload)`
contract while extracting proof-owned helpers for runtime-execution parts,
non-proof claims, request receipts, source receipts, source scope, source
product posture, temporal posture, hash identity, required source strings, and
execution closure. The public validator moved from `121` lines to a `12` line
orchestrator; every extracted helper is `39` lines or smaller.

Validation:

1. `python -m pytest tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py tests/unit/core_portfolio_state_runtime_evidence/test_generator.py -q`
   passed with `56` tests.
2. Ruff check and format-check passed over the touched source and tests.
3. `python -m mypy src/app/application/core_portfolio_state_runtime_evidence/contract.py`
   passed.
4. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed with zero duplicate clusters
   across `2,977` source/script functions.
5. `make github-issue-closure-matrix-gate` and
   `make documentation-contract-gate` passed.

No-claim decision: this is internal proof-contract modularity only. It does
not change Core implementation, Core producer gap `sgajbi/lotus-core#790`,
Core source authority, API/OpenAPI behavior, migrations, runtime topology,
authentication or authorization infrastructure, Gateway, Workbench, data-mesh
certification, external-publication authority, or supported-feature promotion.
README, wiki, supported-features, OpenAPI, migrations, and central skills are
unchanged by explicit scope decision.

## 2026-07-19: Bond-Maturity Core Adapter Source Boundary

Issue `#633` applies the Slice 19 report-only quality-baseline lens to the
Core bond-maturity source adapter. On exact main
`5dd200fe9f385bb27c566fa3ae76bf720249f241`, `make quality-baseline` listed
`src/app/infrastructure/lotus_core_sources.py::fetch_bond_maturity_evidence`
at `126` lines, near the blocking `130` line source-function threshold.

The method mixed:

1. Core maturity-summary HTTP path construction and query execution,
2. entitlement-denied and dependency-unavailable mapping,
3. `PortfolioMaturitySummary:v1` source-ref construction,
4. `HoldingsAsOf:v1` upstream lineage validation,
5. response DTO assembly for maturity window, supportability, hash, freshness,
   policy, and correlation metadata,
6. product-safe bond-maturity diagnostic projection.

This slice preserves the public `fetch_bond_maturity_evidence(request)`
adapter behavior while extracting `_bond_maturity_source_facts(...)` and
`_bond_maturity_evidence(...)`. The public method moved from `126` lines to a
`19` line orchestrator; the extracted helpers are `14` and `73` lines.

Validation:

1. `python -m pytest tests/unit/test_lotus_core_sources.py tests/unit/bond_maturity_runtime_evidence/test_core_adapter.py -q`
   passed with `62` tests.
2. Ruff check and format-check passed over the touched source and tests.
3. `python -m mypy src/app/infrastructure/lotus_core_sources.py` passed.
4. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed with zero duplicate clusters
   across `2,967` functions.
5. `make github-issue-closure-matrix-gate` and
   `make documentation-contract-gate` passed.

No-claim decision: this is internal adapter modularity only. It does not
change Core implementation, Core source authority, source contracts,
API/OpenAPI behavior, migrations, runtime topology, authentication or
authorization infrastructure, Gateway, Workbench, data-mesh certification,
external-publication authority, or supported-feature promotion. README, wiki,
supported-features, OpenAPI, migrations, and central skills are unchanged by
explicit scope decision.

## 2026-07-19: High-Cash Persist API Boundary

Issue `#630` applies the Slice 19 report-only quality-baseline lens to the
high-cash candidate persistence route.

The public `evaluate_and_persist_high_cash_signal(...)` FastAPI route remains
the stable API entry point for caller-supplied high-cash evaluation and
candidate persistence. The implementation now delegates API-boundary decisions
to named private helpers for:

1. candidate-persistence capability validation,
2. idempotency-key validation,
3. Core source-ref contract validation,
4. durable repository readiness and durable-storage posture,
5. request event-lineage parsing,
6. application command execution through the existing use case,
7. idempotency conflict mapping,
8. operation-event outcome emission,
9. final response projection.

This deliberately does not introduce authentication or authorization
infrastructure, a generic signal framework, Core changes, Gateway/Workbench
behavior, or a runtime service split. The route remains an API/controller
orchestrator over the existing application use case and repository port.

Validation and scope decisions:

1. `evaluate_and_persist_high_cash_signal` moved from the report-only `123`
   line hotspot to a `38` line public orchestrator.
2. Existing high-value regression coverage already proves permission denial,
   blank idempotency key rejection, source-contract rejection, durable
   repository fail-closed behavior, replay, duplicate-candidate retry,
   idempotency conflict, blocked/non-candidate no-persistence behavior, event
   lineage, and operation-event outcomes.
3. Local validation passed:
   `python -m ruff check src/app/api/idea_signals.py`,
   `python -m ruff format --check src/app/api/idea_signals.py`,
   `python -m mypy src/app/api/idea_signals.py`,
   `python -m pytest tests/integration/test_high_cash_signal_api.py -q`
   (`36` passed),
   `python -m pytest tests/integration/test_api_operation_events.py -q`
   (`21` passed),
   `python -m pytest tests/integration/outbox/test_event_lineage_api.py -q`
   (`5` passed),
   `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,965` source/script functions.
4. README, wiki, supported-features, OpenAPI, migrations, authn/authz
   infrastructure, Core, Gateway, Workbench, data-mesh certification,
   external-publication authority, and supported-feature truth are unchanged by
   explicit scope decision.
5. PR `#631` merged by rebase to exact-main SHA
   `640dba29a3f592df60381c1875e55bc12b2120bd`. Main Releasability
   `29652436655` and CodeQL `29652431830` passed on that exact SHA. Strict wiki
   publication parity passed with `DiffCount 0`; issue `#630` is closed and the
   implementation branch is absent locally and remotely.

## 2026-07-18: Concentration-Risk Signal Evaluator Boundary

Issue `#625` applies the Slice 19 report-only quality-baseline lens to the
production concentration-risk domain evaluator.

The public `evaluate_concentration_risk_signal(source_input, policy)` contract
remains the only evaluation entry point. The implementation now delegates to
private concentration-risk helpers for:

1. timezone-aware evaluation validation,
2. entitlement and missing Lotus Risk source blockers,
3. source temporal, freshness, and issuer-coverage validation,
4. duplicate suppression and top position / top issuer materiality decisions,
5. deterministic concentration signal, lineage, evidence-packet, candidate,
   and score construction.

This deliberately does not introduce a generic signal framework. The helper
boundary stays capability-owned because concentration risk has its own source
authority, issuer exposure language, materiality semantics, advisor-review
posture, and no-trade/no-rebalance boundary.

Validation and scope decisions:

1. `evaluate_concentration_risk_signal` moved from the report-only `123` line
   hotspot to an `18` line public orchestrator.
2. Existing focused regression coverage in
   `tests/unit/test_concentration_risk_signal_evaluation.py` already proves
   candidate-created, entitlement-denied, missing source, stale source,
   uncertified issuer coverage, below-materiality, duplicate suppression,
   invalid weights, and policy validation paths.
3. Local validation passed:
   `python -m pytest tests/unit/test_concentration_risk_signal_evaluation.py -q`
   (`17` passed),
   `python -m pytest tests/unit/test_github_issue_closure_matrix_gate.py -q`
   (`42` passed), Ruff check/format-check over touched Python files,
   `make quality-baseline`, `make maintainability-gate`,
   `make duplicate-implementation-gate`, `make lint`, and `make check`
   (`4,864` unit tests).
4. README, wiki, supported-features, OpenAPI, migrations, authn/authz, Core,
   Gateway, Workbench, data-mesh certification, external-publication authority,
   and supported-feature truth are unchanged by explicit scope decision.

## 2026-07-18: AI Workflow-Pack Fixture Boundary

Issue `#623` applies the Slice 19 report-only quality-baseline lens to
`tests/support/ai_workflow_pack_fixture.py`.

The public `write_lotus_ai_workflow_pack_fixture()` and
`write_lotus_ai_workflow_pack_runtime_execution_fixture()` helpers remain the
stable entry points for Idea's Lotus AI source-contract and runtime-execution
proof tests. They no longer inline-build every fake Lotus AI file. Base
source-contract fixture files and runtime-execution fixture files now live in
capability-owned module-level catalogs, with one shared writer loop preserving
the generated tree.

This is test-support maintainability only. It does not change runtime
behavior, API/OpenAPI contracts, persistence, migrations,
authentication/authorization, Core, Gateway, Workbench, Lotus AI
runtime/provider certification, external-publication authority, data-mesh
certification, or supported-feature promotion.

Evidence:

1. `write_lotus_ai_workflow_pack_fixture` and
   `write_lotus_ai_workflow_pack_runtime_execution_fixture` dropped out of the
   report-only largest-function list after `make quality-baseline`.
2. `tests/unit/test_ai_workflow_pack_fixture.py` covers critical
   source-contract files, runtime-execution files, and no-claim boundaries for
   external-publication authority, downstream authority, live provider, and
   supported-feature promotion.
3. Focused validation passed:
   `python -m pytest tests/unit/test_ai_workflow_pack_fixture.py tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py -q`
   (`48` tests), Ruff check and format-check over touched files,
   `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate`.
4. PR `#624` merged by rebase to exact-main SHA
   `79a319c37624d62dacd35b516924521c8ddabb06`; exact-main Main Releasability
   `29648568930` and CodeQL `29648566676` passed.

## 2026-07-18: PostgreSQL Fake Row Builder Boundary

Issue `#620` applies the follow-through Slice 19 test-support hardening from
issue `#618` to `tests/unit/postgres_repository_mutation_fake_helpers.py`.

The public `row_for_insert()` helper remains the single insertion entry point
used by the PostgreSQL fake, but it no longer owns every table's fake row
shape inline. It unwraps JSONB values once and delegates to table-owned row
builders for candidate records, idempotency, lifecycle history, audit events,
outbox events, review decisions, feedback, conversion intent/outcome, report
evidence-pack requests, downstream submissions, and AI explanation lineage.

This is test-support maintainability only. It does not change the production
PostgreSQL adapter, database schema, migrations, API/OpenAPI behavior,
authentication/authorization, Core, Gateway, Workbench, runtime certification,
or supported-feature promotion.

Evidence:

1. `row_for_insert` dropped out of the report-only largest-function list after
   `make quality-baseline`.
2. `tests/unit/test_postgres_repository_mutation_fake_helpers.py` covers
   representative candidate-row JSONB unwrapping, downstream-submission row
   shape, unknown-table failure, and column/value mismatch failure.
3. Affected suites passed:
   `tests/unit/test_postgres_repository_mutation_fake_helpers.py`,
   `tests/unit/test_postgres_repository.py`,
   `tests/unit/test_postgres_downstream_submission.py`,
   `tests/unit/outbox/test_postgres_delivery_adapter.py`, and
   `tests/integration/test_postgres_runtime_integration.py` (`45` passed,
   `9` skipped).
4. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed locally.

## 2026-07-18: PostgreSQL Fake SQL Dispatcher Boundary

Issue `#618` reduces the remaining report-only test-support hotspot in
`tests/unit/postgres_repository_fake.py::FakePostgresCursor.execute`.

The fake cursor remains a single in-process test double for the PostgreSQL
repository, but its public `execute()` method now delegates to named
SQL-family handlers for review queues, readiness summaries, runtime trust
telemetry, lookups, review identity, outbox events, candidate updates, generic
selects, deletes, inserts, and idempotency inserts. Existing capability-owned
helpers continue to own bounded mutation, downstream submission, outbox
recovery, runtime trust telemetry row building, review queue rows, and lookup
rows.

This is test-support maintainability only. It does not change the production
PostgreSQL adapter, database schema, migrations, API/OpenAPI behavior,
authentication/authorization, Core, Gateway, Workbench, runtime certification,
or supported-feature promotion.

Evidence:

1. `FakePostgresCursor.execute` dropped out of the report-only largest-function
   list after `make quality-baseline`.
2. `tests/unit/test_postgres_repository_fake_dispatch.py` covers generic
   insert/select/delete write tracking and downstream readiness quarantine
   behavior.
3. Affected suites passed:
   `tests/unit/test_postgres_repository_fake_dispatch.py`,
   `tests/unit/test_postgres_repository.py`,
   `tests/unit/test_postgres_downstream_readiness.py`,
   `tests/unit/runtime_trust_telemetry/test_postgres_projection.py`, and
   `tests/unit/test_postgres_review_queue.py` (`35` tests).
4. `make quality-baseline`, `make maintainability-gate`,
   `make duplicate-implementation-gate`, `make lint`, and `make typecheck`
   passed locally.

## 2026-07-18: PostgreSQL Snapshot Write Boundary

Issue `#612` extracts PostgreSQL snapshot replacement and detail-write helpers
from `src/app/infrastructure/postgres_repository.py` into
`src/app/infrastructure/postgres_snapshot_writes.py`.

The public `PostgresIdeaRepository` API and durable behavior remain unchanged.
The new `PostgresSnapshotWriteRepositoryMixin` owns candidate snapshot inserts,
snapshot idempotency inserts, downstream submission inserts, lifecycle/audit
detail inserts, review/feedback identity-conflict inserts, conversion intent
and outcome detail inserts, report evidence-pack inserts, and AI explanation
lineage detail insertion used during snapshot replacement.

This is design modularity inside the existing Lotus Idea PostgreSQL adapter. It
does not change schema, migrations, source-authority contracts, API/OpenAPI
shape, runtime topology, authentication/authorization, Core, Gateway,
Workbench, or supported-feature promotion.

Evidence:

1. `src/app/infrastructure/postgres_repository.py` moved from `1,186` lines to
   `866` lines.
2. `src/app/infrastructure/postgres_snapshot_writes.py` is a focused `358` line
   PostgreSQL write helper module.
3. Targeted validation passed: Ruff and MyPy over the changed infrastructure
   modules; `make test-unit UNIT_TESTS=tests/unit/test_postgres_repository.py`
   (`19` passed); `make maintainability-gate`; and
   `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,952` functions.

## 2026-07-18: Mandate-Health Signal Evaluation Boundary

`src/app/domain/signal_evaluation.py::evaluate_mandate_health_signal` became
the next production-code source hotspot after #606 closed. Issue `#609`
applies the same Slice 19 maintainability pattern to the allocation-drift
domain signal without changing source authority, Manage/Risk/Performance
ownership, API/OpenAPI shape, migrations, runtime topology, Gateway/Workbench,
authentication/authorization, or supported-feature promotion.

The public evaluator keeps its signature and behavior while delegating to
explicit domain helpers:

1. `_validate_mandate_health_evaluation_time` for timezone-aware evaluation
   preconditions,
2. `_mandate_health_pre_source_block` for entitlement and mandatory
   action-register source blockers,
3. `_mandate_health_source_block` for temporal, freshness, portfolio-scope, and
   Manage supportability blockers,
4. `_mandate_health_materiality_result` for duplicate, count, and threshold
   decisions,
5. `_mandate_health_candidate_created_result` for stable identity, signal,
   lineage, evidence packet, candidate, and final result assembly.

`evaluate_mandate_health_signal` moved from `127` lines to `15` lines; the
candidate-created helper is `52` lines. Focused mandate-health unit,
application, and allocation-drift API integration tests preserve blocker,
not-eligible, suppressed, and candidate-created behavior.

## 2026-07-18: Review-Action API Boundary

`src/app/api/review_workflow.py::record_review_action` was the next source
hotspot left by the #603 same-pattern scan at `127` lines on exact main
`f357d263fb95c3b2ab08462844b54a0ec711b71b`. Issue `#606` applies the same
API-boundary lens to the human-governance review route without widening scope
into authentication, authorization, Workbench, Gateway, or supported-feature
promotion.

The route keeps its public signature, OpenAPI metadata, response schema,
idempotency lineage, entitlement semantics, operation events, persistence
problem mapping, and `supportedFeaturePromoted=false` posture while delegating
to explicit API-boundary helpers:

1. `_review_action_mutation_context` for trusted caller and repository
   mutation context construction,
2. `_apply_review_action_request` for domain command construction and
   application execution,
3. `_review_action_permission_problem` for permission and entitlement failure
   mapping,
4. `_review_action_state_problem` and `_review_action_state_attributes` for
   state-conflict telemetry and problem details,
5. `_review_action_invalid_request_problem` for request validation failure
   mapping,
6. `_review_action_response` for persistence problem and success response
   assembly.

This is design modularity inside the existing Lotus Idea API process. It does
not implement identity provider integration, authenticated sessions,
token-claims, Gateway/Workbench behavior, schema changes, data migration,
runtime topology changes, or supported-feature promotion.

## 2026-07-18: Outbox Delivery Run-Once API Boundary

`src/app/api/outbox/delivery.py::post_outbox_delivery_run_once` appeared in
the report-only quality baseline at `129` lines, one line below the blocking
source-function maintainability threshold. Issue `#603` applies the same
operability and architecture-boundary lens learned from issue `#601`: an
operator-facing run-once route should not mix caller parsing, authorization,
idempotency, durable-write gating, capacity posture, publisher configuration,
execution observation, response mapping, and no-promotion posture in one
near-limit function.

The route keeps its public signature, OpenAPI contract, response schema,
operation events, idempotency replay/conflict behavior, publisher cleanup,
durable-write fail-closed posture, and `supportedFeaturePromoted=false`
semantics while delegating to explicit API-boundary helpers:

1. `_outbox_delivery_run_caller` for trusted caller construction,
2. `_outbox_delivery_run_permission_problem` for product-safe authorization
   failure mapping,
3. `_outbox_delivery_run_context` for idempotency validation, operator run
   reference, repository, and durable-storage posture,
4. `_outbox_delivery_run_precondition_problem` for durable-write, capacity, and
   UTC delivery-time blockers,
5. `_outbox_delivery_run_publisher_or_block` for fail-closed broker
   configuration posture,
6. `_outbox_delivery_run_response` for conflict/replay/accepted response and
   operation-event mapping.

This is design modularity inside the existing Lotus Idea API process. It does
not certify external broker runtime, downstream consumer execution,
platform-mesh event publication, Gateway/Workbench support, data-product
support, external-publication authority, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/outbox/delivery.py`.
2. Tests and gates: Ruff and MyPy over `src/app/api/outbox/delivery.py`,
   `make test-unit UNIT_TESTS=tests/unit/outbox/test_outbox_delivery.py`
   (`16` passed),
   `make test-integration INTEGRATION_TESTS=tests/integration/outbox/test_delivery_readiness_api.py`
   (`16` passed), `make maintainability-gate`,
   `make duplicate-implementation-gate`, and `make quality-baseline`.
3. Maintainability impact: `post_outbox_delivery_run_once` moved from `129` to
   `71` lines and left the report-only top-function list; no duplicate
   implementation clusters were introduced.
4. Documentation/context decision: RFC Slice 19, the codebase review ledger,
   issue closure matrix, repository context, and this decision log were
   updated. README, wiki, supported-features, OpenAPI, migrations, runtime
   topology, and central skills are unchanged because public behavior and
   operating commands did not change.

## 2026-07-18: Service-Capacity Baseline Builder Boundary

`src/app/application/service_capacity_baseline.py::build_service_capacity_baseline`
was at the blocking source-function maintainability threshold in the
report-only quality baseline. The builder is a high-consequence
production-readiness proof path, so future Slice 19 capacity hardening should
not add validation, qualification, or artifact fields into one near-limit
function.

The builder now keeps its public signature and artifact schema but delegates to
explicit internal boundaries:

1. `_validate_capacity_baseline_request` for request-level invariants,
2. `_scenario_summaries` for governed scenario aggregation,
3. `_capacity_evidence_qualifications` for protected PostgreSQL,
   dependency-recovery, load/soak, resource, and cost qualification,
4. `CapacityEvidenceQualificationSet` for derived certification-blocker state,
5. `_capacity_baseline_artifact` for source-safe artifact assembly.

This is design modularity inside the existing Lotus Idea deployable. It does
not execute a live load/soak run, certify capacity, certify cost attribution,
change API behavior, change migrations, prove Gateway/Workbench behavior,
promote a data product, or promote a supported feature.

Evidence:

1. Code: `src/app/application/service_capacity_baseline.py`.
2. Tests and gates:
   `make test-unit UNIT_TESTS=tests/unit/test_service_capacity_baseline.py`
   (`34` passed), `make service-capacity-baseline-contract-gate`,
   `make maintainability-gate`, `make duplicate-implementation-gate`, and
   `make quality-baseline`.
3. Maintainability impact: `build_service_capacity_baseline` moved from
   `130` lines to `64` lines and no longer appears in the report-only
   top-function list; no duplicate implementation clusters were introduced.
4. Documentation/context decision: RFC Slice 19, the codebase review ledger,
   issue closure matrix, and this decision log were updated. README, wiki,
   supported-features, OpenAPI, migrations, runtime topology, and central
   skills are unchanged because public behavior and operating commands did not
   change.

## 2026-07-16: Typed Advise Source-Product Evidence Boundary

The mandate/restriction and missing-risk-profile typed source-product proofs
now share a capability-owned application and automation package. Stable
operator environment variables and Make targets remain, but retired flat v1
modules, scripts, and tests are prohibited.

The shared module owns only source-authority loading, digest binding, closed
field validation, and authority-denial mechanics. Independent profiles retain
diagnostic vocabulary, blocker effects, evidence refs, and non-proof
boundaries. The aggregate proof artifact registry maps every CLI input to its
application arguments, evidence class, blocker effect, tracking issue, and
classification status; documentation validation rejects drift.

This is design modularity inside the existing Lotus Idea deployable. It does
not add an API, database, migration, worker, service, deployment boundary, or
supported feature. Advise retains risk-profile, suitability, policy, proposal,
mandate, and restriction authority. Issue `#508` tracks scheduled-worker
deployment evidence separately because static topology declarations are not a
deployment receipt.

## 2026-07-16: Performance Benchmark-Readiness Evidence Boundary

Performance benchmark-readiness proof generation now uses one named
source-preserving application use case and capability-owned closed v2 runtime
evidence. The source port preserves the exact `ReturnsSeriesBundle:v1`
response identity needed for audit and replay: product/route/time, response
portfolio, calculation and input hashes, benchmark context, coverage,
freshness/quality, and producer correlation/trace.

The runtime contract pseudonymizes consumer scope and cross-binds request,
source, benchmark-context, and deterministic review-required or
no-opportunity receipts. It rejects blocked source execution, malformed or
contradictory context, unknown fields, raw identifiers, stale/future evidence,
scope/time/hash/count drift, diagnostic drift, and recomputed-digest semantic
tampering. Flat v1 implementation, generator, gate, and test paths are removed
and prohibited while the stable environment variable, CLI argument, output
filename, and Make target remain.

This is design modularity inside the existing `lotus-idea` deployable. A
separate runtime service would add network, deployment, support, and failure
surface without workload, scaling, ownership, or isolation evidence. No API,
OpenAPI, persistence, database, migration, or supported-feature change is
introduced. Lotus Performance retains official performance and benchmark
context authority; Lotus Core retains benchmark assignment authority.

Evidence:

1. Code: `src/app/application/performance_benchmark_readiness.py`,
   `src/app/application/performance_benchmark_readiness_runtime_evidence/`,
   `src/app/domain/performance_benchmark_readiness.py`, and the Performance
   port/adapter.
2. Tests: `tests/unit/test_performance_benchmark_readiness.py`,
   `tests/unit/performance_benchmark_readiness_runtime_evidence/`, aggregate
   readiness, archetype, adapter, and canonical-runner suites.
3. Gates: `make missing-benchmark-performance-readiness-proof-contract-gate`,
   `make opportunity-archetype-contract-gate`, and `make ci-contract-gate`.
4. Guidance decision: repository context and operator/wiki truth changed and
   are updated. Existing platform skills already require source-preserving
   one-fetch receipts, semantic tamper checks, capability-owned organization,
   same-pattern scans, and design-versus-runtime modularity, so no skill or
   central-context change is required.

## 2026-07-04: Review Workflow API Operation Boundary

The review-action and feedback API routes now share
`src/app/api/review_workflow_operations.py` for caller-header parsing, mutating
review capability checks, body authorized-scope subset validation, idempotency
validation, durable-write blocking, product-safe persistence problem mapping,
and operation-event mapping.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, a queue boundary,
or independent scaling. The runtime split remains unjustified until workload,
failure-isolation, ownership, or operability evidence shows that a separate
boundary would reduce total system risk.

Evidence:

1. Code: `src/app/api/review_workflow.py`,
   `src/app/api/review_workflow_operations.py`.
2. Tests: `tests/unit/test_review_workflow_api_operations.py` plus existing
   review workflow API and application tests.
3. Gates: run focused unit/integration tests, `make maintainability-gate`,
   `make architecture-boundary-gate`, and `make duplicate-implementation-gate`
   before committing the slice.

## 2026-07-04: Conversion Governance API Operation Boundary

The conversion-intent and conversion-outcome API routes now share
`src/app/api/conversion_governance_operations.py` for caller-header parsing,
mutating conversion capability checks, idempotency validation, durable-write
blocking, product-safe persistence problem mapping, and operation-event
mapping.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary, or
independent scaling. Conversion intent/outcome posture stays in the same API
process because it shares repository, audit, idempotency, and operation-event
ownership with the existing opportunity lifecycle.

Private-banking boundary preserved:

1. Conversion intent remains local and review-gated.
2. Conversion outcome records downstream source posture only.
3. The routes still do not grant execution, suitability, compliance,
   rebalance, report-render, archive, or client-communication authority.

Evidence:

1. Code: `src/app/api/conversion_governance.py`,
   `src/app/api/conversion_governance_operations.py`.
2. Tests: `tests/unit/test_conversion_governance_api_operations.py` plus
   existing conversion domain and review workflow API integration tests.
3. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_api_error_mappings.py tests\unit\test_conversion_governance_api_operations.py tests\unit\test_review_workflow_api_operations.py tests\unit\test_conversion_governance.py tests\integration\test_review_workflow_api.py -q`
   (`49 passed`).
4. Aggregate validation passed: `make lint`, `make typecheck`,
   `make duplicate-implementation-gate`, and `make test-unit` (`2376 passed`).
5. Documentation/context decision: README, repository context, quality
   scorecard, review ledger, refactor decision log, and wiki source were
   updated. No supported-feature promotion or seed/automation change is
   justified by this internal modularity slice. No platform skill update is
   required because the existing backend-delivery and codebase-review skills
   already require design-vs-runtime modularity, same-pattern scans, and
   evidence-backed ledger entries.

## 2026-07-04: Domain Persistence Model Boundary

Immutable persistence decisions, records, results, lifecycle history, and
repository snapshots now live in `src/app/domain/persistence_models.py`.
`src/app/domain/persistence.py` imports and re-exports those types while keeping
`InMemoryIdeaRepository` behavior and existing public imports stable.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary,
worker boundary, or independent scaling. Persistence model contracts and
repository behavior share the same domain-service ownership until workload,
failure-isolation, ownership, or operability evidence justifies a runtime split.

Private-banking boundary preserved:

1. The repository still stores idea candidates, evidence replay, idempotency,
   lifecycle, review, feedback, conversion, report evidence-pack, AI lineage,
   outbox, and downstream submission posture.
2. No portfolio accounting, official performance, risk, suitability,
   compliance, rebalance execution, report rendering, archive authority, or AI
   infrastructure authority moves into lotus-idea.

Evidence:

1. Code: `src/app/domain/persistence.py`,
   `src/app/domain/persistence_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_postgres_repository.py tests\unit\test_repository_port_boundary.py tests\unit\test_domain_validation.py -q`
   (`46 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/domain/persistence.py` moved from 1185 to
   1004 lines; `src/app/domain/persistence_models.py` is 215 lines.

## 2026-07-04: Signal Evaluation Model Boundary

Immutable signal-family inputs, policies, outcomes, and result contracts now
live in `src/app/domain/signal_evaluation_models.py`.
`src/app/domain/signal_evaluation.py` imports and re-exports those types while
keeping deterministic evaluator algorithms and existing public imports stable.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary,
worker boundary, or independently scalable evaluator. Signal evaluation remains
local because lotus-idea consumes caller/source-owned evidence, produces local
candidate posture, and has no workload, failure-isolation, ownership, or
operability evidence for a runtime split.

Private-banking boundary preserved:

1. Signal policies consume source-owned posture and deterministic thresholds.
2. No portfolio accounting, official performance, risk, benchmark assignment,
   suitability, compliance, rebalance execution, report rendering, archive
   authority, or AI infrastructure authority moves into lotus-idea.
3. Source-authority validation and caller entitlement checks remain enforced by
   the API/application boundary before candidate creation.

Evidence:

1. Code: `src/app/domain/signal_evaluation.py`,
   `src/app/domain/signal_evaluation_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_signal_evaluation.py tests\unit\test_concentration_risk_signal_evaluation.py tests\unit\test_underperformance_signal_evaluation.py tests\unit\test_mandate_health_signal_evaluation.py tests\unit\test_high_volatility_signal_evaluation.py tests\unit\test_drawdown_review_signal_evaluation.py tests\unit\test_api_signal_models.py -q`
   (`90 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/domain/signal_evaluation.py` moved from
   1113 to 954 lines; `src/app/domain/signal_evaluation_models.py` is 230
   lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   supported-feature promotion or seed/automation change is justified by this
   internal modularity slice.

## 2026-07-04: AI Governance API Model Boundary

AI explanation request and response DTOs now live in
`src/app/api/ai_governance_models.py`. `src/app/api/ai_governance.py` imports
and re-exports those DTOs while keeping authorization, idempotency,
durable-write checks, route metadata, operation events, and response handling
in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate AI governance service,
queue boundary, worker boundary, or independently scalable AI execution path.
AI explanation governance remains local because lotus-idea evaluates
deterministic evidence and fallback posture for persisted idea candidates; it
does not execute AI runtime workflows.

Private-banking and AI boundaries preserved:

1. The route still requires explicit AI explanation capabilities and
   `Idempotency-Key` for mutation.
2. The route still does not call AI providers, own prompts/provider payloads,
   execute lotus-ai runtime workflows, grant downstream authority, or promote a
   supported feature.
3. Source-authority, entitlement, model-risk, audit, and human-review posture
   remain enforced by the existing API/application/domain contracts.

Evidence:

1. Code: `src/app/api/ai_governance.py`,
   `src/app/api/ai_governance_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_ai_governance.py tests\unit\test_ai_governance_api_contract.py tests\unit\test_ai_explanation_readiness.py -q`
   (`23 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/ai_governance.py` moved from 955 to
   567 lines; `src/app/api/ai_governance_models.py` is 444 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   supported-feature promotion or seed/automation change is justified by this
   internal modularity slice.

## 2026-07-04: Outbox Delivery API Model Boundary

Outbox delivery readiness, status-count, and run-once response DTOs now live in
`src/app/api/outbox/delivery_models.py`.
`src/app/api/outbox/delivery.py` imports those DTOs while keeping
caller authorization, idempotency validation, durable-write blocking, publisher
cleanup, operation-event emission, route metadata, and response handling in the
existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate outbox delivery service,
queue boundary, worker boundary, or independently scalable broker-publication
path. Outbox delivery run-once remains an internal operator foundation because
there is no workload, failure-isolation, ownership, security, or operability
evidence for a runtime split.

Private-banking and operating boundaries preserved:

1. The route still requires operator caller context plus
   `idea.outbox-delivery.*` capabilities.
2. The route still requires `Idempotency-Key` for mutation, uses the configured
   repository and publisher adapter, returns aggregate counts only, and emits
   source-safe operation events.
3. The route still does not certify live broker publication, downstream
   consumer runtime, platform-mesh event runtime publication, Gateway/Workbench support,
   data-product certification, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/outbox/delivery.py`,
   `src/app/api/outbox/delivery_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_outbox_delivery_readiness_api.py tests\unit\test_outbox_delivery_readiness.py -q`
   (`19 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/outbox/delivery.py` moved
   from 625 to 494 lines; `src/app/api/outbox/delivery_models.py`
   is 145 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-08-11: Implementation-Proof Readiness Artifact Wiring

Issue #929 refactors the API-layer configured-artifact mapping for
`/api/v1/implementation-proof/readiness`. The route now builds the
application-owned `ImplementationProofReadinessProofInputs` aggregate through
named source-authority helper groups instead of passing a broad legacy keyword
fan-out into the readiness builder.

Evidence:

1. `_build_readiness_snapshot_from_configured_artifacts(...)` moved from 108
   lines to 13 lines.
2. Largest new helper is 47 lines; helpers are grouped by source ingestion,
   repository/runtime/AI, downstream owner, Workbench/Gateway, and Core source
   evidence.
3. Focused validation passed: Ruff, format check, MyPy, and
   `tests/integration/test_implementation_proof_readiness_api.py` (`8 passed`),
   plus maintainability, duplicate implementation, and quality-baseline gates.
4. PR #930 merged by rebase to exact-main SHA
   `35f302e53be2178640bdbac6ae11b9643e1193d6`; exact-main Main
   Releasability `31497468739` and exact-main Push/CodeQL `31497459747`
   passed.
5. No wiki, README, supported-feature, OpenAPI, migration, runtime topology,
   skill, or central context change is justified; this is internal API
   maintainability only.

## Aggregate Persistence Mutation Boundary

Candidate ingestion first exposed the generic whole-repository snapshot cost.
The same-pattern fix now covers lifecycle, review, feedback, conversion, report
evidence, AI lineage, outbox run idempotency, evidence replay, and report
precheck. Aggregate snapshot composition, PostgreSQL mutation orchestration,
and replay projections are separate internal modules with stable interfaces.

Identity, sorted candidate, and idempotency locks fence exact state before the
unchanged domain decision and atomic row delta. Full snapshots remain explicit
administrative/test/DR operations. Query-shape tests and all 17 disposable
PostgreSQL 18 tests pass. This is design and data-access modularity inside one
deployable and one Idea-owned database; it creates no database-per-module,
microservice, schema, API, migration, source-authority, or supported-feature
boundary.

PR `#365` merged the bounded mutation family to main SHA `69326064`; Main
Releasability `29239140276`, CodeQL `29239134509`, and wiki publication
`8386705` provide exact merged-main closure evidence.

## 2026-07-13: Outbox Capability Packages Inside Existing Layers

Outbox ownership now uses an `outbox/` package inside each applicable runtime
layer and support area. The migration covers API routes/DTOs, application use
cases and proof evaluators, domain event/lineage/delivery/recovery policy, the
publisher port, PostgreSQL and HTTP adapters, runtime composition,
observability, operator scripts, and focused tests.

This is design modularity inside the existing `lotus-idea` deployable. API and
optional worker roles still use one Idea-owned PostgreSQL boundary. Folder
cohesion does not justify another service, broker ownership, or independently
scalable process.

Decisions:

1. Internal consumers use explicit capability paths; stable public domain
   exports remain available through `app.domain` without legacy module aliases.
2. Event lineage, in-memory writes, PostgreSQL fake behavior, and event-lineage
   integration proof move with the outbox capability. Aggregate
   implementation-proof consumers remain with their actual owning capability.
3. Direct scripts share `scripts/outbox/_bootstrap.py` so package and Windows
   direct execution resolve the repository consistently.
4. Repository hygiene requires canonical package paths and rejects every
   retired flat path. It does not impose directory-size limits.
5. Supported features, seed data, runtime topology, and external broker,
   consumer, and platform-mesh certification remain unchanged.

Validation evidence:

1. Focused outbox, domain, integration, and hygiene suite: `293 passed`, one
   environment-dependent PostgreSQL skip.
2. Ruff, focused MyPy, architecture, private-import, maintainability,
   duplicate-implementation, repository-hygiene, and all seven outbox contract
   gates pass.
3. Final `make ci`: MyPy over 739 files; 3,567 unit tests; 430 integration
   tests passed with 19 environment-dependent skips; 4 E2E tests; 99.02%
   coverage over 23,779 statements; no known dependency vulnerabilities.
4. Disposable PostgreSQL 18: all 16 required persistence, recovery, queue,
   downstream, and lifecycle tests passed.
5. A clean isolated wheel contains and imports the canonical package paths with
   no retired modules. SHA-tagged Docker build, container package imports,
   health/version smoke, and OCI label inspection passed.

## 2026-07-04: Review Workflow API Model Boundary

Review-action and feedback request/response DTOs now live in
`src/app/api/review_workflow_models.py`.
`src/app/api/review_workflow.py` imports and explicitly re-exports those DTOs
while keeping caller checks, entitlement-scope validation, idempotency,
review workflow persistence, operation-event emission, route metadata, and
response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate review service, worker
boundary, compliance approval runtime, or independently scalable human-review
runtime. Review workflow remains an internal human-review foundation.

Private-banking and authority boundaries preserved:

1. The route still requires explicit review/feedback capabilities, actor role,
   trusted entitlement-scope subset validation, and `Idempotency-Key`.
2. The route still records idea review and feedback posture only; it does not
   approve suitability, compliance, mandates, execution, reporting, or client
   communication.
3. The route still does not certify Gateway/Workbench support, data-product
   publication, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/review_workflow.py`,
   `src/app/api/review_workflow_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_review_workflow_api_operations.py tests\unit\test_api_request_validation.py tests\integration\test_api_operation_events.py -q`
   (`26 passed`), plus targeted ruff and mypy over the changed modules.
3. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Conversion Governance API Model Boundary

Conversion-intent and conversion-outcome request/response DTOs now live in
`src/app/api/conversion_governance_models.py`.
`src/app/api/conversion_governance.py` imports those DTOs while keeping caller
checks, idempotency validation, conversion workflow persistence, operation-event
emission, route metadata, and response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate conversion service, worker
boundary, downstream execution boundary, report materialization boundary, or
independently scalable conversion runtime. Conversion governance remains an
internal lifecycle-intent/outcome foundation.

Private-banking and authority boundaries preserved:

1. The route still requires explicit conversion capabilities and
   `Idempotency-Key` for mutations.
2. The route still records only governed conversion intent/outcome posture; it
   does not grant Advise, Manage, Report, suitability, execution, render,
   archive, or client-communication authority.
3. The route still does not certify downstream execution, Gateway/Workbench
   support, data-product publication, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/conversion_governance.py`,
   `src/app/api/conversion_governance_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_conversion_governance.py tests\unit\test_conversion_governance_api_operations.py tests\unit\test_api_request_validation.py tests\integration\test_api_operation_events.py -q`
   (`37 passed`), plus targeted ruff and mypy over the changed modules.
3. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Idea Signal API Model Boundary

High-cash and mandate-restriction request/response DTOs now live in
`src/app/api/idea_signal_models.py`.
`src/app/api/idea_signals.py` imports those DTOs while keeping caller checks,
source-ref authority validation, candidate persistence orchestration,
operation-event emission, route metadata, and response handling in the
existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate idea-signal service,
worker boundary, source-ingestion runtime, or independently scalable signal
evaluation path. The endpoints remain bounded API foundations that consume
caller-supplied, source-owned evidence.

Private-banking and source-authority boundaries preserved:

1. The route still requires explicit caller capabilities and validates
   source-ref contracts against owning source authorities.
2. The route still does not calculate official portfolio cash, holdings,
   suitability, risk, performance, execution, or report facts.
3. The route still does not certify live source ingestion, Gateway/Workbench
   support, client publication, or supported-feature promotion.

Test-harness learning:

1. API operation-event tests now patch review/conversion helper emitter aliases
   after route/helper extraction so integration tests follow the real operation
   boundary instead of stale route-local emitter names.

Evidence:

1. Code: `src/app/api/idea_signals.py`,
   `src/app/api/idea_signal_models.py`,
   `tests/integration/test_api_operation_events.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_api_operation_events.py tests\unit\test_api_signal_models.py -q`
   (`24 passed`), plus targeted ruff and mypy over the changed modules.
3. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Runtime Trust Telemetry API Model Boundary

Runtime trust telemetry preview, product posture, snapshot, freshness, lineage,
blocking, and evidence response DTOs now live in
`src/app/api/runtime_trust_telemetry_models.py`.
`src/app/api/runtime_trust_telemetry.py` imports those DTOs while keeping
operator caller checks, timezone query validation, aggregate preview/snapshot
construction, operation-event emission, route metadata, and response handling
in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate telemetry service, worker
boundary, data-product certification process, or independently scalable mesh
publication path. Runtime trust telemetry remains an internal operator and
data-mesh readiness surface because there is no workload, failure-isolation,
ownership, security, or operability evidence for a runtime split.

Private-banking and data-mesh boundaries preserved:

1. The route still requires operator caller context plus
   `idea.mesh.trust-telemetry.*` capabilities.
2. The route still returns source-safe aggregate posture and contract-shaped
   telemetry without candidate identifiers, source routes, portfolio/account
   holdings, client identifiers, or official performance/risk facts.
3. The route still does not certify data products, platform mesh, live source
   ingestion, Gateway/Workbench support, client publication, or
   supported-feature promotion.

Evidence:

1. Code: `src/app/api/runtime_trust_telemetry.py`,
   `src/app/api/runtime_trust_telemetry_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_runtime_trust_telemetry_api.py tests\unit\test_runtime_trust_telemetry.py -q`
   (`16 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/runtime_trust_telemetry.py` moved
   from 584 to 416 lines; `src/app/api/runtime_trust_telemetry_models.py` is
   187 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Candidate Detail API Model Boundary

Source-safe candidate-detail response DTOs now live in
`src/app/api/candidate_detail_models.py`. `src/app/api/candidate_detail.py`
imports and explicitly re-exports those DTOs while keeping caller authorization,
entitlement-scope filtering, candidate lookup, operation-event emission, route
metadata, and product-safe response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate candidate-detail service,
Gateway boundary, Workbench boundary, data-product publication path, or
independently scalable read model. Candidate detail remains a bounded internal
read-only API foundation.

Private-banking and source-safety boundaries preserved:

1. The route still requires explicit `idea.candidate.detail.read` capability and
   caller entitlement scope is applied fail-closed before returning detail.
2. The response model still redacts source routes and source content hashes from
   source refs while exposing source authority, product id, version, as-of date,
   generated-at timestamp, data-quality status, and freshness posture.
3. The route still does not provide portfolio accounting, official risk or
   performance facts, suitability/compliance approval, execution authority,
   report rendering/archive authority, client communication, Workbench product
   proof, data-product certification, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/candidate_detail.py`,
   `src/app/api/candidate_detail_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_candidate_detail_models.py tests\unit\test_candidate_detail_application.py tests\integration\test_candidate_detail_api.py tests\integration\test_api_operation_events.py::test_candidate_detail_api_emits_bounded_operation_event -q`
   (`12 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/candidate_detail.py` moved from 624 to
   289 lines; `src/app/api/candidate_detail_models.py` is 349 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Source-Ingestion Readiness API Model Boundary

Source-ingestion readiness and aggregate run-once response DTOs now live in
`src/app/api/source_ingestion_readiness_models.py`.
`src/app/api/source_ingestion_readiness.py` imports and explicitly re-exports
those DTOs while keeping operator caller authorization, durable-repository
gating, runtime composition, Core runtime cleanup, operation-event emission,
route metadata, and product-safe response handling in the existing route
module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate source-ingestion service,
new worker boundary, data-product publication path, Gateway/Workbench product
surface, or independently scalable ingestion runtime. Source ingestion remains
a bounded internal operator proof foundation until workload,
failure-isolation, ownership, security, or operability evidence justifies a
runtime split.

Private-banking, source-authority, and modernization boundaries preserved:

1. The routes still require operator caller context with explicit
   `idea.source-ingestion.*` capabilities.
2. The run-once response still returns aggregate decision counts only and does
   not expose portfolio identifiers, candidate identifiers, idempotency keys,
   raw Core payloads, source routes, or source content hashes.
3. The routes still do not certify live Core source ingestion, data-product
   readiness, Gateway/Workbench support, client publication, downstream
   execution, or supported-feature promotion.
4. The slice does not add compatibility shims, legacy route aliases, or new
   runtime process boundaries; it reduces design-time complexity inside the
   current module boundary.

Evidence:

1. Code: `src/app/api/source_ingestion_readiness.py`,
   `src/app/api/source_ingestion_readiness_models.py`,
   `tests/unit/test_source_ingestion_readiness_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_readiness_models.py tests\unit\test_source_ingestion_readiness.py tests\integration\test_source_ingestion_readiness_api.py`
   (`28 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/source_ingestion_readiness.py` moved
   from 546 to 384 lines; `src/app/api/source_ingestion_readiness_models.py`
   is 162 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Review Queue API Model Boundary

Advisor queue and review queue readiness response DTOs now live in
`src/app/api/review_queue_models.py`. `src/app/api/review_queues.py` imports
and explicitly re-exports those DTOs while keeping caller authorization,
entitlement-scope narrowing, repository selection, readiness snapshot
construction, operation-event emission, route metadata, and product-safe
response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate queue service, PM or
compliance queue runtime, Workbench boundary, data-product publication path, or
independently scalable read model. Advisor review queues remain bounded
internal API and readiness foundations until workload, failure-isolation,
ownership, security, or operability evidence justifies a runtime split.

Private-banking, source-safety, and modernization boundaries preserved:

1. The advisor queue route still requires advisor role plus
   `idea.review.queue.read` capability and applies caller entitlement scope
   fail-closed.
2. The readiness route still requires operator role plus
   `idea.review.queue.readiness.read` capability.
3. The queue response still returns ranked idea candidates, page metadata, and
   exclusions only; it does not expose source routes, source content hashes,
   raw evidence, portfolio accounting, suitability/compliance approval,
   execution authority, or report rendering/archive authority.
4. The routes still do not prove Workbench product support, data-product
   certification, external-publication authority, PM/compliance queue support, or
   supported-feature promotion.
5. The slice does not add compatibility shims, legacy route aliases, or new
   runtime process boundaries; it reduces design-time complexity inside the
   current module boundary.

Evidence:

1. Code: `src/app/api/review_queues.py`,
   `src/app/api/review_queue_models.py`,
   `tests/unit/test_review_queue_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_review_queue_models.py tests\unit\test_review_queue_application.py tests\integration\test_review_queue_api.py`
   (`37 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/review_queues.py` moved from 606 to
   484 lines; `src/app/api/review_queue_models.py` is 174 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.
## 2026-08-12: Review Feedback API Handler Boundary

Issue: [#998](https://github.com/sgajbi/lotus-idea/issues/998)

Decision:

`src/app/api/review_workflow.py::record_feedback` stays as the public FastAPI
route entry point, but the route now delegates feedback mutation setup,
application-command execution, permission/entitlement denial mapping,
invalid-request mapping, persistence problem projection, and successful
response assembly to named API-boundary helpers. This mirrors the hardened
`record_review_action` pattern from #606 without changing route behavior.

Why:

`make quality-baseline` listed `record_feedback` as the next production API
hotspot at 99 lines. The function mixed trusted caller context, idempotency,
event lineage, entitlement failure handling, persistence decision projection,
operation-event emission, and response DTO assembly in one route body. Keeping
those concerns named reduces review risk around RFC-0002 Slice 08 human
feedback, Slice 15 operation/security posture, and Slice 19 maintainability.

Preserved boundaries:

1. Route signature, route metadata, response model, status codes,
   ProblemDetails behavior, event-lineage/causation handling, idempotency-key
   semantics, durable-storage-backed truth, operation-event family, and
   `supportedFeaturePromoted=false` remain unchanged.
2. No authentication/authz infrastructure, persistence schema, migration,
   runtime topology, Gateway, Workbench, Core, data-product certification,
   supported-feature promotion, client-publication, or final RFC-0002 closure
   claim is made.
3. No repo-authored wiki source changed because this is internal API-boundary
   maintainability and does not change operator- or user-facing truth.

Evidence:

1. Duplicate issue searches for `record_feedback review_workflow quality
   baseline RFC-0002` and `record_feedback review_workflow maintainability
   hotspot quality-baseline RFC-0002` found no focused existing owner.
2. Focused validation passed: Ruff format/check, MyPy over
   `src/app/api/review_workflow.py`, and 83 review workflow
   API/application/example/entitlement/operation-event tests.
3. Quality validation passed: `make quality-baseline`,
   `make maintainability-gate`, and `make duplicate-implementation-gate`
   (`0` duplicate clusters across `3,572` source/script functions).
