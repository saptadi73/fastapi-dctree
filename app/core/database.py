from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


async def get_db_session():
    async with SessionLocal() as session:
        yield session


async def check_database_connection() -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True
