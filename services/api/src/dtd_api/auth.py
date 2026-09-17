import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from dtd_api.contracts import Contract
from dtd_api.database import database
from dtd_api.errors import ApiError
from dtd_api.models import AuditEvent, LoginTicket, User, WebSession, now

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
DB = Annotated[Session, Depends(database)]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(token: str) -> str:
    return digest("csrf:" + token)


def cookie_name(request: Request) -> str:
    return (
        "__Host-dtd_session"
        if request.app.state.settings.app_origin.startswith("https:")
        else "dtd_local_session"
    )


def require_origin(request: Request) -> None:
    if request.headers.get("origin") != request.app.state.settings.app_origin:
        raise ApiError(403, "ORIGIN_REJECTED", "The request origin is not allowed.")


class Exchange(Contract):
    token: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]+$")


class SessionInfo(Contract):
    user_id: str
    csrf_token: str


@dataclass
class Principal:
    user: User
    token: str
    csrf_hash: str


def authenticated(request: Request, db: DB) -> Principal:
    token = request.cookies.get(cookie_name(request), "")
    if len(token) != 43:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue.")
    result = db.execute(
        select(User, WebSession.csrf_hash)
        .join(WebSession, WebSession.user_id == User.id)
        .where(
            WebSession.token_hash == digest(token),
            WebSession.expires_at > now(),
            User.active.is_(True),
        )
    ).one_or_none()
    if result is None:
        raise ApiError(401, "UNAUTHENTICATED", "The session is invalid or expired.")
    return Principal(result[0], token, result[1])


AUTH = Annotated[Principal, Depends(authenticated)]


def mutation(request: Request, principal: AUTH) -> Principal:
    require_origin(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not secrets.compare_digest(digest(supplied), principal.csrf_hash):
        raise ApiError(403, "CSRF_REJECTED", "A valid session CSRF token is required.")
    return principal


MUTATION = Annotated[Principal, Depends(mutation)]


def issue_ticket(db: Session, subject: str) -> str:
    """Operator-only entry point, never exposed as a public route."""
    subject = subject.strip()
    if not subject or len(subject) > 180:
        raise ValueError("Subject must contain 1–180 characters")
    subject = "local:" + subject
    user = db.scalar(select(User).where(User.auth_subject == subject))
    if user is None:
        user = User(auth_subject=subject)
        db.add(user)
        db.flush()
    if not user.active:
        raise ValueError("User is disabled")
    # Only the newest unconsumed ticket for this user is valid.
    db.execute(delete(LoginTicket).where(LoginTicket.user_id == user.id))
    token = secrets.token_urlsafe(32)
    db.add(
        LoginTicket(
            token_hash=digest(token), user_id=user.id, expires_at=now() + timedelta(minutes=5)
        )
    )
    db.commit()
    return token


@router.post("/exchange", response_model=SessionInfo)
def exchange(body: Exchange, request: Request, response: Response, db: DB) -> SessionInfo:
    require_origin(request)
    user_id = db.scalar(
        delete(LoginTicket)
        .where(
            LoginTicket.token_hash == digest(body.token),
            LoginTicket.expires_at > now(),
        )
        .returning(LoginTicket.user_id)
    )
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.active:
        raise ApiError(401, "INVALID_TICKET", "The sign-in token is invalid or expired.")
    old = request.cookies.get(cookie_name(request), "")
    if old:
        db.execute(delete(WebSession).where(WebSession.token_hash == digest(old)))
    token = secrets.token_urlsafe(32)
    db.add(
        WebSession(
            token_hash=digest(token),
            user_id=user.id,
            csrf_hash=digest(csrf_for(token)),
            expires_at=now() + timedelta(hours=8),
        )
    )
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="session.created",
            resource_id=user.id,
            request_id=request.state.request_id,
        )
    )
    db.commit()
    response.set_cookie(
        cookie_name(request),
        token,
        max_age=8 * 3600,
        httponly=True,
        secure=request.app.state.settings.app_origin.startswith("https:"),
        samesite="strict",
        path="/",
    )
    return SessionInfo(user_id=user.id, csrf_token=csrf_for(token))


@router.get("/session", response_model=SessionInfo)
def session_info(principal: AUTH) -> SessionInfo:
    return SessionInfo(user_id=principal.user.id, csrf_token=csrf_for(principal.token))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, principal: MUTATION, db: DB) -> None:
    db.execute(delete(WebSession).where(WebSession.token_hash == digest(principal.token)))
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="session.revoked",
            resource_id=principal.user.id,
            request_id=request.state.request_id,
        )
    )
    db.commit()
    response.delete_cookie(
        cookie_name(request),
        path="/",
        httponly=True,
        samesite="strict",
        secure=request.app.state.settings.app_origin.startswith("https:"),
    )
