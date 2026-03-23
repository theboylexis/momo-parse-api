"""SQLAlchemy table definitions."""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func

from db.engine import Base


class JobRecord(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    webhook_url = Column(String, nullable=True)
    message_count = Column(Integer, default=0)


class CounterpartyProfile(Base):
    __tablename__ = "counterparty_profiles"

    key = Column(String, primary_key=True)
    counts = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
