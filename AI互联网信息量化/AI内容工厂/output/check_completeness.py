"""检查所有选题的文件完整性"""
import os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)))
TIDS = [f'T20260520{i:03d}' for i in range(1, 11)]

issues = []
for tid in TIDS:
    for day in range(1, 11):
        day_dir = os.path.join(BASE, tid, 'xiaohongshu', f'Day{day}')
        if not os.path.exists(day_dir):
            issues.append(f'{tid}/Day{day} 目录缺失')
            continue

        # 检查4个核心文件
        for f in ['title.txt', 'note.md', 'comments.txt', 'cover.png']:
            p = os.path.join(day_dir, f)
            if not os.path.exists(p):
                issues.append(f'{tid}/Day{day}/{f} 缺失')
            elif os.path.getsize(p) == 0:
                issues.append(f'{tid}/Day{day}/{f} 空文件')

        # 检查title.txt内容过短
        tp = os.path.join(day_dir, 'title.txt')
        if os.path.exists(tp) and os.path.getsize(tp) < 5:
            issues.append(f'{tid}/Day{day}/title.txt 内容过短({os.path.getsize(tp)}B)')

        # 检查note.md内容过短
        np = os.path.join(day_dir, 'note.md')
        if os.path.exists(np) and os.path.getsize(np) < 500:
            issues.append(f'{tid}/Day{day}/note.md 内容过短({os.path.getsize(np)}B)')

        # 检查内容图
        has_images = any(
            os.path.exists(os.path.join(day_dir, f'image_0{i}.png'))
            for i in range(1, 6)
        )
        if not has_images:
            issues.append(f'{tid}/Day{day} 缺少内容图(image_01~05.png)')

print(f'共发现 {len(issues)} 个问题:')
for issue in issues:
    print(f'  {issue}')
