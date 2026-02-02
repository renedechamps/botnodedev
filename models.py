from sqlalchemy import Column, String, Integer, Float, Boolean, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime
import uuid

Base = declarative_base()

class Node(Base):
    __tablename__ = "nodes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_hash = Column(String, unique=True, index=True)
    ip_address = Column(String, index=True)
    fingerprint = Column(String, index=True)
    balance = Column(Numeric(12, 2), default=100.0)
    reputation_score = Column(Float, default=1.0)
    strikes = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = Column(String, ForeignKey("nodes.id"))
    label = Column(String)
    price_tck = Column(Numeric(10, 2))
    metadata_json = Column(JSON)
    provider = relationship("Node")

class Escrow(Base):
    __tablename__ = "escrows"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String, ForeignKey("nodes.id"))
    seller_id = Column(String, ForeignKey("nodes.id"))
    amount = Column(Numeric(10, 2))
    status = Column(String, default="PENDING") # PENDING, SETTLED, DISPUTED, REFUNDED
    proof_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    auto_settle_at = Column(DateTime, nullable=True) # 24h window

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(String, ForeignKey("skills.id"))
    buyer_id = Column(String, ForeignKey("nodes.id"))
    seller_id = Column(String, ForeignKey("nodes.id"), nullable=True)
    input_data = Column(JSON)
    output_data = Column(JSON, nullable=True)
    status = Column(String, default="OPEN") # OPEN, IN_PROGRESS, COMPLETED, FAILED
    escrow_id = Column(String, ForeignKey("escrows.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
