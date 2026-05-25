"""验证T20260522001和T20260522002的内容完整性"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
issues = []

for tid in ['T20260522001', 'T20260522002']:
    for day in range(1, 11):
        d = os.path.join(BASE, tid, 'xiaohongshu', f'Day{day}')
        if not os.path.exists(d):
            issues.append(f'{tid}/Day{day} 目录缺失')
            continue
        for f in ['title.txt', 'note.md', 'comments.txt', 'cover.png']:
            p = os.path.join(d, f)
            if not os.path.exists(p):
                issues.append(f'{tid}/Day{day}/{f} 缺失')
            elif os.path.getsize(p) == 0:
                issues.append(f'{tid}/Day{day}/{f} 空文件')

        note_path = os.path.join(d, 'note.md')
        if os.path.exists(note_path) and os.path.getsize(note_path) < 1500:
            issues.append(f'{tid}/Day{day}/note.md 过短({os.path.getsize(note_path)}B)')

        imgs = sum(1 for i in range(1, 6) if os.path.exists(os.path.join(d, f'image_0{i}.png')))
        if imgs < 5:
            issues.append(f'{tid}/Day{day} 内容图不足({imgs}/5)')

    manifest_path = os.path.join(BASE, tid, 'manifest.json')
    if not os.path.exists(manifest_path):
        issues.append(f'{tid}/manifest.json 缺失')

if issues:
    print(f'发现 {len(issues)} 个问题:')
    for i in issues:
        print(f'  {i}')
else:
    print('✅ 全部通过！2个选题×10天×8文件 = 160个文件完整')
    for tid in ['T20260522001', 'T20260522002']:
        sizes = []
        for day in range(1, 11):
            np = os.path.join(BASE, tid, 'xiaohongshu', f'Day{day}', 'note.md')
            sizes.append(os.path.getsize(np))
        print(f'{tid}: note.md min={min(sizes)}B max={max(sizes)}B avg={sum(sizes)//len(sizes)}B')
