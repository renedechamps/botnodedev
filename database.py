from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database URL from environment or fallback to SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./botnode.db")

# For PostgreSQL, we need to handle the URL slightly differently if it's async or has specific requirements
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
