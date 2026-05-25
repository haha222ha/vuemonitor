import sqlite3
import os

db_path = r"D:\小红书数据库\xhs_burst_monitor_backup.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

TBL = "backup_goods"

print(f"=== Sample Data: {TBL} (first 3) ===")
cursor.execute(f"SELECT * FROM [{TBL}] LIMIT 3")
rows = cursor.fetchall()
cursor.execute(f"PRAGMA table_info([{TBL}])")
cols = cursor.fetchall()
col_names = [c[1] for c in cols]
print(f"  Columns: {col_names}")
for row in rows:
    for i, col in enumerate(col_names):
        val = str(row[i])[:80]
        print(f"    {col:20s} = {val}")
    print()

print("=== Data Distribution ===")
cursor.execute("""
    SELECT 
        CASE 
            WHEN deal_price < 10 THEN '0-10'
            WHEN deal_price < 50 THEN '10-50'
            WHEN deal_price < 100 THEN '50-100'
            WHEN deal_price < 500 THEN '100-500'
            ELSE '500+'
        END as price_range,
        COUNT(*) as cnt
    FROM backup_goods 
    WHERE deal_price IS NOT NULL AND deal_price > 0
    GROUP BY price_range
    ORDER BY MIN(deal_price)
""")
print("  Price distribution:")
for row in cursor.fetchall():
    print(f"    {row[0]:15s} {row[1]:>8,}")

cursor.execute(f"SELECT COUNT(DISTINCT store_id) FROM [{TBL}] WHERE store_id IS NOT NULL AND store_id != ''")
print(f"\n  Unique stores: {cursor.fetchone()[0]:,}")

cursor.execute(f"SELECT COUNT(DISTINCT keyword) FROM [{TBL}] WHERE keyword IS NOT NULL AND keyword != ''")
print(f"  Unique keywords: {cursor.fetchone()[0]:,}")

cursor.execute(f"SELECT COUNT(*) FROM [{TBL}] WHERE sold_num > 0")
print(f"  Goods with sales > 0: {cursor.fetchone()[0]:,}")

cursor.execute(f"SELECT COUNT(*) FROM [{TBL}] WHERE sold_num > 100")
print(f"  Goods with sales > 100: {cursor.fetchone()[0]:,}")

cursor.execute(f"SELECT COUNT(*) FROM [{TBL}] WHERE sold_num > 1000")
print(f"  Goods with sales > 1000: {cursor.fetchone()[0]:,}")

cursor.execute(f"SELECT COUNT(*) FROM [{TBL}] WHERE sold_num > 10000")
print(f"  Goods with sales > 10000: {cursor.fetchone()[0]:,}")

print("\n=== Top 20 Keywords by count ===")
cursor.execute(f"""
    SELECT keyword, COUNT(*) as cnt 
    FROM [{TBL}] 
    WHERE keyword IS NOT NULL AND keyword != ''
    GROUP BY keyword 
    ORDER BY cnt DESC 
    LIMIT 20
""")
for row in cursor.fetchall():
    print(f"  {row[0]:30s} {row[1]:>8,}")

print("\n=== Top 20 Stores by goods count ===")
cursor.execute(f"""
    SELECT store_name, COUNT(*) as cnt, SUM(sold_num) as total_sold
    FROM [{TBL}] 
    WHERE store_name IS NOT NULL AND store_name != ''
    GROUP BY store_name 
    ORDER BY cnt DESC 
    LIMIT 20
""")
for row in cursor.fetchall():
    print(f"  {row[0]:30s} goods={row[1]:>6,}  sold={row[2]:>10,}")

print("\n=== filter_result distribution ===")
cursor.execute(f"SELECT filter_result, COUNT(*) FROM [{TBL}] GROUP BY filter_result ORDER BY filter_result")
for row in cursor.fetchall():
    print(f"  filter_result={row[0]:>5}  count={row[1]:>10,}")

print("\n=== filter_tag distribution (top 20) ===")
cursor.execute(f"SELECT filter_tag, COUNT(*) FROM [{TBL}] WHERE filter_tag IS NOT NULL AND filter_tag != '' GROUP BY filter_tag ORDER BY COUNT(*) DESC LIMIT 20")
for row in cursor.fetchall():
    print(f"  {str(row[0]):30s} {row[1]:>10,}")

print("\n=== shelf_time range ===")
cursor.execute(f"SELECT MIN(shelf_time), MAX(shelf_time) FROM [{TBL}] WHERE shelf_time IS NOT NULL AND shelf_time != ''")
row = cursor.fetchone()
print(f"  From: {row[0]}  To: {row[1]}")

print("\n=== scan_count distribution ===")
cursor.execute(f"""
    SELECT 
        CASE 
            WHEN scan_count = 1 THEN '1'
            WHEN scan_count BETWEEN 2 AND 5 THEN '2-5'
            WHEN scan_count BETWEEN 6 AND 20 THEN '6-20'
            WHEN scan_count > 20 THEN '20+'
        END as scan_group,
        COUNT(*) as cnt
    FROM [{TBL}]
    GROUP BY scan_group
    ORDER BY MIN(scan_count)
""")
for row in cursor.fetchall():
    print(f"  scan_count {row[0]:10s} {row[1]:>10,}")

conn.close()
