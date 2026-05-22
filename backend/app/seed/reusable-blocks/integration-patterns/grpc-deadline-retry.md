---
block_id: integration-grpc-deadline-retry
title: gRPC Deadline and Retry Standard
type: integration-pattern
version: "1.0"
status: approved
owner: integration-architecture
tags:
  - grpc
  - resilience
  - retry
---

## gRPC Deadline and Retry Standard

gRPC integrations must apply explicit deadlines and a bounded retry policy.

- Every call sets an absolute deadline; unbounded calls are prohibited.
- Retries apply only to idempotent methods and use exponential backoff with
  jitter.
- The total retry budget must not exceed the caller's own deadline.
- `DEADLINE_EXCEEDED` and `UNAVAILABLE` are the only retryable status codes.
