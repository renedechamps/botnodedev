from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import time
import secrets
from . import models, schemas

# DB Setup (SQLite for MVP)
SQLALCHEMY_DATABASE_URL = "sqlite:///./botnode.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BotNode.io Core Engine")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Anti-Human Middleware
@app.middleware("http")
async def anti_human_filter(request: Request, call_next):
    user_agent = request.headers.get("user-agent", "").lower()
    browsers = ["chrome", "firefox", "safari", "edge"]
    if any(b in user_agent for b in browsers):
        return JSONResponse(
            status_code=406,
            content={
                "error": "Human interface not supported",
                "mission_protocol": "https://botnode.io/mission.pdf"
            }
        )
    return await call_next(request)

# 2. Helper: Is Prime?
def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True

# 3. Endpoints
@app.post("/v1/node/register")
async def register_node(data: schemas.RegisterRequest, request: Request, db: Session = Depends(get_db)):
    # Check if fingerprint or IP already exists to prevent farming
    # (Simplified for MVP)
    
    challenge_payload = [13, 24, 37, 42, 59, 61, 80, 97]
    # Primes are: 13, 37, 59, 61, 97 -> Sum: 267. Result: 133.5
    
    return {
        "status": "NODE_PENDING_VERIFICATION",
        "node_id": data.node_id,
        "wallet": {"initial_balance": 100.0, "state": "FROZEN_UNTIL_CHALLENGE_SOLVED"},
        "verification_challenge": {
            "type": "PRIME_SUM_HASH",
            "payload": challenge_payload,
            "instruction": "Sum all prime numbers in 'payload', multiply by 0.5, and POST to /v1/node/verify",
            "timeout_ms": 200,
            "ts": time.time()
        }
    }

@app.post("/v1/node/verify")
async def verify_node(data: schemas.VerifyRequest, request: Request, db: Session = Depends(get_db)):
    # Logic: Validate the solution
    expected_sum = sum([n for n in [13, 24, 37, 42, 59, 61, 80, 97] if is_prime(n)])
    expected_result = expected_sum * 0.5
    
    if abs(data.solution - expected_result) > 0.01:
        raise HTTPException(status_code=400, detail="Challenge failed: Incorrect solution")

    # Generate API Key
    api_key = f"bn_{secrets.token_hex(24)}"
    
    new_node = models.Node(
        id=data.node_id,
        api_key=api_key,
        ip_address=request.client.host,
        balance=100.0
    )
    db.add(new_node)
    db.commit()
    
    return {
        "status": "NODE_ACTIVE",
        "message": f"Welcome to the cluster, {data.node_id}.",
        "api_key": api_key,
        "unlocked_balance": 100.0
    }

@app.get("/v1/marketplace")
async def get_marketplace(db: Session = Depends(get_db)):
    skills = db.query(models.Skill).all()
    return {
        "timestamp": int(time.time()),
        "market_status": "HIGH_LIQUIDITY",
        "listings": skills
    }

@app.post("/v1/trade/escrow/init")
async def init_escrow(data: schemas.EscrowInit, request: Request, db: Session = Depends(get_db)):
    # 1. Identify Buyer (via API Key header)
    api_key = request.headers.get("X-API-KEY")
    buyer = db.query(models.Node).filter(models.Node.api_key == api_key).first()
    if not buyer: raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 2. Check balance
    if buyer.balance < data.amount:
        raise HTTPException(status_code=402, detail="Insufficient funds")
    
    # 3. Lock funds
    buyer.balance -= data.amount
    
    new_escrow = models.Escrow(
        buyer_id=buyer.id,
        seller_id=data.seller_id,
        amount=data.amount,
        status="PENDING"
    )
    db.add(new_escrow)
    db.commit()
    
    return {"escrow_id": new_escrow.id, "status": "FUNDS_LOCKED"}

@app.post("/v1/trade/escrow/settle")
async def settle_escrow(data: schemas.EscrowSettle, request: Request, db: Session = Depends(get_db)):
    escrow = db.query(models.Escrow).filter(models.Escrow.id == data.escrow_id).first()
    if not escrow: raise HTTPException(status_code=404, detail="Escrow not found")
    
    # 4. Calculate Tax (3%)
    tax = float(escrow.amount) * 0.03
    payout = float(escrow.amount) - tax
    
    # 5. Transfer to Seller
    seller = db.query(models.Node).filter(models.Node.id == escrow.seller_id).first()
    seller.balance += payout
    
    escrow.status = "SETTLED"
    escrow.proof_hash = data.proof_hash
    db.commit()
    
    return {"status": "SETTLED", "payout": payout, "tax": tax}
