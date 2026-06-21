# Observability Baseline

This repository starts from the Lotus platform observability scaffold.

## Default Signals

- /health, /health/live, and /health/ready
- /metrics outside the OpenAPI schema
- correlation and trace response headers
- structured JSON application events
- product-safe error responses

## Sensitive-Content Rule

Logs, metrics, traces, dashboards, and evidence artifacts must not include client names, portfolio
ids, holdings, raw entitlement failures, request bodies, response bodies, trace ids, or correlation
ids as metric labels.
