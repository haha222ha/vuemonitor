"""
批量改造0522选题小红书内容的标题
将"决策框架"等旧关键词替换为新标题体系
- A层: 决策框架→路径推演, 决策报告→路径推演报告
- B层: 决策框架→适配诊断, 决策报告→适配诊断报告
- C层: 决策框架→方案适配, 决策报告→方案适配报告
- D层: 决策框架→机会扫描, 决策报告→机会扫描报告
"""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))

# 选题→层级映射
TOPIC_LAYER = {
    'T20260522001': 'A',  # 防晒霜（之前的选题，A层）
    'T20260522002': 'A',  # 读博
    'T20260522003': 'A',  # 考研控制vs电气
    'T20260522004': 'C',  # 中班拼音
    'T20260522005': 'B',  # SU vs 3Dmax
    'T20260522006': 'B',  # AI绘画工具
    'T20260522007': 'B',  # Pr vs 剪映
    'T20260522008': 'C',  # 小学教辅
    'T20260522009': 'C',  # iPad笔记App
    'T20260522010': 'D',  # 小红书vs B站
}

# 层级→替换词映射
LAYER_REPLACEMENTS = {
    'A': {
        '决策框架': '路径推演',
        '决策报告': 'PathFinder™路径推演报告',
        '决策自评表': '路径推演自评表',
        '方向决策自评表': 'PathFinder™路径推演自评表',
        '决策评估框架': 'PathFinder™路径评估框架',
        '5维度决策框架': 'PathFinder™ 5维路径推演',
        '行动框架': 'PathFinder™行动框架',
    },
    'B': {
        '决策框架': '适配诊断',
        '决策报告': 'SkillRadar™适配诊断报告',
        '决策自评表': '适配诊断自评表',
        '软件选择自评表': 'SkillRadar™适配诊断自评表',
        '工具选择自评表': 'SkillRadar™适配诊断自评表',
        '决策评估框架': 'SkillRadar™适配评估框架',
        '5维度决策框架': 'SkillRadar™ 5维适配诊断',
    },
    'C': {
        '决策框架': '方案适配',
        '决策报告': 'LifeCompass™方案适配报告',
        '决策自评表': '方案适配自评表',
        '拼音决策自评表': 'LifeCompass™方案适配自评表',
        '教辅选择自评表': 'LifeCompass™方案适配自评表',
        'App选择自评表': 'LifeCompass™方案适配自评表',
        '决策评估框架': 'LifeCompass™方案评估框架',
        '5维度决策框架': 'LifeCompass™ 5维方案适配',
        '5维度评估框架': 'LifeCompass™ 5维方案适配',
    },
    'D': {
        '决策框架': '机会扫描',
        '决策报告': 'OppScan™机会扫描报告',
        '决策自评表': '机会扫描自评表',
        '平台选择自评表': 'OppScan™机会扫描自评表',
        '决策评估框架': 'OppScan™机会评估框架',
        '5维度决策框架': 'OppScan™ 5维机会扫描',
    },
}

# 旧标题→新标题映射（每个选题的Day1标题需要特别处理）
TITLE_UPGRADES = {
    'T20260522003': {
        'old_keywords': ['考研控制vs电气怎么选', '考研控制vs电气', '控制vs电气'],
        'new_prefix': '25%后悔率：控制vs电气',
        'method_brand': 'PathFinder™ 5维路径推演',
    },
    'T20260522002': {
        'old_keywords': ['读博', '你适合读博吗'],
        'new_prefix': '3年差距定10年：读博vs就业',
        'method_brand': 'PathFinder™ 5维路径推演',
    },
    'T20260522001': {
        'old_keywords': ['防晒霜', '100-300元'],
        'new_prefix': '选错浪费200元：100-300元防晒霜',
        'method_brand': 'PathFinder™ 5维路径推演',
    },
    'T20260522004': {
        'old_keywords': ['中班拼音', '中班升大班', '拼音要不要提前学'],
        'new_prefix': '67%选错方案：中班拼音要不要提前学',
        'method_brand': 'LifeCompass™ 3维方案适配',
    },
    'T20260522005': {
        'old_keywords': ['SU vs 3Dmax', 'SU vs 3Dmax建模', '建模软件'],
        'new_prefix': '效率差3倍：SU vs 3Dmax',
        'method_brand': 'SkillRadar™ 6维适配诊断',
    },
    'T20260522006': {
        'old_keywords': ['AI绘画', 'AI绘画工具'],
        'new_prefix': '产出差5倍：AI绘画工具',
        'method_brand': 'SkillRadar™ 6维适配诊断',
    },
    'T20260522007': {
        'old_keywords': ['Pr vs 剪映', '视频剪辑'],
        'new_prefix': '学习成本差10倍：Pr vs 剪映',
        'method_brand': 'SkillRadar™ 6维适配诊断',
    },
    'T20260522008': {
        'old_keywords': ['小学教辅', '教辅选择'],
        'new_prefix': '5年差10万：小学教辅怎么选',
        'method_brand': 'LifeCompass™ 5维方案适配',
    },
    'T20260522009': {
        'old_keywords': ['iPad笔记', '笔记App'],
        'new_prefix': '90%只用1个功能：iPad笔记App',
        'method_brand': 'LifeCompass™ 5维方案适配',
    },
    'T20260522010': {
        'old_keywords': ['小红书vs B站', '小红书vs B站自媒体'],
        'new_prefix': '窗口期18个月：小红书vs B站',
        'method_brand': 'OppScan™ 5维机会扫描',
    },
}

def replace_in_text(text, replacements):
    """按替换词表替换文本，长词优先"""
    # 按长度降序排列，确保长词优先匹配
    sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
    for old in sorted_keys:
        new = replacements[old]
        text = text.replace(old, new)
    return text

def process_file(filepath, replacements, title_info=None, is_title=False):
    """处理单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 通用关键词替换
    content = replace_in_text(content, replacements)

    # title.txt特殊处理：在标题前加入数据锚点
    if is_title and title_info:
        # 如果标题中不包含新前缀的关键数据词，在前面加入
        new_prefix = title_info['new_prefix']
        # 检查标题是否已经包含数据锚点特征（数字+%或倍）
        has_data_anchor = bool(re.search(r'\d+[%％倍万]', content.strip()))
        if not has_data_anchor:
            # 在标题最前面加入数据锚点前缀
            # 提取新前缀中的数据锚点部分
            anchor_match = re.match(r'([^：]+：)', new_prefix)
            if anchor_match:
                anchor = anchor_match.group(1)
                content = anchor + content.strip()

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    total_files = 0
    changed_files = 0

    for tid, layer in TOPIC_LAYER.items():
        topic_dir = os.path.join(BASE, tid)
        if not os.path.isdir(topic_dir):
            continue

        xhs_dir = os.path.join(topic_dir, 'xiaohongshu')
        if not os.path.isdir(xhs_dir):
            continue

        replacements = LAYER_REPLACEMENTS[layer]
        title_info = TITLE_UPGRADES.get(tid)

        for day_dir in os.listdir(xhs_dir):
            day_path = os.path.join(xhs_dir, day_dir)
            if not os.path.isdir(day_path):
                continue

            # 处理 title.txt
            title_file = os.path.join(day_path, 'title.txt')
            if os.path.isfile(title_file):
                total_files += 1
                if process_file(title_file, replacements, title_info, is_title=True):
                    changed_files += 1

            # 处理 note.md
            note_file = os.path.join(day_path, 'note.md')
            if os.path.isfile(note_file):
                total_files += 1
                if process_file(note_file, replacements, title_info, is_title=False):
                    changed_files += 1

            # 处理 comments.txt
            comments_file = os.path.join(day_path, 'comments.txt')
            if os.path.isfile(comments_file):
                total_files += 1
                if process_file(comments_file, replacements, title_info, is_title=False):
                    changed_files += 1

    print(f'处理完成：共{total_files}个文件，{changed_files}个文件已更新')

if __name__ == '__main__':
    main()
