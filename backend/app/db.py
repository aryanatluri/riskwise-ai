"""Database engine and sessions.

Tenant isolation has two locks:
1. Every query in the app filters by org_id (the main lock).
2. Postgres row-level security (RLS) on every tenant table, keyed on the
   `app.current_org` setting, which we set per transaction (the second lock).
   Background jobs that legitimately span orgs set `app.bypass_rls = 'on'`.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def new_session() -> Session:
    return _session_factory()()


def set_tenant(db: Session, org_id: uuid.UUID | None) -> None:
    """Pin the current transaction to one org for RLS. Call after every commit too."""
    db.execute(
        text("SELECT set_config('app.current_org', :org, true)"),
        {"org": str(org_id) if org_id else ""},
    )


def set_bypass_rls(db: Session) -> None:
    db.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))


def get_db() -> Iterator[Session]:
    db = new_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def system_session() -> Iterator[Session]:
    """Session for jobs and webhooks that must see across orgs."""
    db = new_session()
    try:
        set_bypass_rls(db)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
