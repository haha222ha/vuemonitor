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
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))

        import app.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_rankings (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                category VARCHAR(100),
                price_percentile FLOAT,
                sales_percentile FLOAT,
                rating_percentile FLOAT,
                overall_rank INTEGER,
                category_rank INTEGER,
                category_total INTEGER,
                lifecycle_stage VARCHAR(20),
                trend_short VARCHAR(10),
                trend_long VARCHAR(10),
                sales_velocity FLOAT,
                growth_rate_7d FLOAT,
                growth_rate_30d FLOAT,
                volatility FLOAT,
                competition_index FLOAT,
                calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_product_rankings_product_unique
            ON product_rankings(product_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_product_rankings_product_id ON product_rankings(product_id)
        """))

        result = await conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        table_count = result.scalar()
        logger.info(f"Database initialized with {table_count} tables")


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
