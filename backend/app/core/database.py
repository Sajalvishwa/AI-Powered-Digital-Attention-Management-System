"""SQLAlchemy engine, session and Base."""
import uuid
from collections.abc import Generator

from sqlalchemy import DateTime, create_engine, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

TIMESTAMPTZ = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


def uuid_pk():
    """UUID primary key (python-side uuid4 + postgres gen_random_uuid fallback)."""
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def created_at_col():
    return mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
