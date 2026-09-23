from fastapi.testclient import TestClient

from nobleport.api import create_app


def client() -> TestClient:
    return TestClient(create_app())


def test_health():
    c = client()
    r = c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["modules"] >= 50
    assert body["agents"] == ["cyborg", "gcagent", "permitstream", "stephanie"]
    assert body["voice"]["provider"] == "voicebox"


def test_voice_status_disabled(monkeypatch):
    monkeypatch.setenv("STEPHANIE_VOICE_ENABLED", "false")
    c = client()
    r = c.get("/voice/status")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "voicebox"
    assert body["status"] == "disabled"
    assert body["reachable"] is False


def test_module_listing_and_filters():
    c = client()
    everything = c.get("/modules").json()
    assert everything["count"] >= 50
    permits = c.get("/modules", params={"cluster": "permits"}).json()
    assert permits["count"] >= 5
    assert all(m["cluster"] == "permits" for m in permits["modules"])
    assert all(m["agent"] == "permitstream" for m in permits["modules"])


def test_module_detail_exposes_gating():
    c = client()
    r = c.get("/modules/token.mint_burn")
    assert r.status_code == 200
    body = r.json()
    assert body["human_gate"] is True
    assert body["autonomous_execution_blocked"] is True
    assert c.get("/modules/no.such.module").status_code == 404


def test_workflow_lifecycle_over_http():
    c = client()
    run = c.post("/workflows/lead_to_estimate/start",
                 json={"payload": {"lead": {"name": "Ada"}}}).json()
    assert run["state"] == "AWAITING_APPROVAL"
    approval_id = run["pending_approval_id"]

    pending = c.get("/approvals").json()["pending"]
    assert any(p["id"] == approval_id for p in pending)

    resolved = c.post(f"/approvals/{approval_id}/resolve",
                      json={"approved": True, "actor": "ops@nobleport"}).json()
    assert resolved["state"] == "COMPLETED"

    fetched = c.get(f"/runs/{run['id']}").json()
    assert fetched["state"] == "COMPLETED"

    # double-resolve is a conflict
    again = c.post(f"/approvals/{approval_id}/resolve",
                   json={"approved": True, "actor": "ops@nobleport"})
    assert again.status_code == 409


def test_unknown_workflow_404():
    c = client()
    assert c.post("/workflows/nope/start", json={"payload": {}}).status_code == 404


def test_avatar_websocket_dialog(monkeypatch):
    monkeypatch.setenv("STEPHANIE_VOICE_ENABLED", "false")
    c = client()
    with c.websocket_connect("/ws/avatar") as ws:
        ws.send_text("Can you help with a permit?")
        reply = ws.receive_json()
        assert reply["persona"] == "stephanie"
        assert "PermitStream" in reply["reply"]
        assert reply["voice"] == {
            "provider": "voicebox",
            "enabled": False,
            "queued": False,
        }
        ws.send_text("what about NBPT tokens?")
        reply = ws.receive_json()
        assert "multi-sig" in reply["reply"]
