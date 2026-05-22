---
block_id: nfr-observability
title: Standard Observability Requirements
type: nfr
version: "1.3"
status: approved
owner: platform-architecture
tags:
  - observability
  - logging
  - metrics
  - tracing
---

## Standard Observability Requirements

Every service must expose the platform's standard observability signals.

- **Logs** — structured JSON, correlation ID on every entry, shipped to the
  central log platform.
- **Metrics** — RED metrics (rate, errors, duration) exposed in Prometheus
  format on `/metrics`.
- **Tracing** — distributed traces emitted via OpenTelemetry with context
  propagated across all integration calls.
- Dashboards and alerts must exist before a service is promoted to production.
