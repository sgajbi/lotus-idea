# RFC-0002 Slice 04: Source Authority, Signal Contracts, And Data Mesh Baseline

Status: Planned

## Outcome

Turn the source map into machine-readable consumer and producer contracts.

## Required Work

1. Add or update `contracts/domain-data-products/` declarations for
   `lotus-idea` consumer dependencies and planned producer products.
2. Define freshness, source-owner, compatibility, quality, access, SLO, and
   evidence-policy fields for each product.
3. Add validation tests or repo-native commands for the declarations.
4. Reconcile exact upstream product names with platform-generated catalogs.

## Acceptance Gate

1. Consumer declarations name real source owners.
2. Producer declarations remain proposed until implementation-backed.
3. Platform mesh validation passes.
4. No source fact is accepted without provenance and freshness posture.
