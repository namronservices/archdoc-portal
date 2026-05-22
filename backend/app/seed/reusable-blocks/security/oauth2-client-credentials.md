---
block_id: security-oauth2-client-credentials
title: OAuth2 Client Credentials
type: security
version: "1.2"
status: approved
owner: security-architecture
tags:
  - oauth2
  - service-to-service
---

## OAuth2 Client Credentials

Service-to-service authentication must use the OAuth2 client credentials grant
wherever machine-to-machine access is required.

- Clients obtain access tokens from the central authorization server.
- Tokens must be short-lived (max 15 minutes) and scoped to the calling service.
- Client secrets must be stored in the platform secret manager, never in source.
- Token validation must verify issuer, audience, and expiry on every request.
