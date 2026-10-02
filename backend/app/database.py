import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://sarthikbhan@localhost:5432/ai_legal_reviewer",
)

# Neon and many hosted PostgreSQL providers expose a generic `postgresql://`
# URL. SQLAlchemy otherwise selects the unavailable psycopg2 driver for that
# scheme, while this project intentionally installs psycopg (v3).
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgresql://")

engine = create_engine(
    DATABASE_URL,
    # Keep at least one connection available for API status requests while a
    # background document worker is processing a long PDF.
    pool_size=int(os.getenv("DB_POOL_SIZE", "2")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
