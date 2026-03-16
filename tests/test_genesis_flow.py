import pytest
from fastapi.testclient import TestClient
from botnode_mvp.main import app, models, database
from botnode_mvp.worker import check_and_award_genesis_badges
import secrets
from datetime import datetime

client = TestClient(app)

def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True

def register_and_get_key(node_id=None):
    if not node_id:
        node_id = f"test-node-{secrets.token_hex(4)}"
    
    # 1. Register
    reg_resp = client.post("/v1/node/register", json={"node_id": node_id})
    assert reg_resp.status_code == 200
    challenge = reg_resp.json()["verification_challenge"]
    
    # 2. Verify
    payload = challenge["payload"]
    solution = sum([n for n in payload if is_prime(n)]) * 0.5
    
    verify_resp = client.post("/v1/node/verify", json={"node_id": node_id, "solution": solution})
    assert verify_resp.status_code == 200
    return verify_resp.json()["api_key"], node_id

def test_genesis_lifecycle():
    # 1. Early Access Signup
    email = f"genesis_test_{secrets.token_hex(4)}@example.com"
    ea_resp = client.post("/v1/early-access", json={
        "email": email,
        "node_name": "GenesisPrime",
        "why_joining": "E2E Test",
        "agent_type": "TEST_BOT"
    })
    assert ea_resp.status_code == 200, f"Early access failed: {ea_resp.text}"
    signup_token = ea_resp.json()["signup_token"]
    assert signup_token.startswith("ea_")

    # 2. Register Node with signup_token
    node_id = f"genesis-node-{secrets.token_hex(4)}"
    reg_resp = client.post("/v1/node/register", json={
        "node_id": node_id,
        "signup_token": signup_token
    })
    assert reg_resp.status_code == 200
    challenge = reg_resp.json()["verification_challenge"]

    # Solve challenge
    solution = sum([n for n in challenge["payload"] if is_prime(n)]) * 0.5

    # 3. Verify Node with signup_token to complete linking
    verify_resp = client.post("/v1/node/verify", json={
        "node_id": node_id,
        "solution": solution,
        "signup_token": signup_token
    })
    assert verify_resp.status_code == 200
    
    # 4. Verify linking in DB
    db = database.SessionLocal()
    try:
        # Check Signup -> Node link
        signup = db.query(models.EarlyAccessSignup).filter(
            models.EarlyAccessSignup.signup_token == signup_token
        ).first()
        assert signup.linked_node_id == node_id
        
        # Check Node -> Signup link
        node = db.query(models.Node).filter(models.Node.id == node_id).first()
        assert node.signup_token == signup_token
        
        # Ensure genesis fields are empty initially
        assert node.first_settled_tx_at is None
        assert node.has_genesis_badge is False
    finally:
        db.close()

    # 5. Simulate Trade Settlement
    # Create a buyer
    buyer_key, buyer_id = register_and_get_key()
    
    # Init Escrow (Buyer pays Seller)
    trade_amount = 50.0
    init_resp = client.post(
        "/v1/trade/escrow/init",
        headers={"X-API-KEY": buyer_key},
        json={"seller_id": node_id, "amount": trade_amount}
    )
    assert init_resp.status_code == 200
    escrow_id = init_resp.json()["escrow_id"]
    
    # Settle Escrow
    settle_resp = client.post("/v1/trade/escrow/settle", json={
        "escrow_id": escrow_id,
        "proof_hash": "genesis_proof_123"
    })
    assert settle_resp.status_code == 200
    assert settle_resp.json()["status"] == "SETTLED"

    # 6. Verify first_settled_tx_at update
    db = database.SessionLocal()
    try:
        node = db.query(models.Node).filter(models.Node.id == node_id).first()
        assert node.first_settled_tx_at is not None
        
        # 7. Verify Badge Assignment (Run worker logic)
        # Note: calling the worker function directly
        check_and_award_genesis_badges(db)
        db.commit()
        
        # Refresh and verify
        db.refresh(node)
        assert node.has_genesis_badge is True
        assert node.genesis_rank is not None
        
        # Verify Bonus (Initial 100 + Trade ~48.5 + Bonus 300 = ~448.5)
        # Exact calculation: 100 + (50 * 0.97) + 300 = 448.5
        assert node.balance > 400.0
        
    finally:
        db.close()
