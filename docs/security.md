Security baseline

- Redaction: Use `ledgerloop.security.redact(text)` before logging any raw statement text or descriptors.
- No secrets in repo: use `.env` and local config; avoid printing account numbers.
- Encrypted backups (V1.1): Export normalized data and encrypt with AES-GCM; store key outside repo.
- Least privilege: local-first; no external services by default.
- Determinism: Repeatable imports prevent integrity drift.
- Authentication
  - Currently disabled (single-user mode). Assume all endpoints are accessible to anyone who can reach the service.
  - Production safety should come from network isolation: bind to `127.0.0.1`, firewall the host, or expose only via SSH tunnel/reverse proxy.

- CORS
  - Control via `LEDGERLOOP_CORS` (comma-separated origins). For production, avoid `*` and set explicit origins.

- WebSocket
  - Recommend passing a token during handshake and validating prior to subscription (future work).

- Lifecycle
  - App startup/shutdown managed via FastAPI lifespan; DB connect/close and realtime processors start/stop handled centrally.
