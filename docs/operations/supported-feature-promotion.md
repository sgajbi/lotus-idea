# Supported Feature Promotion

`lotus-idea` currently has no supported external business features. The supported-feature registry
is a publication control, not a roadmap list.

## Source Of Truth

The registry lives at:

1. `supported-features/supported-features.json`
2. `supported-features/supported-features.schema.json`
3. `src/app/application/supported_feature_promotion.py`
4. `scripts/supported_features_gate.py`

Run `make supported-features-gate` before any branch claims a capability is supported.
Run `make supported-feature-promotion-contract-gate` when gate, readiness API,
or generated readiness projection code changes.

## Promotion Contract

An implemented supported-feature entry must carry structured evidence for:

1. stable feature id, business name, owner, RFC, support scope, unsupported scope, and last-reviewed
   UTC timestamp,
2. API surfaces tied to `docs/operations/endpoint-certification-ledger.json`,
3. UI or consumer surfaces with explicit state,
4. source dependencies and authority boundaries,
5. Gateway/Workbench, consumer-publication, and data-product state,
6. code modules, API contracts, tests, runtime evidence, CI evidence, docs, runbooks, proof
   artifacts, known gaps, and the promotion decision reference.

The gate rejects placeholder or string-only promotion evidence. It also resolves referenced code,
contract, documentation, runbook, and test evidence so a registry entry cannot pass with invented
paths or nonexistent pytest functions.

The shared evaluator also requires `last_reviewed_utc` to be no more than 90
days old and not later than the readiness evaluation time. The CLI gate and
runtime readiness use that same evaluator. A missing, invalid, incomplete, or
unresolved registry yields `supported_feature_registry_invalid`; an expired
review additionally yields `supported_feature_promotion_evidence_stale`.
Neither condition counts a feature or exposes validation details or filesystem
paths through the API.

## Runtime Reconciliation

The implementation-proof readiness application, API response, and generated
artifact derive promotion from the validated evaluator result. They do not
count an `implemented` status string independently.

| Registry state | Runtime result |
| --- | --- |
| Valid and empty | `no_supported_features_promoted` |
| Planned or not-applicable record under `features[]` | `supported_feature_registry_invalid` |
| Missing field, path, test, endpoint, or proof evidence | `supported_feature_registry_invalid` |
| Review older than 90 days | Invalid plus `supported_feature_promotion_evidence_stale` |
| Fully evidenced, current implemented entry | Counted and projected consistently by gate, API, and artifact |

## Non-Promotion Boundary

Endpoint certification, a proof artifact, a bounded Gateway route, a Workbench rendering path,
runtime trust telemetry, or a green CI run is not sufficient by itself to promote a feature. A
feature becomes supported only when the registry entry, implementation, tests, OpenAPI/contract
evidence, runtime proof, docs/wiki truth, CI evidence, and known-gap posture agree on `main`.

Current foundation work must continue to use planned, blocked, not-certified, or not-supported
language until that evidence exists.
