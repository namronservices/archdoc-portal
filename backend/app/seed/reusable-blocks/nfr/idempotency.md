---
block_id: nfr-idempotency
title: Idempotency Requirements
type: nfr
version: "1.1"
status: approved
owner: integration-architecture
tags:
  - idempotency
  - reliability
---

## Idempotency Requirements

All state-changing operations exposed over the network must be idempotent.

- Clients supply an idempotency key on every mutating request.
- The server deduplicates by key for at least 24 hours.
- Retried requests must return the original result, not a duplicate effect.
- Idempotency behaviour must be covered by automated tests.
