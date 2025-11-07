"""SQLAlchemy session and engine helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def get_mysql_url() -> str:
    override = os.getenv("DATABASE_URL")
    if override:
        return override

    host = os.getenv("MYSQL_HOST", "43.138.191.40")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "gov-agent")
    password = os.getenv("MYSQL_PASSWORD", "3fzpRmB4JyBbHG6L")
    database = os.getenv("MYSQL_DB", "gov-agent")

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


if __name__ == "__main__":
    from .session import ensure_engine
    import argparse

    parser = argparse.ArgumentParser(description="Database session util")
    parser.add_argument("--init", action="store_true", help="Initialize tables")
    parser.add_argument("--echo", action="store_true", help="Enable SQL echo")
    args = parser.parse_args()

    if args.init:
        ensure_engine(echo=args.echo)
        print("Tables created")


def ensure_engine(echo: bool = False) -> Engine:
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE is None:
        url = get_mysql_url()
        _ENGINE = create_engine(url, echo=echo, pool_pre_ping=True, pool_recycle=1800)
        _SESSION_FACTORY = sessionmaker(bind=_ENGINE, expire_on_commit=False)
        Base.metadata.create_all(_ENGINE)
    return _ENGINE


def get_session() -> Session:
    ensure_engine()
    assert _SESSION_FACTORY is not None
    return _SESSION_FACTORY()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
