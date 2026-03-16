from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime

class RegisterRequest(BaseModel):
    node_id: str
    signup_token: Optional[str] = None

class VerifyRequest(BaseModel):
    node_id: str
    solution: float
    signup_token: Optional[str] = None

class SkillOffer(BaseModel):
    type: str = "SKILL_OFFER"
    label: str
    price_tck: float
    metadata: Dict

class BountyRequest(BaseModel):
    type: str = "TASK_BOUNTY"
    task_description: str
    max_budget: float
    deadline_ms: int

class EscrowInit(BaseModel):
    seller_id: str
    amount: float

class EscrowSettle(BaseModel):
    escrow_id: str
    proof_hash: str

class PublishOffer(BaseModel):
    type: str # SKILL_OFFER or TASK_BOUNTY
    label: str
    price_tck: float
    metadata: Dict

class BetRequest(BaseModel):
    amount: float

class PackPurchase(BaseModel):
    pack_name: str # Starter, Pro, Enterprise
    fiat_amount: float
    currency: str = "EUR"

class TaskCreate(BaseModel):
    skill_id: str
    input_data: dict

class TaskComplete(BaseModel):
    task_id: str
    output_data: dict
    proof_hash: str

class DisputeRequest(BaseModel):
    task_id: str
    reason: str


class MCPHireRequest(BaseModel):
    integration: str  # "claude" | "cursor" | "zed" | "other"
    capability: str
    payload: dict
    max_price: Optional[float] = 1.0
    deadline_seconds: Optional[int] = 30


class EarlyAccessSignupRequest(BaseModel):
    email: EmailStr
    node_name: Optional[str] = None
    agent_type: Optional[str] = None
    primary_capability: Optional[str] = None
    why_joining: Optional[str] = None


class EarlyAccessSignupResponse(BaseModel):
    signup_token: str
    status: str = "pre_eligible"


class GenesisHallOfFameEntry(BaseModel):
    rank: int
    node_id: str
    name: Optional[str] = None
    awarded_at: datetime


class SkillExecuteRequest(BaseModel):
    skill_id: str
    parameters: dict
    priority: Optional[str] = "normal"  # "high", "normal", "low"


class SkillExecuteResponse(BaseModel):
    job_id: str
    status: str
    queue_position: Optional[int] = None
    estimated_wait: Optional[int] = None  # seconds
