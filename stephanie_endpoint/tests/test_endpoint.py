"""Tests for the Stephanie endpoint."""

import hashlib
import hmac
import json
import os

import pytest
from fastapi.testclient import TestClient

# Set env vars before importing the app
os.environ["STEPHANIE_API_KEY"] = "test-api-key-123"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"

from app.main import app  # noqa: E402

client = TestClient(app)

AUTH_HEADER = {"Authorization": "Bearer test-api-key-123"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "stephanie-endpoint"

    def test_health_has_version(self):
        resp = client.get("/health")
        assert "version" in resp.json()


# ---------------------------------------------------------------------------
# Execute endpoint
# ---------------------------------------------------------------------------

class TestExecute:
    def test_execute_requires_auth(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            json={"action": "create_job", "source": "test"},
        )
        assert resp.status_code == 401

    def test_execute_rejects_bad_key(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers={"Authorization": "Bearer wrong-key"},
            json={"action": "create_job", "source": "test"},
        )
        assert resp.status_code == 403

    def test_execute_create_job(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={
                "action": "create_job",
                "source": "openc law",
                "data": {
                    "client": "Dave McCoy",
                    "address": "33 Ashland St, Newburyport, MA",
                    "scope": "Porch repair",
                    "budget": 25000,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["action"] == "create_job"
        assert "request_id" in data
        assert data["result"]["client"] == "Dave McCoy"

    def test_execute_dry_run(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={
                "action": "create_job",
                "source": "openc law",
                "dry_run": True,
                "data": {"client": "Test"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dry_run"
        assert data["result"]["dry_run"] is True
        assert data["result"]["validated"] is True

    def test_execute_check_permit(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={
                "action": "check_permit",
                "source": "test",
                "data": {"address": "33 Ashland St"},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["result"]["permit_status"] == "pending_review"

    def test_execute_sync_crm(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={"action": "sync_crm", "source": "test", "data": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["result"]["status"] == "synced"

    def test_execute_get_status(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={
                "action": "get_status",
                "source": "test",
                "data": {"job_id": "job_123"},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["result"]["job_id"] == "job_123"

    def test_execute_invalid_action(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={"action": "nonexistent", "source": "test"},
        )
        assert resp.status_code == 422

    def test_execute_returns_request_id_header(self):
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers=AUTH_HEADER,
            json={"action": "get_status", "source": "test", "data": {}},
        )
        assert "x-request-id" in resp.headers

    def test_execute_preserves_custom_request_id(self):
        custom_id = "my-custom-id-999"
        resp = client.post(
            "/api/v1/stephanie/execute",
            headers={**AUTH_HEADER, "X-Request-ID": custom_id},
            json={"action": "get_status", "source": "test", "data": {}},
        )
        assert resp.headers["x-request-id"] == custom_id
        assert resp.json()["request_id"] == custom_id


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

def _sign_payload(payload: dict) -> str:
    body = json.dumps(payload).encode()
    sig = hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


class TestWebhook:
    def test_webhook_requires_signature(self):
        resp = client.post(
            "/api/v1/webhooks/openclaw",
            json={"event_type": "job.created", "payload": {}},
        )
        assert resp.status_code == 401

    def test_webhook_rejects_bad_signature(self):
        resp = client.post(
            "/api/v1/webhooks/openclaw",
            headers={"X-Webhook-Signature": "sha256=badhash"},
            json={"event_type": "job.created", "payload": {}},
        )
        assert resp.status_code == 403

    def test_webhook_valid_event(self):
        payload = {"event_type": "job.created", "payload": {"job_id": "j1"}}
        resp = client.post(
            "/api/v1/webhooks/openclaw",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": _sign_payload(payload),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"] is True
        assert data["event_type"] == "job.created"

    def test_webhook_returns_request_id(self):
        payload = {"event_type": "permit.updated", "payload": {}}
        resp = client.post(
            "/api/v1/webhooks/openclaw",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": _sign_payload(payload),
            },
        )
        assert "x-request-id" in resp.headers
        assert "request_id" in resp.json()
