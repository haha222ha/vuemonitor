"""
统一生产入口 run_pipeline.py
整合：质检 → 报告生成 → 封面生成 → PDF导出 → 每日情报单篇（见 generate_daily_intel.py）
⚠️ 已废弃：10天 Day01~Day10 小红书矩阵
用法：
  python run_pipeline.py check          # 仅质检
  python run_pipeline.py covers         # 重新生成封面
  python run_pipeline.py pdf            # 导出PDF
  python run_pipeline.py clean          # 清理临时文件
  python run_pipeline.py full           # 完整流水线
"""
import os, sys, json, re, shutil, subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
TOPICS_DIR = BASE  # output目录就是BASE
PYTHON = sys.executable
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'


def get_topics():
    """获取所有选题目录"""
    topics = []
    for name in sorted(os.listdir(BASE)):
        path = os.path.join(BASE, name)
        if os.path.isdir(path) and name.startswith('T20260520'):
            topics.append((name, path))
    return topics


def cmd_check():
    """运行质检"""
    print('=' * 50)
    print('步骤1: 内容质检')
    print('=' * 50)
    qc_script = os.path.join(BASE, 'quality_check.py')
    if not os.path.exists(qc_script):
        print('  [ERROR] quality_check.py 不存在')
        return False
    result = subprocess.run([PYTHON, qc_script], capture_output=True, text=True)
    if result.returncode != 0 and 'UnicodeEncodeError' not in result.stderr:
        print(f'  [ERROR] 质检失败: {result.stderr[:200]}')
        return False
    # 读取报告
    report_path = os.path.join(BASE, 'quality_report.json')
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        avg_title = sum(r['title_avg_score'] for r in data) / len(data) if data else 0
        avg_note = sum(r['note_avg_score'] for r in data) / len(data) if data else 0
        total_issues = sum(r['total_issues'] for r in data)
        print(f'  标题均分: {avg_title:.1f}/10 | 正文均分: {avg_note:.1f}/10 | 问题总数: {total_issues}')
        if avg_title < 6 or avg_note < 6:
            print('  [WARN] 质量不达标，建议先修复再继续')
            return False
    print('  [OK] 质检完成')
    return True


def cmd_covers():
    """重新生成封面（使用generate_covers.py）"""
    print('=' * 50)
    print('步骤2: 封面生成')
    print('=' * 50)
    cover_script = os.path.join(os.path.dirname(BASE), 'generate_covers.py')
    if not os.path.exists(cover_script):
        print('  [WARN] generate_covers.py 不存在，跳过封面生成')
        return True
    result = subprocess.run([PYTHON, cover_script], capture_output=True, text=True, cwd=os.path.dirname(BASE))
    if result.returncode != 0:
        print(f'  [ERROR] 封面生成失败: {result.stderr[:200]}')
        return False
    print('  [OK] 封面生成完成')
    return True


def cmd_pdf():
    """导出PDF"""
    print('=' * 50)
    print('步骤3: PDF导出')
    print('=' * 50)
    topics = get_topics()
    success = 0
    for tid, tpath in topics:
        pdf_dir = os.path.join(tpath, 'pdf')
        export_script = os.path.join(pdf_dir, 'export_pdf.py')
        html_path = os.path.join(tpath, 'html', 'report.html')
        pdf_path = os.path.join(pdf_dir, 'report.pdf')

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 5000:
            print(f'  {tid}: PDF已存在({os.path.getsize(pdf_path)}B)，跳过')
            success += 1
            continue

        if not os.path.exists(html_path):
            print(f'  {tid}: HTML报告不存在，跳过')
            continue

        if os.path.exists(export_script):
            result = subprocess.run([PYTHON, export_script], capture_output=True, text=True, cwd=pdf_dir)
            if result.returncode == 0 and os.path.exists(pdf_path):
                print(f'  {tid}: PDF导出成功({os.path.getsize(pdf_path)}B)')
                success += 1
            else:
                print(f'  {tid}: PDF导出失败')
        else:
            print(f'  {tid}: export_pdf.py不存在，跳过')

    print(f'  [OK] PDF导出完成: {success}/{len(topics)}')
    return True


def cmd_clean():
    """清理临时文件"""
    print('=' * 50)
    print('步骤4: 清理临时文件')
    print('=' * 50)
    topics = get_topics()
    cleaned = 0

    for tid, tpath in topics:
        xhs_dir = os.path.join(tpath, 'xiaohongshu')
        if not os.path.isdir(xhs_dir):
            continue

        # 清理临时HTML
        for day in range(1, 11):
            temp = os.path.join(xhs_dir, f'Day{day}', '_cover_temp.html')
            if os.path.exists(temp):
                os.remove(temp)
                cleaned += 1

        # 清理cover.txt（旧版文本封面）
        for day in range(1, 11):
            txt = os.path.join(xhs_dir, f'Day{day}', 'cover.txt')
            if os.path.exists(txt):
                os.remove(txt)
                cleaned += 1

        # 清理过小的封面
        for day in range(1, 11):
            png = os.path.join(xhs_dir, f'Day{day}', 'cover.png')
            if os.path.exists(png) and os.path.getsize(png) < 10000:
                os.remove(png)
                cleaned += 1
                print(f'  {tid}/Day{day}: 删除过小封面({os.path.getsize(png)}B)')

    print(f'  [OK] 清理完成: 删除{cleaned}个临时文件')
    return True


def cmd_full():
    """完整流水线"""
    print('开始完整流水线...')
    print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()

    steps = [
        ('质检', cmd_check),
        ('清理', cmd_clean),
        ('封面', cmd_covers),
        ('PDF', cmd_pdf),
        ('最终质检', cmd_check),
    ]

    results = {}
    for name, func in steps:
        try:
            ok = func()
            results[name] = 'PASS' if ok else 'FAIL'
        except Exception as e:
            results[name] = f'ERROR: {e}'
        print()

    # 汇总
    print('=' * 50)
    print('流水线执行汇总')
    print('=' * 50)
    for name, status in results.items():
        icon = '[OK]' if status == 'PASS' else '[!!]'
        print(f'  {icon} {name}: {status}')

    return all(s == 'PASS' for s in results.values())


def main():
    if len(sys.argv) < 2:
        print('用法: python run_pipeline.py [check|covers|pdf|clean|full]')
        print()
        print('  check  - 运行内容质检')
        print('  covers - 重新生成封面')
        print('  pdf    - 导出PDF')
        print('  clean  - 清理临时文件')
        print('  full   - 完整流水线(质检→清理→封面→PDF→最终质检)')
        sys.exit(0)

    command = sys.argv[1].lower()
    commands = {
        'check': cmd_check,
        'covers': cmd_covers,
        'pdf': cmd_pdf,
        'clean': cmd_clean,
        'full': cmd_full,
    }

    if command not in commands:
        print(f'未知命令: {command}')
        print(f'可用命令: {", ".join(commands.keys())}')
        sys.exit(1)

    ok = commands[command]()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
