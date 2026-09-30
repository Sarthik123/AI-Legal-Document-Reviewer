from datetime import datetime, timedelta
import hashlib
import logging
import os
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    EmailAddressRequest,
    EmailTokenRequest,
    MessageResponse,
    PasswordResetConfirm,
    RegistrationResponse,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.email_service import (
    EmailDeliveryError,
    app_base_url,
    send_email,
)
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

EMAIL_VERIFICATION_HOURS = 24
PASSWORD_RESET_MINUTES = 30
EMAIL_VERIFICATION_ENABLED = (
    os.getenv("EMAIL_VERIFICATION_ENABLED", "true").strip().lower()
    not in {"0", "false", "no", "off"}
)
PASSWORD_RESET_ENABLED = (
    os.getenv("PASSWORD_RESET_ENABLED", "false").strip().lower()
    not in {"0", "false", "no", "off"}
)


def _new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def _send_verification_email(email: str, token: str) -> None:
    verification_url = (
        f"{app_base_url()}/verify-email?token={token}"
    )
    send_email(
        recipient=email,
        subject="Verify your AI Legal Document Reviewer account",
        body=(
            "Confirm your email address to finish creating your account.\n\n"
            f"Open this link within {EMAIL_VERIFICATION_HOURS} hours:\n"
            f"{verification_url}\n\n"
            "If you did not create this account, you can ignore this email."
        ),
    )


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists.",
        )

    user = User(
        id=str(uuid4()),
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        email_verified=not EMAIL_VERIFICATION_ENABLED,
    )

    verification_token = None
    if EMAIL_VERIFICATION_ENABLED:
        verification_token, token_hash = _new_token()
        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = (
            datetime.utcnow()
            + timedelta(hours=EMAIL_VERIFICATION_HOURS)
        )

    db.add(user)
    db.commit()

    if EMAIL_VERIFICATION_ENABLED:
        try:
            _send_verification_email(user.email, verification_token)
        except EmailDeliveryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Your account was created, but the verification email "
                    "could not be sent. Please use the resend-verification "
                    "option after email delivery is configured."
                ),
            ) from error

    return {
        "message": (
            "Account created. Check your email to verify it."
            if EMAIL_VERIFICATION_ENABLED
            else "Account created. You can now log in."
        ),
        "verification_required": EMAIL_VERIFICATION_ENABLED,
    }


@router.post("/token", response_model=Token)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == form_data.username)
        .first()
    )

    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if EMAIL_VERIFICATION_ENABLED and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    request: EmailTokenRequest,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
    user = (
        db.query(User)
        .filter(User.email_verification_token_hash == token_hash)
        .first()
    )

    if (
        not user
        or not user.email_verification_expires_at
        or user.email_verification_expires_at < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link is invalid or expired.",
        )

    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.commit()

    return {"message": "Email verified. You can now log in."}


@router.post("/verification/request", response_model=MessageResponse)
def request_verification_email(
    request: EmailAddressRequest,
    db: Session = Depends(get_db),
):
    if not EMAIL_VERIFICATION_ENABLED:
        return {"message": "Email verification is not required right now."}

    user = db.query(User).filter(User.email == request.email).first()

    if user and not user.email_verified:
        token, token_hash = _new_token()
        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = (
            datetime.utcnow()
            + timedelta(hours=EMAIL_VERIFICATION_HOURS)
        )
        db.commit()

        try:
            _send_verification_email(user.email, token)
        except EmailDeliveryError:
            # Keep the same response for existing and unknown addresses.
            pass

    return {
        "message": "If the account needs verification, an email will be sent."
    }


@router.post("/password-reset/request", response_model=MessageResponse)
def request_password_reset(
    request: EmailAddressRequest,
    db: Session = Depends(get_db),
):
    if not PASSWORD_RESET_ENABLED:
        return {"message": "Password reset is temporarily unavailable. Please try again later."}

    user = db.query(User).filter(User.email == request.email).first()

    if user and (user.email_verified or not EMAIL_VERIFICATION_ENABLED):
        token, token_hash = _new_token()
        user.password_reset_token_hash = token_hash
        user.password_reset_expires_at = (
            datetime.utcnow()
            + timedelta(minutes=PASSWORD_RESET_MINUTES)
        )
        db.commit()

        reset_url = f"{app_base_url()}/reset-password?token={token}"

        try:
            send_email(
                recipient=user.email,
                subject="Reset your AI Legal Document Reviewer password",
                body=(
                    "A password reset was requested for your account.\n\n"
                    f"Choose a new password within {PASSWORD_RESET_MINUTES} minutes:\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
            )
        except EmailDeliveryError as error:
            # Do not reveal whether an account exists through this endpoint.
            logger.warning("Password reset email delivery failed: %s", error)

    return {
        "message": "If an account exists for that address, a reset email will be sent."
    }


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    if not PASSWORD_RESET_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset is temporarily unavailable. Please try again later.",
        )

    token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
    user = (
        db.query(User)
        .filter(User.password_reset_token_hash == token_hash)
        .first()
    )

    if (
        not user
        or not user.password_reset_expires_at
        or user.password_reset_expires_at < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or expired.",
        )

    user.hashed_password = hash_password(request.password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    db.commit()

    return {"message": "Password updated. You can now log in."}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise credentials_exception

    return user


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
