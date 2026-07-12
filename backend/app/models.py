"""SQLAlchemy ORM models mirroring the Postgres schema in ARCHITECTURE.md Section 8."""
from sqlalchemy import (
    JSON, Column, String, Integer, Numeric, Date, DateTime, ForeignKey, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# JSONB on Postgres (production), plain JSON elsewhere (e.g. SQLite in tests) --
# JSONB has no SQLite compiler support, and tests run against SQLite so the
# suite doesn't require a live Postgres instance.
JSONType = JSON().with_variant(JSONB, "postgresql")


class Developer(Base):
    __tablename__ = "developers"

    developer_id = Column(String(10), primary_key=True)
    name = Column(String(100))
    track_record_score = Column(Integer)
    active_projects_count = Column(Integer)
    delivery_delay_rate = Column(Numeric(4, 2))

    buildings = relationship("Building", back_populates="developer")


class Building(Base):
    __tablename__ = "buildings"

    building_id = Column(String(10), primary_key=True)
    name = Column(String(150))
    community = Column(String(100))
    developer_id = Column(String(10), ForeignKey("developers.developer_id"))
    completion_status = Column(String(20))
    total_units = Column(Integer)
    avg_price_per_sqft = Column(Numeric(10, 2))

    developer = relationship("Developer", back_populates="buildings")
    transactions = relationship("Transaction", back_populates="building")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(15), primary_key=True)
    building_id = Column(String(10), ForeignKey("buildings.building_id"))
    community = Column(String(100))
    property_type = Column(String(20))
    bedrooms = Column(Integer)
    size_sqft = Column(Numeric(8, 2))
    price_aed = Column(Numeric(12, 2))
    price_per_sqft = Column(Numeric(10, 2))
    transaction_type = Column(String(20))
    transaction_date = Column(Date)
    registration_type = Column(String(20))
    buyer_type = Column(String(20))

    building = relationship("Building", back_populates="transactions")


class OffPlanProject(Base):
    __tablename__ = "off_plan_projects"

    project_id = Column(String(10), primary_key=True)
    name = Column(String(150))
    developer_id = Column(String(10), ForeignKey("developers.developer_id"))
    community = Column(String(100))
    launch_date = Column(Date)
    handover_date = Column(Date)
    payment_plan_structure = Column(Text)
    escrow_account_status = Column(String(20))
    rera_registration_number = Column(String(30))
    percent_sold = Column(Numeric(5, 2))


class DealQuery(Base):
    __tablename__ = "deal_queries"

    query_id = Column(Integer, primary_key=True, autoincrement=True)
    raw_query = Column(Text)
    query_type = Column(String(20))
    deal_state = Column(JSONType)
    agent_trace = Column(JSONType)
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("deal_queries.query_id"))
    event_type = Column(String(50))
    event_payload = Column(JSONType)
    timestamp = Column(DateTime, server_default=func.now())
