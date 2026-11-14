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

## Outbound SMS (disabled by default)

Set `SMS_ENABLED=true`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, and comma-separated `SMS_ALLOWED_RECIPIENTS` in the server's protected environment. Use E.164 phone numbers. Only add recipients who have agreed to the intended messages. The allowlist is not an opt-out or consent management system. Do not place credentials in React, source control, or chat.

Authenticated `POST /send-sms/` accepts JSON `{"request_id":"unique-16-char-id", "to":"+15551234567", "message":"Plan ready for review."}`. Use a fresh unique ID for each intended message; reuse that ID on retry. A durable record suppresses repeated submissions, including ambiguous timeouts. `queued` means the provider accepted the request, not that the handset received it. For `unknown` or `submitting`, check Twilio before taking any further action; do not create a new request ID blindly. No callbacks or delivery tracking are implemented. The API does not automatically message on dashboard load, job changes, or a schedule. Add identity-based access controls, recipient consent/opt-out enforcement, rate limits, TLS, and monitoring before production exposure. No client-side secrets or automatic promises about pricing or start dates are included.
