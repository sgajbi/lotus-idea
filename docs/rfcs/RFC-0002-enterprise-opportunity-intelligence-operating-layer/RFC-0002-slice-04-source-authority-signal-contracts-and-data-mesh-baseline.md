# RFC-0002 Slice 04: Source Authority, Signal Contracts, And Data Mesh Baseline

Status: Partially implemented

## Outcome

Turn the source map into machine-readable consumer and producer contracts.

## Current Baseline

The repository now carries proposed source-truth mesh contracts:

1. `contracts/domain-data-products/lotus-idea-products.v1.json`
2. `contracts/domain-data-products/lotus-idea-consumers.v1.json`
3. `contracts/domain-data-products/mesh-readiness.v1.json`
4. `contracts/trust-telemetry/idea-candidate.telemetry.v1.json`
5. `contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json`
6. `contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json`
7. `contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json`

The baseline is deliberately not certified. Products remain `proposed`, the
static telemetry snapshot is blocked, and platform mesh promotion waits for
implementation-backed runtime evidence.

## Required Work

1. Keep `contracts/domain-data-products/` declarations current for
   `lotus-idea` consumer dependencies and proposed producer products.
2. Maintain freshness, source-owner, compatibility, quality, access, SLO, and
   evidence-policy fields for the first promoted product family.
3. Add validation tests or repo-native commands for every declaration expansion.
4. Reconcile exact upstream product names with platform-generated catalogs.

## Acceptance Gate

1. Consumer declarations name real source owners.
2. Producer declarations remain proposed until implementation-backed.
3. Placeholder mesh files do not exist in `contracts/` or operations docs.
4. Platform mesh validation passes before any certification claim.
5. No source fact is accepted without provenance and freshness posture.
