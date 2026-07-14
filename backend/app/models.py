"""SQLAlchemy ORM models mirroring the Postgres schema in ARCHITECTURE.md Section 8."""
from sqlalchemy import (
    JSON, Boolean, Column, String, Integer, Numeric, Date, DateTime, ForeignKey, Text,
    UniqueConstraint, func, text
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

    # Team/seat billing (Phase 11c). NULL for every non-Team user; set for a
    # Team org's owner and its accepted members alike (the owner is a member
    # of their own org, not tracked separately).
    organization_id = Column(Integer, ForeignKey("organizations.organization_id"), nullable=True)

    deal_queries = relationship("DealQuery", back_populates="owner")


class AuthToken(Base):
    """Opaque, single-use-ish tokens for refresh sessions, password reset, and
    email verification. Only the SHA-256 hash of the raw token is stored, so a
    DB leak doesn't hand over usable tokens. token_type in
    {refresh, reset, verify}.

    user_agent/ip_address/last_used_at (Phase 16: session-management UI) are
    only populated for token_type='refresh' rows -- a reset/verify token is
    single-use and emailed, not a "session" a user would recognize or want to
    individually revoke."""

    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    token_type = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, server_default=func.now())
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    last_used_at = Column(DateTime, nullable=True)


class ApiKey(Base):
    """Partner/embed API keys (Phase 20) -- a rate-limited, read-only comps
    endpoint reachable outside the web app/WhatsApp/extension, for a
    proptech tool wanting to embed Sakan AI's comps data. Same
    hash-not-raw-value storage pattern as AuthToken: a DB leak hands over no
    usable key. No billing/quota tie-in yet -- gated purely by
    app.ratelimit's per-key rate limit, not by Stripe tier; that's a
    deliberate scope decision, not an oversight (see README "Partner API")."""

    __tablename__ = "api_keys"

    api_key_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    # Shown in the UI so a user can tell keys apart without ever re-displaying
    # the full secret (e.g. "sk_live_ab12cd34...").
    key_prefix = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, server_default=text("false"))


class ApiKeyUsage(Base):
    """Per-key, per-day request counter for the partner API dashboard's
    volume chart. Deliberately coarse (one row per key per day, incremented
    on each authenticated call) rather than a full request log -- there's
    only one partner endpoint today (GET /partner/v1/comps), so per-endpoint
    breakdown would be a column with a single always-the-same value; add
    that column if/when a second partner endpoint actually ships."""

    __tablename__ = "api_key_usage"
    __table_args__ = (UniqueConstraint("api_key_id", "date", name="uq_api_key_usage_key_date"),)

    usage_id = Column(Integer, primary_key=True, autoincrement=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.api_key_id"), nullable=False)
    date = Column(Date, nullable=False)
    count = Column(Integer, nullable=False, server_default=text("0"))


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

    # Shareable public memo links: NULL means "not shared". The token itself
    # (not a hash of it) is stored, since -- unlike an auth secret -- the
    # token IS the read-capability by design: anyone holding the URL can view
    # the memo, and revoking just means clearing this column, not comparing
    # a submitted value against anything.
    share_token = Column(String(64), nullable=True, unique=True, index=True)

    owner = relationship("User", back_populates="deal_queries")


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("deal_queries.query_id"))
    event_type = Column(String(50))
    event_payload = Column(JSONType)
    timestamp = Column(DateTime, server_default=func.now())


class Organization(Base):
    """A Team-tier billing unit (Phase 11c). One owner (the user who
    checked out for Team), zero or more accepted members. Deliberately
    minimal: no org name/branding beyond a label, no nested roles -- the
    owner manages membership and billing, members just get the shared
    unmetered quota. seat_count mirrors the Stripe subscription's item
    quantity so /billing/team/members' seat usage and the actual invoice
    never silently diverge (kept in sync by team_service.sync_stripe_seats)."""

    __tablename__ = "organizations"

    organization_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    stripe_subscription_id = Column(String(255), nullable=True)
    seat_count = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(DateTime, server_default=func.now())


class TeamInvite(Base):
    """Single-use invite tokens for joining an Organization (Phase 11c).
    Separate from AuthToken (refresh/reset/verify) because those are always
    scoped to "the user this token was issued to acts on their own account";
    an invite instead needs to carry *which org* it grants membership to,
    which AuthToken's schema has no field for."""

    __tablename__ = "team_invites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.organization_id"), nullable=False)
    invited_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    accepted = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, server_default=func.now())


class StripeWebhookEvent(Base):
    """Idempotency record for /billing/webhook (Phase 11a). Stripe explicitly
    documents that webhooks can be delivered more than once for the same
    event -- without this, a replayed checkout.session.completed could
    re-trigger _apply_subscription_to_user redundantly (harmless on its own,
    but a foot-gun for any future handler that isn't naturally idempotent,
    e.g. one that increments a counter or sends an email per delivery)."""

    __tablename__ = "stripe_webhook_events"

    event_id = Column(String(255), primary_key=True)
    event_type = Column(String(100), nullable=False)
    received_at = Column(DateTime, server_default=func.now())


class SavedComp(Base):
    """A user's watchlist entry for a single comparable transaction.
    Natural-keyed on (owner_id, transaction_id) rather than surfacing a
    separate save/unsave concept per user+comp pair with its own lifecycle --
    saving is just "does this row exist," so the unique constraint is what
    makes save idempotent instead of application-level check-then-insert."""

    __tablename__ = "saved_comps"
    __table_args__ = (UniqueConstraint("owner_id", "transaction_id", name="uq_saved_comp_owner_transaction"),)

    saved_comp_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    transaction_id = Column(String(15), ForeignKey("transactions.transaction_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SavedSearch(Base):
    """A saved comps filter that gets a periodic email digest (Phase 25).
    Deliberately a *digest*, not a "new listing" alert: Transaction has no
    insertion timestamp, only transaction_date (the real-world sale date),
    so there's no honest way to tell "added since you last checked" apart
    from "always matched but you hadn't seen it." scripts/send_search_digests.py
    emails the current top matches on a schedule and stamps last_notified_at --
    it never claims something is new that we can't actually prove is new."""

    __tablename__ = "saved_searches"

    saved_search_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    community = Column(String(100), nullable=True)
    property_type = Column(String(20), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    budget_min = Column(Numeric(12, 2), nullable=True)
    budget_max = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_notified_at = Column(DateTime, nullable=True)
