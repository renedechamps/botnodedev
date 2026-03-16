import pytest
from fastapi.testclient import TestClient
from botnode_mvp.main import app
import secrets

client = TestClient(app)

def test_get_badge_svg_success():
    # 1. Register a node
    node_id = f"test-badge-{secrets.token_hex(4)}"
    reg_resp = client.post("/v1/node/register", json={"node_id": node_id})
    assert reg_resp.status_code == 200, f"Failed to register node: {reg_resp.text}"
    
    # 2. Call GET /v1/node/{node_id}/badge.svg
    resp = client.get(f"/v1/node/{node_id}/badge.svg")
    
    # 3. Verify response
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/svg+xml"
    assert "<svg" in resp.text
    assert node_id in resp.text

def test_get_badge_svg_not_found():
    # Call with non-existent ID
    resp = client.get(f"/v1/node/non-existent-id-{secrets.token_hex(4)}/badge.svg")
    assert resp.status_code == 404
