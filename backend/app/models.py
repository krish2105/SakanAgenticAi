"""SQLAlchemy ORM models mirroring the Postgres schema in ARCHITECTURE.md Section 8."""
from sqlalchemy import (
    JSON, Boolean, Column, String, Integer, Numeric, Date, DateTime, ForeignKey, Text, func, text
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
    # Phase D: "full DLD or portal data partnership." Distinguishes
    # synthetic demo rows from a real Kaggle/Dubai-Pulse DLD mirror from a
    # (currently nonexistent) licensed partner feed -- see
    # app/services/data_source.py and README "Data partnership".
    data_provenance = Column(String(20), nullable=False, default="synthetic")

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


class User(Base):
    """Extension beyond ARCHITECTURE.md Section 8's original DDL -- added for
    Phase A auth (see the MVP roadmap: deal endpoints must not be publicly
    readable by guessable query_id)."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), default="Agent")  # Agent | Investor | Admin
    created_at = Column(DateTime, server_default=func.now())

    # Billing (Phase B: paid launch -- see MVP roadmap). tier gates monthly
    # full-pipeline query quota (billing_service.PLANS); the stripe_* columns
    # are unset until the user completes a Stripe Checkout at least once.
    tier = Column(String(20), nullable=False, default="starter")
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(30), nullable=True)  # active | canceled | past_due | ...

    # Auth hardening (Phase 3). server_default keeps the ALTER on the existing
    # live users table backfilling cleanly.
    email_verified = Column(Boolean, nullable=False, server_default=text("false"))
    failed_login_attempts = Column(Integer, nullable=False, server_default=text("0"))
    locked_until = Column(DateTime, nullable=True)

    deal_queries = relationship("DealQuery", back_populates="owner")


class AuthToken(Base):
    """Opaque, single-use-ish tokens for refresh sessions, password reset, and
    email verification. Only the SHA-256 hash of the raw token is stored, so a
    DB leak doesn't hand over usable tokens. token_type in
    {refresh, reset, verify}."""

    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    token_type = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, server_default=func.now())


class DealQuery(Base):
    __tablename__ = "deal_queries"

    query_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    raw_query = Column(Text)
    query_type = Column(String(20))
    deal_state = Column(JSONType)
    agent_trace = Column(JSONType)
    created_at = Column(DateTime, server_default=func.now())

    # Job durability (Phase 4 of the MVP roadmap). The pipeline runs
    # fire-and-forget in-process (see pipeline_runner.py); if the instance
    # restarts mid-run, deal_state/agent_trace alone can't distinguish "never
    # started" from "started and got killed" from "genuinely still running" --
    # this column is the authoritative record. pending -> running -> done|failed.
    status = Column(String(20), nullable=False, server_default=text("'pending'"))
    attempt_count = Column(Integer, nullable=False, server_default=text("0"))

    owner = relationship("User", back_populates="deal_queries")


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("deal_queries.query_id"))
    event_type = Column(String(50))
    event_payload = Column(JSONType)
    timestamp = Column(DateTime, server_default=func.now())
