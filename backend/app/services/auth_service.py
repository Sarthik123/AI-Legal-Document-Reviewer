from datetime import datetime, timedelta, timezone
import os

import jwt
from dotenv import load_dotenv

load_dotenv()
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "exp": expire,
    }

    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    return jwt.decode(
        token,
        secret_key,
        algorithms=[ALGORITHM],
    )