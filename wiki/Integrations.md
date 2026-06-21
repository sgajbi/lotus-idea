# Integrations

`lotus-idea` is an orchestrating domain service. It must integrate through
source-owned APIs, data products, and Gateway/BFF contracts.

## Upstream

1. `lotus-core`
2. `lotus-performance`
3. `lotus-risk`
4. `lotus-advise`
5. `lotus-manage`
6. `lotus-report`
7. `lotus-ai`

## Downstream

1. `lotus-gateway`
2. `lotus-workbench`
3. `lotus-advise`
4. `lotus-manage`
5. `lotus-report`
6. `lotus-render`
7. `lotus-archive`

Integration claims are planned until the relevant RFC-0002 slice is implemented
and certified.

## Data Product Dependencies

Mesh integration truth starts in
`contracts/domain-data-products/lotus-idea-consumers.v1.json`.

The first planned consumer declaration names current upstream products:

1. `lotus-core:PortfolioStateSnapshot:v1`
2. `lotus-performance:ReturnsSeriesBundle:v1`
3. `lotus-risk:RiskMetricsReport:v1`
4. `lotus-advise:AdvisoryProposalLifecycleRecord:v1`
5. `lotus-manage:PortfolioActionRegister:v1`
6. `lotus-report:ClientReportEvidencePack:v1`
7. `lotus-advise:AdvisoryCopilotInteractionRecord:v1`

`lotus-idea` planned producer products remain proposed until implementation and
platform certification.
