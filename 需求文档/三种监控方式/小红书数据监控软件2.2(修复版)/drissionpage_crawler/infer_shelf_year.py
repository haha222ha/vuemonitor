"""
智能推断商品上架年份

逻辑：
- 如果月份 > 当前月份 → 上一年
- 如果月份 <= 当前月份 → 今年

例如当前是 2026年4月25日：
- "04月17日" → 2026年（今年4月）
- "09月20日" → 2025年（去年9月，因为今年9月还没到）
- "12月24日" → 2025年（去年12月）
- "01月09日" → 2026年（今年1月）
"""

from datetime import datetime

def infer_shelf_year(month_day_str: str, current_date: datetime = None) -> str:
    """
    根据月日字符串推断完整日期
    
    Args:
        month_day_str: 格式如 "09月20日" 或 "04月17日"
        current_date: 当前日期，默认为今天
    
    Returns:
        完整日期字符串，格式 "YYYY-MM-DD"
    """
    if current_date is None:
        current_date = datetime.now()
    
    # 解析月日
    try:
        # 提取月份和日期
        match = __import__('re').search(r'(\d{1,2})月(\d{1,2})日', month_day_str)
        if not match:
            return month_day_str  # 无法解析，返回原值
        
        month = int(match.group(1))
        day = int(match.group(2))
        
        # 推断年份
        current_year = current_date.year
        current_month = current_date.month
        
        # 如果商品月份 > 当前月份，说明是去年上架的
        if month > current_month:
            year = current_year - 1
        else:
            year = current_year
        
        # 构造完整日期
        full_date = f"{year}-{month:02d}-{day:02d}"
        return full_date
        
    except Exception as e:
        print(f"日期解析错误: {month_day_str}, 错误: {e}")
        return month_day_str


def test_infer_shelf_year():
    """测试年份推断"""
    # 假设当前日期是 2026年4月25日
    current = datetime(2026, 4, 25)
    
    test_cases = [
        "04月17日",  # 应该是 2026-04-17
        "09月20日",  # 应该是 2025-09-20
        "12月24日",  # 应该是 2025-12-24
        "01月09日",  # 应该是 2026-01-09
        "03月01日",  # 应该是 2026-03-01
        "11月15日",  # 应该是 2025-11-15
    ]
    
    print("📅 年份推断测试")
    print("=" * 60)
    print(f"当前日期: {current.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    for md in test_cases:
        full_date = infer_shelf_year(md, current)
        print(f"  {md} → {full_date}")


if __name__ == '__main__':
    test_infer_shelf_year()
