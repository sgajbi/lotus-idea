# Data Mesh Readiness

Status: Planned.

Certification status: not certified.

`lotus-idea` is a day-one data-mesh participant in design and repository
governance. It is not yet a certified data-mesh producer because business
runtime behavior is intentionally not implemented.

## Source Truth

1. Producer declarations:
   `contracts/domain-data-products/lotus-idea-products.v1.json`.
2. Consumer declarations:
   `contracts/domain-data-products/lotus-idea-consumers.v1.json`.
3. Mesh readiness posture:
   `contracts/domain-data-products/mesh-readiness.v1.json`.
4. Trust telemetry fallback:
   `contracts/trust-telemetry/idea-candidate.telemetry.v1.json`.
5. SLO, access, and evidence policies:
   `contracts/mesh-slo/`, `contracts/mesh-access/`, and
   `contracts/mesh-evidence/`.

## Promotion Rule

Every `lotus-idea` product remains `proposed` until:

1. endpoint behavior is implemented and certified,
2. every source-owned input has provenance, freshness, and trust metadata,
3. runtime telemetry replaces static fallback evidence,
4. platform source-manifest inclusion and mesh certification pass,
5. Gateway and Workbench discovery expose only supported behavior,
6. README, repo context, supported features, RFC evidence, and wiki source are
   updated on `main`.

The static telemetry snapshot is deliberately blocked so operators and future
agents cannot treat the day-one contract baseline as runtime certification.

## Current Consumer Source Map

The repo-local consumer declaration names the source-authority products needed
by the RFC-0002 first-wave map. The first high-cash / idle-liquidity journey
uses Core-owned portfolio state, holdings/cash balance, cash movement, and
cashflow projection evidence. Later first-wave families reference
Performance-owned returns and mandate performance health, Risk-owned risk
metrics and scenario/mandate risk posture, Advise-owned proposal/policy/copilot
records, Manage-owned action register posture, and Report-owned client report
evidence.

These dependencies are not runtime certification. They are the source-owner
contract skeleton that later implementation slices must consume through ports,
supportability handling, tests, and certification evidence.
