import pytest
from fastapi.testclient import TestClient
from botnode_mvp.main import app
import secrets

client = TestClient(app)

def test_jwt_authentication_flow():
    print("\n🧪 Testing State-of-the-Art JWT Authentication...")
    node_id = f"jwt-bot-{secrets.token_hex(4)}"
    
    # 1. Register and Verify to get a JWT
    client.post("/v1/node/register", json={"node_id": node_id})
    verify_resp = client.post("/v1/node/verify", json={"node_id": node_id, "solution": 133.5})
    assert verify_resp.status_code == 200
    
    jwt_token = verify_resp.json()["session_token"]
    assert jwt_token is not None
    print(f"✅ JWT Token received: {jwt_token[:20]}...")

    # 2. Access protected endpoint using Bearer Token
    # Use publish_listing as a test case
    pub_resp = client.post(
        "/v1/marketplace/publish",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={
            "type": "SKILL_OFFER",
            "label": "jwt-verified-skill",
            "price_tck": 5.0,
            "metadata": {"auth": "jwt"}
        }
    )
    
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "PUBLISHED"
    print("✅ Protected access with Bearer Token: SUCCESS")

    # 3. Access with INVALID JWT
    bad_resp = client.post(
        "/v1/marketplace/publish",
        headers={"Authorization": "Bearer invalid.token.here"},
        json={"label": "fail"}
    )
    assert bad_resp.status_code == 401
    assert "Invalid token" in bad_resp.json()["detail"]
    print("✅ Rejection of invalid JWT: SUCCESS")

    # 4. Access with EXPIRED JWT (simulated by malformed header or waiting, but let's test missing)
    no_auth_resp = client.post(
        "/v1/marketplace/publish",
        json={"label": "fail"}
    )
    assert no_auth_resp.status_code == 401
    print("✅ Rejection of missing credentials: SUCCESS")

if __name__ == "__main__":
    test_jwt_authentication_flow()
