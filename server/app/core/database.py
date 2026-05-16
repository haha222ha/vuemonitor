import logging
import time
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30,
    connect_args={
        "command_timeout": 60,
        "server_settings": {
            "application_name": "vuemonitor",
            "jit": "off",
        },
    },
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

_slow_query_threshold = 2.0


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    elapsed = time.time() - getattr(context, "_query_start_time", time.time())
    if elapsed > _slow_query_threshold:
        logger.warning(
            f"Slow query detected ({elapsed:.2f}s): {statement[:200]}..."
        )


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        table_count = result.scalar()
        if table_count == 0:
            logger.info("No tables found, creating database schema...")
            await conn.run_sync(Base.metadata.create_all)
        else:
            logger.info(f"Database already has {table_count} tables, skipping create_all")


async def get_pool_stats() -> dict:
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalidated": pool.invalidated,
    }


async def health_check() -> dict:
    try:
        async with async_session_factory() as session:
            start = time.time()
            await session.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000

        pool_stats = await get_pool_stats()
        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "pool": pool_stats,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
