---
block_id: integration-kafka-event-publishing
title: Kafka Event Publishing Pattern
type: integration-pattern
version: "2.0"
status: approved
owner: integration-architecture
tags:
  - kafka
  - eventing
  - messaging
---

## Kafka Event Publishing Pattern

Domain events published to Kafka must follow the platform eventing contract.

- Events carry a versioned schema registered in the schema registry.
- Each event includes an event ID, event type, occurred-at timestamp, and
  partition key.
- Producers publish via the transactional outbox to guarantee at-least-once
  delivery.
- Consumers must be idempotent and tolerate out-of-order redelivery.
