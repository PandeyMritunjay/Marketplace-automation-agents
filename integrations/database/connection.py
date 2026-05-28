from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from lighthouse.config import settings
from lighthouse.models.agent.base import Base as AgentBase


# Marketplace database (read-only)
# Support both MySQL and PostgreSQL
if settings.marketplace_db_url.startswith('mysql'):
    marketplace_engine = create_engine(settings.marketplace_db_url, pool_pre_ping=True)
else:
    marketplace_engine = create_engine(settings.marketplace_db_url)
MarketplaceSessionLocal = sessionmaker(bind=marketplace_engine)


# Agent database (read-write)
# Support both MySQL and PostgreSQL
if settings.agent_db_url.startswith('mysql'):
    agent_engine = create_engine(settings.agent_db_url, pool_pre_ping=True)
else:
    agent_engine = create_engine(settings.agent_db_url)
AgentSessionLocal = sessionmaker(bind=agent_engine)


def get_marketplace_db() -> Session:
    """Get a session for the marketplace database (read-only)."""
    session = MarketplaceSessionLocal()
    return session


def get_agent_db() -> Session:
    """Get a session for the agent database (read-write)."""
    session = AgentSessionLocal()
    return session


def init_db():
    """Initialize the agent database schema."""
    AgentBase.metadata.create_all(bind=agent_engine)
