# Stephanie CEO decision intake — starter

A Python API for recording decision requests in a persistent SQLite queue. Every request remains PENDING_REVIEW; it never approves or executes actions. This is a starter, not the pictured dashboard or a replacement for the existing CEO decision engine. No wallets, payments, live integrations, or token transactions are connected.

## Linux / Docker Compose

Generate a unique secret on the host and keep it out of Git and shell history. Store it in a protected deployment secret manager or a root-readable environment file. Set `STEPHANIE_API_TOKEN` to at least 32 bytes, then run:

```sh
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:8000/health
```

POST JSON with `project`, `decision_type`, and `summary` to `/decisions` with `Authorization: Bearer <token>`; GET `/decisions` returns the latest 100. `/health` checks process availability only, not integrations or data integrity. The port binds to loopback; use a properly secured TLS reverse proxy and individual user identity/authorization before any network deployment. The shared token is not user identity and this starter has no approval endpoint, audit ledger, backups, upload handling, or production-ready access control. Preserve and back up the Docker volume before changes.
