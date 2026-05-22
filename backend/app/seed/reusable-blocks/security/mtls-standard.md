---
block_id: security-mtls-standard
title: mTLS Standard
type: security
version: "1.0"
status: approved
owner: security-architecture
tags:
  - mtls
  - transport-security
---

## mTLS Standard

All internal service-to-service traffic must be protected with mutual TLS.

- Both client and server present X.509 certificates issued by the internal CA.
- Certificates must be rotated automatically at least every 90 days.
- TLS 1.2 is the minimum accepted version; TLS 1.3 is preferred.
- Plaintext fallback is prohibited inside the trust boundary.
