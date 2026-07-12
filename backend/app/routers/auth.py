from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import config
from app.auth import (
    consume_single_use_token,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    create_verify_token,
    get_current_user,
    hash_password,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from app.db import get_engine, get_session_factory
from app.models import Base, User
from app.ratelimit import limiter
from app.services.email import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])

_VALID_ROLES = {"Agent", "Investor", "Admin"}


def ensure_users_table() -> None:
    # Alembic owns the schema in production (see pipeline_runner.ensure_tables);
    # this lazy create_all only runs in dev/test.
    if config.IS_PRODUCTION:
        return
    Base.metadata.create_all(get_engine())


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "Agent"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        # Self-registration can never mint an Admin -- only Agent/Investor.
        if v not in {"Agent", "Investor"}:
            raise ValueError("role must be one of ['Agent', 'Investor']")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class VerifyRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserOut(BaseModel):
    user_id: int
    email: str
    full_name: str | None
    role: str
    email_verified: bool


def _frontend_link(path: str, token: str) -> str:
    base = config.FRONTEND_URL.rstrip("/")
    return f"{base}{path}?token={token}"


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest) -> TokenResponse:
    ensure_users_table()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = User(
            email=body.email.lower(),
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
            role=body.role,
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        session.refresh(user)

        # Capture scalars before the session closes -- the ORM instance is
        # detached (and its attributes expired) outside the `with` block.
        email = user.email
        access = create_access_token(user.user_id, user.email)
        refresh = create_refresh_token(session, user.user_id)
        verify_token = create_verify_token(session, user.user_id)
        session.commit()

    send_verification_email(email, _frontend_link("/verify", verify_token))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest) -> TokenResponse:
    ensure_users_table()
    session_factory = get_session_factory()
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == body.email.lower()))

        # Account lockout: after MAX_FAILED_LOGINS bad attempts, refuse for
        # ACCOUNT_LOCKOUT_MINUTES even with the right password.
        if user is not None and user.locked_until is not None:
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                raise HTTPException(
                    status_code=429,
                    detail="Too many failed attempts. Try again later.",
                )

        if user is None or not verify_password(body.password, user.hashed_password):
            if user is not None:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= config.MAX_FAILED_LOGINS:
                    user.locked_until = now + timedelta(minutes=config.ACCOUNT_LOCKOUT_MINUTES)
                    user.failed_login_attempts = 0
                session.add(user)
                session.commit()
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        # Success: clear the failure counter and issue tokens.
        user.failed_login_attempts = 0
        user.locked_until = None
        session.add(user)
        access = create_access_token(user.user_id, user.email)
        refresh = create_refresh_token(session, user.user_id)
        session.commit()

    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    ensure_users_table()
    session_factory = get_session_factory()
    with session_factory() as session:
        rotated = rotate_refresh_token(session, body.refresh_token)
        if rotated is None:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        new_refresh, user_id = rotated
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User no longer exists")
        access = create_access_token(user.user_id, user.email)
        session.commit()
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
async def logout(body: LogoutRequest) -> None:
    ensure_users_table()
    session_factory = get_session_factory()
    with session_factory() as session:
        revoke_refresh_token(session, body.refresh_token)
        session.commit()


@router.post("/forgot", status_code=202)
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotRequest) -> dict:
    """Always returns 202 regardless of whether the email exists -- never leak
    which addresses are registered."""
    ensure_users_table()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == body.email.lower()))
        if user is not None:
            reset_token = create_reset_token(session, user.user_id)
            session.commit()
            send_password_reset_email(user.email, _frontend_link("/reset", reset_token))
    return {"detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset", status_code=200)
async def reset_password(body: ResetRequest) -> dict:
    ensure_users_table()
    session_factory = get_session_factory()
    with session_factory() as session:
        user_id = consume_single_use_token(session, body.token, "reset")
        if user_id is None:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        user.hashed_password = hash_password(body.new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        session.add(user)
        # A password reset logs out every existing session.
        revoke_all_refresh_tokens(session, user_id)
        session.commit()
    return {"detail": "Password updated. Please sign in with your new password."}


@router.post("/verify", status_code=200)
async def verify_email(body: VerifyRequest) -> dict:
    ensure_users_table()
    session_factory = get_session_factory()
    with session_factory() as session:
        user_id = consume_single_use_token(session, body.token, "verify")
        if user_id is None:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        user.email_verified = True
        session.add(user)
        session.commit()
    return {"detail": "Email verified."}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        email_verified=bool(current_user.email_verified),
    )
