"""
批量修复已生成内容中的诱导互动违规内容
- note.md: 删除"评论区扣【XX】"行、"关注不迷路"行、"收藏但没看"替换
- comments.txt: 删除诱导评论行 + 补充合规评论到10条
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))

# 诱导互动模式
INDUCING_PATTERNS_NOTE = [
    (r'^💬 评论区扣【.*?】，获取完整报告\s*$', ''),
    (r'^💬 评论区扣【.*?】获取完整报告\s*$', ''),
    (r'关注不迷路\s*👇\s*$', ''),
    (r'^明天开始，我会每天深度拆解1个核心模块。关注不迷路 👇\s*$',
     '明天开始，我会每天深度拆解1个核心模块。'),
    (r'收藏但没看的人', '看了但没行动的人'),
    (r'完整报告店铺搜索【.*?】即可获取。', '完整报告共15个模块，笔记下方即可获取。'),
    (r'完整报告共15个模块，笔记下方即可获取。', ''),  # 也删除获取引导
]

INDUCING_PATTERNS_COMMENTS = [
    # 诱导评论类
    r'^完整报告怎么获取？\s*$',
    r'^扣【.*?】真的能拿到报告吗？\s*$',
    r'^需要完整版，求分享\s*$',
    r'^收藏了，给.*?也看看\s*$',
    r'^收藏了，转给我.*?看\s*$',
    # 虚假证言类
    r'^拿到完整报告了，.*$',
    r'^19\.9买这份报告太值了.*$',
    r'^19\.9买这份报告，.*$',
    r'^这个目录太全了，必须拿到完整版\s*$',
    r'^完整报告拿到了，.*$',
    r'^扣【.*?】获取了，.*$',
    r'^自评表帮我做了决定，.*$',
    r'^已获取完整版，.*$',
    r'^报告里的数据表帮我避了.*$',
    r'^报告里的数据对比帮我做了决定.*$',
    r'^10天追完了，报告比10篇笔记有用.*$',
    r'^行动框架太实用了，.*$',
    r'^这种量化决策的方式太好了$',
    r'^终于有人把.*?说清楚了$',
    r'^报告里的.*?帮我.*$',
    r'^已获取.*$',
    r'^.*?太实用了$',
    r'^.*?超值$',
]

# 合规评论模板（按主题关键词替换）
COMPLIANT_COMMENTS = [
    '这个数据角度很新颖，之前没这么想过',
    '模块之间的逻辑关系梳理得很清楚',
    '这个分析框架可以套用到其他场景吗？',
    '数据来源是哪里？想进一步了解',
    '这个结论和我了解的情况有差异，可能地区不同',
    '如果条件变了，这个结论还成立吗？',
    '这个维度的对比很有参考价值',
    '有没有考虑过XX因素的影响？',
    '这个方法论背后的逻辑是什么？',
    '数据密度很高，每段都有信息量',
]

fixed_files = 0
fixed_lines = 0

for tid in os.listdir(BASE):
    xhs = os.path.join(BASE, tid, 'xiaohongshu')
    if not os.path.isdir(xhs):
        continue

    for day_dir in os.listdir(xhs):
        day_path = os.path.join(xhs, day_dir)
        if not os.path.isdir(day_path):
            continue

        # 修复 note.md
        note_path = os.path.join(day_path, 'note.md')
        if os.path.exists(note_path):
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content
            for pattern, replacement in INDUCING_PATTERNS_NOTE:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            # 清理连续空行
            content = re.sub(r'\n{3,}', '\n\n', content)
            # 清理末尾多余空行
            content = content.rstrip() + '\n'

            if content != original:
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files += 1
                fixed_lines += 1

        # 修复 comments.txt
        comments_path = os.path.join(day_path, 'comments.txt')
        if os.path.exists(comments_path):
            with open(comments_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            new_lines = []
            removed = 0
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # 修复拼接行：在"量化了"后面如果紧跟中文字符，插入换行
                stripped = re.sub(r'(量化了)([^\n])', r'\1\n\2', stripped)
                # 按换行拆分，逐条检查
                sub_lines = stripped.split('\n')
                for sub in sub_lines:
                    sub = sub.strip()
                    if not sub:
                        continue
                    is_inducing = False
                    for pattern in INDUCING_PATTERNS_COMMENTS:
                        if re.match(pattern, sub):
                            is_inducing = True
                            removed += 1
                            break
                    if not is_inducing:
                        new_lines.append(sub + '\n')

            # 补充合规评论到10条
            existing_count = len(new_lines)
            need_supplement = existing_count < 10
            if need_supplement:
                seed = hash(tid + day_dir) % len(COMPLIANT_COMMENTS)
                for i in range(10 - existing_count):
                    idx = (seed + i) % len(COMPLIANT_COMMENTS)
                    new_lines.append(COMPLIANT_COMMENTS[idx] + '\n')

            # 只要有删除、拼接修复或补充就写入
            if removed > 0 or need_supplement:
                with open(comments_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                fixed_files += 1
                fixed_lines += removed + max(0, 10 - existing_count)

            # 检查拼接行（即使没有删除也需要修复）
            has_concat = False
            with open(comments_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            if re.search(r'量化了[^\n]', raw):
                raw = re.sub(r'(量化了)([^\n])', r'\1\n\2', raw)
                # 重新整理为10行
                all_lines = [l.strip() for l in raw.split('\n') if l.strip()]
                # 去重
                seen = set()
                unique = []
                for l in all_lines:
                    if l not in seen:
                        seen.add(l)
                        unique.append(l)
                # 补充到10条
                seed = hash(tid + day_dir) % len(COMPLIANT_COMMENTS)
                while len(unique) < 10:
                    idx = (seed + len(unique)) % len(COMPLIANT_COMMENTS)
                    c = COMPLIANT_COMMENTS[idx]
                    if c not in seen:
                        unique.append(c)
                        seen.add(c)
                with open(comments_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(unique[:10]) + '\n')
                fixed_files += 1
                fixed_lines += 1

print(f'修复完成: {fixed_files} 个文件, {fixed_lines} 行被修改/删除/补充')
