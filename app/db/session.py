from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

# Convert DATABASE_URL to async format (sqlite+aiosqlite:// or postgresql+asyncpg://)
DATABASE_URL = settings.DATABASE_URL.replace(
    "sqlite://", "sqlite+aiosqlite://"
).replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        yield session
