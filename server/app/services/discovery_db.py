import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_POOL_SIZE = 3
_INDEX_DEFINITIONS = [
    ("idx_backup_goods_title", "CREATE INDEX IF NOT EXISTS idx_backup_goods_title ON backup_goods(title)"),
    ("idx_backup_goods_store_name", "CREATE INDEX IF NOT EXISTS idx_backup_goods_store_name ON backup_goods(store_name)"),
    ("idx_backup_goods_keyword", "CREATE INDEX IF NOT EXISTS idx_backup_goods_keyword ON backup_goods(keyword)"),
    ("idx_backup_goods_store_id", "CREATE INDEX IF NOT EXISTS idx_backup_goods_store_id ON backup_goods(store_id)"),
    ("idx_backup_goods_sold_num", "CREATE INDEX IF NOT EXISTS idx_backup_goods_sold_num ON backup_goods(sold_num)"),
]


class DiscoveryDatabase:
    _instance: "DiscoveryDatabase | None" = None
    _db_path: str | None = None
    _pool: list[aiosqlite.Connection] = []
    _semaphore: asyncio.Semaphore | None = None
    _initialized: bool = False

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._pool: list[aiosqlite.Connection] = []
        self._semaphore = asyncio.Semaphore(_POOL_SIZE)

    @classmethod
    def get_instance(cls) -> "DiscoveryDatabase | None":
        return cls._instance

    @classmethod
    def initialize(cls, db_path: str) -> "DiscoveryDatabase":
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    async def _create_connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self._db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA cache_size = -64000")
        await conn.execute("PRAGMA temp_store = MEMORY")
        await conn.execute("PRAGMA query_only = ON")
        return conn

    async def _ensure_indexes(self, conn: aiosqlite.Connection) -> None:
        existing_indexes = set()
        try:
            async with conn.execute("PRAGMA index_list(backup_goods)") as cursor:
                rows = await cursor.fetchall()
                existing_indexes = {row[1] for row in rows}
        except Exception as e:
            logger.warning(f"Failed to list existing indexes: {e}")
            return

        for idx_name, idx_sql in _INDEX_DEFINITIONS:
            if idx_name not in existing_indexes:
                try:
                    temp_conn = await aiosqlite.connect(self._db_path)
                    try:
                        await temp_conn.execute(idx_sql)
                        await temp_conn.commit()
                        logger.info(f"Created index: {idx_name}")
                    finally:
                        await temp_conn.close()
                except Exception as e:
                    logger.warning(f"Failed to create index {idx_name}: {e}")

    async def connect(self) -> None:
        if self._initialized or not self._db_path or not os.path.exists(self._db_path):
            logger.warning(f"Discovery DB not found at {self._db_path}")
            return

        try:
            probe_conn = await aiosqlite.connect(self._db_path)
            await self._ensure_indexes(probe_conn)
            await probe_conn.close()
        except Exception as e:
            logger.warning(f"Index check failed: {e}")

        for _ in range(_POOL_SIZE):
            try:
                conn = await self._create_connection()
                self._pool.append(conn)
            except Exception as e:
                logger.error(f"Failed to create discovery DB connection: {e}")

        if self._pool:
            self._initialized = True
            logger.info(f"Discovery DB connected with pool size {len(self._pool)}: {self._db_path}")
        else:
            logger.error("Discovery DB: no connections available")

    @asynccontextmanager
    async def _acquire(self):
        if not self._pool:
            yield None
            return
        async with self._semaphore:
            conn = self._pool.pop()
            try:
                yield conn
            finally:
                self._pool.append(conn)

    async def close(self) -> None:
        for conn in self._pool:
            try:
                await conn.close()
            except Exception:
                logger.warning("Silent exception")
        self._pool.clear()
        self._initialized = False

    async def reload(self) -> None:
        await self.close()
        await self.connect()

    async def search_goods(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        min_price: float | None = None,
        max_price: float | None = None,
        min_sold: int | None = None,
        store_id: str | None = None,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        category: str | None = None,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            conditions = []
            params: list[Any] = []

            if keyword:
                conditions.append("(title LIKE ? OR keyword LIKE ? OR goods_id = ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%", keyword])

            if min_price is not None:
                conditions.append("deal_price >= ?")
                params.append(min_price)

            if max_price is not None:
                conditions.append("deal_price <= ?")
                params.append(max_price)

            if min_sold is not None:
                conditions.append("sold_num >= ?")
                params.append(min_sold)

            if store_id:
                conditions.append("store_id = ?")
                params.append(store_id)

            if category:
                conditions.append("keyword = ?")
                params.append(category)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            count_sql = f"SELECT COUNT(*) FROM backup_goods WHERE {where_clause}"
            async with conn.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            sort_mapping = {
                "relevance": None,
                "price_asc": "deal_price ASC",
                "price_desc": "deal_price DESC",
                "sales_desc": "sold_num DESC",
                "sales_asc": "sold_num ASC",
            }
            order_clause = sort_mapping.get(sort_by)
            if sort_by == "relevance" and keyword:
                order_clause = None
            if not order_clause:
                order_clause = "sold_num DESC"

            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT goods_id, title, store_name, store_id,
                       deal_price, sold_num, keyword
                FROM backup_goods
                WHERE {where_clause}
                ORDER BY {order_clause}
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "goods_id": row["goods_id"],
                    "title": row["title"] or "",
                    "store_name": row["store_name"] or "",
                    "store_id": row["store_id"] or "",
                    "deal_price": row["deal_price"],
                    "sold_num": row["sold_num"],
                    "keyword": row["keyword"] or "",
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_top_sold(
        self,
        page: int = 1,
        page_size: int = 20,
        min_sold: int = 1000,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            count_sql = "SELECT COUNT(*) FROM backup_goods WHERE sold_num >= ?"
            async with conn.execute(count_sql, [min_sold]) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = """
                SELECT goods_id, title, store_name, store_id,
                       deal_price, sold_num, keyword, shelf_time
                FROM backup_goods
                WHERE sold_num >= ?
                ORDER BY sold_num DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, [min_sold, page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "goods_id": row["goods_id"],
                    "title": row["title"] or "",
                    "store_name": row["store_name"] or "",
                    "store_id": row["store_id"] or "",
                    "deal_price": row["deal_price"],
                    "sold_num": row["sold_num"],
                    "keyword": row["keyword"] or "",
                    "shelf_time": row["shelf_time"] or "",
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def search_stores(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            params = [f"%{keyword}%"]
            count_sql = """
                SELECT COUNT(*) FROM (
                    SELECT store_id FROM backup_goods
                    WHERE store_name LIKE ? AND store_id IS NOT NULL AND store_id != ''
                    GROUP BY store_id
                )
            """
            async with conn.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = """
                SELECT store_id, store_name,
                       COUNT(*) as product_count,
                       SUM(COALESCE(sold_num, 0)) as total_sold,
                       AVG(COALESCE(deal_price, 0)) as avg_price
                FROM backup_goods
                WHERE store_name LIKE ? AND store_id IS NOT NULL AND store_id != ''
                GROUP BY store_id
                ORDER BY product_count DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "store_id": row["store_id"],
                    "store_name": row["store_name"],
                    "product_count": row["product_count"],
                    "total_sold": row["total_sold"],
                    "avg_price": round(row["avg_price"], 2) if row["avg_price"] else None,
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_store_goods(
        self,
        store_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            count_sql = "SELECT COUNT(*) FROM backup_goods WHERE store_id = ?"
            async with conn.execute(count_sql, [store_id]) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = """
                SELECT goods_id, title, store_name, store_id,
                       deal_price, sold_num, keyword
                FROM backup_goods WHERE store_id = ?
                ORDER BY sold_num DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, [store_id, page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "goods_id": row["goods_id"],
                    "title": row["title"] or "",
                    "store_name": row["store_name"] or "",
                    "store_id": row["store_id"] or "",
                    "deal_price": row["deal_price"],
                    "sold_num": row["sold_num"],
                    "keyword": row["keyword"] or "",
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_hot_keywords(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            count_sql = "SELECT COUNT(DISTINCT keyword) FROM backup_goods WHERE keyword IS NOT NULL AND keyword NOT IN ('web_store', '')"
            async with conn.execute(count_sql) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = """
                SELECT keyword, COUNT(*) as item_count
                FROM backup_goods
                WHERE keyword IS NOT NULL AND keyword NOT IN ('web_store', '')
                GROUP BY keyword
                ORDER BY item_count DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, [page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = [{"keyword": row["keyword"], "item_count": row["item_count"]} for row in rows]
            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_hot_goods(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            conditions = ["sold_num IS NOT NULL", "sold_num > 0"]
            params: list[Any] = []

            if category:
                conditions.append("keyword = ?")
                params.append(category)

            where_clause = " AND ".join(conditions)

            count_sql = f"SELECT COUNT(*) FROM backup_goods WHERE {where_clause}"
            async with conn.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT goods_id, title, store_name, store_id,
                       deal_price, sold_num, keyword
                FROM backup_goods
                WHERE {where_clause}
                ORDER BY sold_num DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "goods_id": row["goods_id"],
                    "title": row["title"] or "",
                    "store_name": row["store_name"] or "",
                    "store_id": row["store_id"] or "",
                    "deal_price": row["deal_price"],
                    "sold_num": row["sold_num"],
                    "keyword": row["keyword"] or "",
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_rising_goods(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            conditions = ["sold_num IS NOT NULL", "sold_num > 100"]
            params: list[Any] = []

            if category:
                conditions.append("keyword = ?")
                params.append(category)

            where_clause = " AND ".join(conditions)

            count_sql = f"SELECT COUNT(*) FROM backup_goods WHERE {where_clause}"
            async with conn.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT goods_id, title, store_name, store_id,
                       deal_price, sold_num, keyword
                FROM backup_goods
                WHERE {where_clause}
                ORDER BY sold_num DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "goods_id": row["goods_id"],
                    "title": row["title"] or "",
                    "store_name": row["store_name"] or "",
                    "store_id": row["store_id"] or "",
                    "deal_price": row["deal_price"],
                    "sold_num": row["sold_num"],
                    "keyword": row["keyword"] or "",
                    "growth_rate": None,
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_new_goods(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"items": [], "total": 0}

            conditions = ["sold_num IS NOT NULL", "sold_num >= 0"]
            params: list[Any] = []

            if category:
                conditions.append("keyword = ?")
                params.append(category)

            where_clause = " AND ".join(conditions)

            count_sql = f"SELECT COUNT(*) FROM backup_goods WHERE {where_clause}"
            async with conn.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT goods_id, title, store_name, store_id,
                       deal_price, sold_num, keyword
                FROM backup_goods
                WHERE {where_clause}
                ORDER BY ROWID DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(data_sql, params + [page_size, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                items.append({
                    "goods_id": row["goods_id"],
                    "title": row["title"] or "",
                    "store_name": row["store_name"] or "",
                    "store_id": row["store_id"] or "",
                    "deal_price": row["deal_price"],
                    "sold_num": row["sold_num"],
                    "keyword": row["keyword"] or "",
                })

            return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_stats(self) -> dict[str, Any]:
        async with self._acquire() as conn:
            if not conn:
                return {"total_goods": 0, "total_stores": 0, "total_keywords": 0}

            try:
                async with conn.execute("SELECT COUNT(*) FROM backup_goods") as cursor:
                    total_goods = (await cursor.fetchone())[0]

                async with conn.execute(
                    "SELECT COUNT(DISTINCT store_id) FROM backup_goods WHERE store_id IS NOT NULL AND store_id != ''"
                ) as cursor:
                    total_stores = (await cursor.fetchone())[0]

                async with conn.execute(
                    "SELECT COUNT(DISTINCT keyword) FROM backup_goods WHERE keyword IS NOT NULL AND keyword NOT IN ('web_store', '')"
                ) as cursor:
                    total_keywords = (await cursor.fetchone())[0]

                return {
                    "total_goods": total_goods,
                    "total_stores": total_stores,
                    "total_keywords": total_keywords,
                }
            except Exception as e:
                logger.error(f"Discovery DB get_stats failed: {e}")
                return {"total_goods": 0, "total_stores": 0, "total_keywords": 0}


discovery_db = DiscoveryDatabase.__new__(DiscoveryDatabase)
discovery_db._pool = []
discovery_db._db_path = None
discovery_db._semaphore = None
discovery_db._initialized = False
