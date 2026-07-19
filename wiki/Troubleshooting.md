# Troubleshooting

This page gives first-response checks for `lotus-idea` operators and future
implementation agents. It routes deeper investigation to the runbooks, endpoint
certification ledger, and CI gates instead of duplicating every proof detail.

Current posture: internal foundation and operator diagnostics only. A failing
diagnostic usually means a proof artifact, source dependency, entitlement,
runtime configuration, or repository posture is missing. It should not be
worked around by weakening blockers or promoting unsupported claims.

## First Checks

| Symptom | First command or endpoint | What to inspect |
| --- | --- | --- |
| Service is not reachable | `GET /health/live` | Process startup, port `8330`, container logs, dependency install. |
| Readiness is degraded | `GET /health/ready` | Intentional drain state, runtime startup errors, deployment routing, missing durable repository configuration, or unavailable configured PostgreSQL for `demo`, `staging`, or `production`. |
| OpenAPI or Swagger looks stale | `make openapi-gate` and `make endpoint-certification-gate` | Route metadata, examples, endpoint ledger synchronization, problem responses. |
| Wiki page is missing or live wiki looks stale | `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-idea` | Repo-local `wiki/` versus published `lotus-idea.wiki.git`; publish after merge if source changed. |
| API returns `403` | Caller-context headers and required `idea.*` capability | Do not bypass fail-closed entitlement behavior; fix caller identity or documented capability. |
| Mutating API returns conflict | `Idempotency-Key` and request payload fingerprint | Same key with different payload is a governed conflict, not a retry bug. |
| Mutating API returns `durable_repository_not_configured` | `LOTUS_IDEA_RUNTIME_PROFILE` and `LOTUS_IDEA_DATABASE_URL` | Production-like profiles require PostgreSQL-backed writes; configure the database URL or use explicit `local`/`test` profile only for non-production work. |
| Mutating API returns `durable_repository_unavailable` | PostgreSQL connectivity and configuration | Verify the configured database, credentials, network path, and deployment secret wiring without pasting DSNs, passwords, hostnames, or raw driver errors into tickets or proof artifacts. |
| Candidate or workflow record is missing | `GET /api/v1/idea-candidates/{candidateId}` or workflow-specific endpoint | Confirm candidate persistence, active repository provider, and tenant/book/portfolio/client scope. |
| Source-ingestion readiness is blocked | `GET /api/v1/source-ingestion/readiness` | Manifest, durable repository posture, Core source configuration, receipt-bound runtime evidence, scheduled-worker source contract, and separately observed deployment evidence. |
| Outbox delivery is blocked | `GET /api/v1/outbox-delivery/readiness` | Broker configuration, publisher adapter, durable repository posture, consumer runtime proof, platform mesh event proof. |
| Outbox event cannot be correlated to a request | `make outbox-event-contract-gate` | Authorized durable row and publisher envelope must contain distinct `correlationId` and `traceId`; `causationId` is optional parent-event identity only. Do not copy raw broker payloads or identifiers into tickets. |
| Downstream realization is blocked | `GET /api/v1/downstream-realization/readiness` | Advise/Manage route source contracts, local downstream submission denominator and unresolved reconciliation workload, separate live route-serving/acceptance receipts, Report intake/materialization source contracts, live materialization/render/archive evidence, adapter configuration, and client-publication blockers. |
| Data-mesh posture is blocked | `GET /api/v1/data-mesh/readiness` | Platform source-manifest/catalog proof, SLO/access/evidence policy, runtime telemetry, and machine-verifiable Gateway/Workbench discovery evidence. |
| AI explanation is blocked | `GET /api/v1/ai-explanations/readiness` | Guardrails, model-risk operations proof, AI lineage store proof, `lotus-ai` workflow-pack registration/runtime execution proof. |

## Local Validation Path

```powershell
make documentation-contract-gate
make implementation-truth-gate
make openapi-gate
make endpoint-certification-gate
make supported-features-gate
```

Use `make check` when the issue touches code, contracts, endpoint metadata, or
tests. Use `make ci` for broad local aggregate proof. Use `make ci-release`
when the change could affect generated release/review evidence, Docker,
PostgreSQL runtime behavior, image scan, container smoke, SBOM, or release-lane
parity and the required local services are available.

## Wiki Publication Problems

| Observation | Likely cause | Correct action |
| --- | --- | --- |
| Source files end in `.md` | Normal GitHub wiki source format | Keep `.md` files in repo-local `wiki/`; same-wiki links should omit `.md`, for example `[Overview](Overview)`. |
| GitHub wiki does not show latest source | Published wiki is behind repo-local `main` | Merge source changes, then run `Sync-RepoWikis.ps1 -Publish -Repository lotus-idea`. |
| GitHub page-level edit is unavailable | Permission/session or GitHub UI state | Edit repo-local `wiki/` source, merge to `main`, and publish; do not hand-edit the publish target. |
| A page is not reachable from navigation | Missing `Home` or `_Sidebar` link | Add the page to `Home.md` and `_Sidebar.md` in the same PR. |
| Link opens raw source or a 404 | Wrong link type | Same-wiki links use page names without `.md`; repository file links should use full GitHub `blob/main` URLs. |

## Evidence And Claim Hygiene

| If you see | Do this |
| --- | --- |
| A doc says production-ready, demo-ready, certified, or supported without proof | Move it to roadmap/gap language or add the missing code, tests, OpenAPI/contract evidence, supported-features update, CI proof, and mainline validation. |
| A proof artifact clears one blocker | Clear only that blocker; preserve unrelated Gateway, Workbench, data-mesh, downstream, client-publication, and supported-feature blockers. |
| An upstream source value is missing or stale | Return blocked/degraded posture with source-owner evidence; do not recompute another repository's official fact. |
| AI output includes unsupported advice or action language | Block or fall back through deterministic guardrails; do not route it to clients or downstream execution. |
| A branch contains wiki/docs/RFC truth not on `main` | Run stranded-truth reconciliation and merge, cherry-pick, supersede, or delete with evidence before claiming closure. |

## Deeper References

| Reference | Use |
| --- | --- |
| [Operations Runbook](Operations-Runbook) | Detailed operator diagnostics, readiness endpoints, proof artifacts, and operation-event interpretation. |
| [API Surface](API-Surface) | Route-family map, error-model expectations, and API evidence paths. |
| [Validation and CI](Validation-and-CI) | Local and GitHub gate meanings. |
| [Security and Governance](Security-and-Governance) | Entitlements, sensitive-data rules, source authority, and AI governance posture. |
| [Supported Features](Supported-Features) | Current supported-feature truth and promotion requirements. |

Do not treat a troubleshooting workaround as product support. If a fix changes
runtime behavior, route shape, endpoint evidence, operator procedure, or
supported posture, update README, wiki, docs, RFC evidence, repository context,
and `supported-features` as applicable in the same slice.
