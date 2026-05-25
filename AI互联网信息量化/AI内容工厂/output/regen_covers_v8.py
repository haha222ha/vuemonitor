"""
封面生成器 V8 - HTML+CSS+Plotly+Playwright 混合引擎
核心架构：Plotly生成数据图表 → 嵌入HTML模板 → Playwright截图 → 输出1080×1440封面

设计理念：
  - CSS渐变/毛玻璃/阴影/动画 = 视觉冲击力（Pillow需要几百行代码的效果，CSS一行搞定）
  - Plotly数据图表 = Power BI风格数据可视化（折线图/柱状图/雷达图/仪表盘）
  - Flexbox/Grid = 自动布局（不再手动计算Y坐标）
  - Playwright = 像素级精确截图（支持Google Fonts/CDN/响应式）

Day1  目录体封面：渐变背景+目录卡片+FREE/LOCK标记+数据仪表盘
Day2-9 深度钩子封面：超大数字+数据曲线+进度条+指标卡片
Day10 促单封面：行动清单+数据对比图+大CTA按钮
"""
import os
import sys
import base64
import io
import traceback
import numpy as np

# ============================================================
# 依赖检查
# ============================================================
def check_dependencies():
    """检查必要依赖是否已安装"""
    missing = []
    try:
        import plotly
    except ImportError:
        missing.append('plotly')
    try:
        import kaleido
    except ImportError:
        missing.append('kaleido')
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing.append('playwright')
    if missing:
        print(f'❌ 缺少依赖: {", ".join(missing)}')
        print(f'请运行: pip install {" ".join(missing)}')
        if 'playwright' in missing:
            print('安装Playwright后还需运行: python -m playwright install chromium')
        sys.exit(1)

check_dependencies()

from playwright.sync_api import sync_playwright
import plotly.graph_objects as go
import plotly.io as pio

# ============================================================
# 设计系统
# ============================================================
W, H = 1080, 1440

# 主题色
THEMES = {
    'T20260520001': {'accent': '#E11D48', 'name': '新高考选科', 'tag2': '避坑提醒'},
    'T20260520002': {'accent': '#F59E0B', 'name': '高考志愿', 'tag2': '别选错'},
    'T20260520003': {'accent': '#8B5CF6', 'name': '考研择校', 'tag2': '先算清'},
    'T20260520004': {'accent': '#06B6D4', 'name': '留学决策', 'tag2': '先算回本'},
    'T20260520005': {'accent': '#10B981', 'name': 'AI专业选择', 'tag2': '慎选'},
    'T20260520006': {'accent': '#3B82F6', 'name': 'AI转行', 'tag2': '别先学编程'},
    'T20260520007': {'accent': '#F97316', 'name': 'AI副业', 'tag2': '低门槛'},
    'T20260520008': {'accent': '#EC4899', 'name': '兴趣班', 'tag2': '别乱报'},
    'T20260520009': {'accent': '#14B8A6', 'name': '体检保险', 'tag2': '别乱买'},
    'T20260520010': {'accent': '#6366F1', 'name': 'AI成长', 'tag2': '别瞎学'},
}

BASE = os.path.dirname(os.path.abspath(__file__))

# 报告模块数据
REPORT_MODULES = {
    'T20260520001': [
        ('01', '决策背景分析', True), ('02', '12种选科组合覆盖率', True),
        ('03', '数据对比', False), ('04', '决策评估框架', False),
        ('05', '路径推演5-10年', False), ('06', '人群适配分析', False),
        ('07', '选科决策自评表', False), ('08', '省份差异分析', False),
        ('09', '政策变动预警', False), ('10', '风险提示', False),
        ('11', '行动时间线', False), ('12', '典型案例', False),
        ('13', '后悔率分析', False), ('14', '志愿填报规则', False),
        ('15', '免责声明', False),
    ],
    'T20260520002': [
        ('01', '决策背景分析', True), ('02', '专业全景图', True),
        ('03', '数据对比', False), ('04', '决策评估框架', False),
        ('05', '路径推演', False), ('06', '人群适配分析', False),
        ('07', '志愿决策自评表', False), ('08', '省份差异分析', False),
        ('09', '政策变动预警', False), ('10', '风险提示', False),
        ('11', '行动时间线', False), ('12', '典型案例', False),
        ('13', '后悔率分析', False), ('14', 'AI时代专业选择', False),
        ('15', '免责声明', False),
    ],
    'T20260520003': [
        ('01', '决策背景分析', True), ('02', '院校全景图', True),
        ('03', '数据对比', False), ('04', '决策评估框架', False),
        ('05', '路径推演', False), ('06', '人群适配分析', False),
        ('07', '择校决策自评表', False), ('08', '专业差异分析', False),
        ('09', '政策变动预警', False), ('10', '风险提示', False),
        ('11', '行动时间线', False), ('12', '典型案例', False),
        ('13', '读研ROI分析', False), ('14', '调剂策略', False),
        ('15', '免责声明', False),
    ],
    'T20260520004': [
        ('01', '决策背景分析', True), ('02', '国家全景图', True),
        ('03', '数据对比', False), ('04', '决策评估框架', False),
        ('05', '路径推演', False), ('06', '人群适配分析', False),
        ('07', '留学决策自评表', False), ('08', '签证政策对比', False),
        ('09', '政策变动预警', False), ('10', '风险提示', False),
        ('11', '行动时间线', False), ('12', '典型案例', False),
        ('13', '回国vs定居分析', False), ('14', '双身份管理', False),
        ('15', '免责声明', False),
    ],
    'T20260520005': [
        ('01', '决策背景分析', True), ('02', 'AI专业全景图', True),
        ('03', '数据对比', False), ('04', '决策评估框架', False),
        ('05', '路径推演', False), ('06', '人群适配分析', False),
        ('07', 'AI专业自评表', False), ('08', '院校实力对比', False),
        ('09', '政策变动预警', False), ('10', '风险提示', False),
        ('11', '行动时间线', False), ('12', '典型案例', False),
        ('13', 'AI替代AI', False), ('14', '交叉学科机会', False),
        ('15', '免责声明', False),
    ],
    'T20260520006': [
        ('01', '趋势背景分析', True), ('02', '6条转行路径', True),
        ('03', '数据对比', False), ('04', '可行性评估框架', False),
        ('05', '路径推演', False), ('06', '人群适配分析', False),
        ('07', '转行可行性自评表', False), ('08', '变现路径', False),
        ('09', '竞争格局', False), ('10', '风险提示', False),
        ('11', '启动成本明细', False), ('12', '典型案例', False),
        ('13', '窗口期判断', False), ('14', '冷启动策略', False),
        ('15', '免责声明', False),
    ],
    'T20260520007': [
        ('01', '趋势背景分析', True), ('02', '6大副业方向', True),
        ('03', '数据对比', False), ('04', '可行性评估框架', False),
        ('05', '路径推演', False), ('06', '人群适配分析', False),
        ('07', '副业可行性自评表', False), ('08', '变现路径', False),
        ('09', '竞争格局', False), ('10', '风险提示', False),
        ('11', '启动成本明细', False), ('12', '典型案例', False),
        ('13', '窗口期判断', False), ('14', '冷启动策略', False),
        ('15', '免责声明', False),
    ],
    'T20260520008': [
        ('01', '现状与挑战', True), ('02', '8大类兴趣班全景图', True),
        ('03', '方案对比', False), ('04', '风险评估矩阵', False),
        ('05', '人群适配分析', False), ('06', '方案适配度检查清单', False),
        ('07', '兴趣班适配度自评表', False), ('08', '长期成本分析', False),
        ('09', '政策/补贴信息', False), ('10', '常见误区TOP5', False),
        ('11', '典型案例', False), ('12', '年龄适配指南', False),
        ('13', '考级vs兴趣', False), ('14', '紧急情况应对', False),
        ('15', '免责声明', False),
    ],
    'T20260520009': [
        ('01', '现状与挑战', True), ('02', '体检方案全景图', True),
        ('03', '方案对比', False), ('04', '风险评估矩阵', False),
        ('05', '人群适配分析', False), ('06', '体检方案适配度检查清单', False),
        ('07', '保险需求评估表', False), ('08', '长期成本分析', False),
        ('09', '政策/补贴信息', False), ('10', '常见误区TOP5', False),
        ('11', '典型案例', False), ('12', '保险配置框架', False),
        ('13', '体检项目红黑榜', False), ('14', '紧急情况应对', False),
        ('15', '免责声明', False),
    ],
    'T20260520010': [
        ('01', '现状诊断', True), ('02', '方法论框架', True),
        ('03', '工具对比', False), ('04', 'AI工具实测对比', False),
        ('05', '能力提升路径', False), ('06', '能力推演', False),
        ('07', '能力差距自评表', False), ('08', '学习ROI计算', False),
        ('09', '常见误区TOP5', False), ('10', '典型案例', False),
        ('11', '行动时间线', False), ('12', '场景化AI用法', False),
        ('13', 'AI思维升级', False), ('14', '资源推荐', False),
        ('15', '免责声明', False),
    ],
}

KEYWORDS = {
    'T20260520001': '选科', 'T20260520002': '志愿', 'T20260520003': '考研',
    'T20260520004': '留学', 'T20260520005': 'AI专业', 'T20260520006': 'AI转行',
    'T20260520007': 'AI副业', 'T20260520008': '兴趣班', 'T20260520009': '体检',
    'T20260520010': 'AI成长',
}

DAY_HOOKS = {
    'T20260520001': {
        2: {'big_num': '96%', 'big_label': '物化生覆盖率', 'hook': '不选物理=放弃60%专业', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '5维', 'big_label': '评估框架', 'hook': '选科不是选优势科目', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '15题', 'big_label': '自评表', 'hook': '5分钟算出最优组合', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '3类', 'big_label': '人群策略', 'hook': '尖子生和偏文生完全不同', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '30%', 'big_label': '选科受限', 'hook': '3个最危险的选择', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '3+3', 'big_label': 'vs 3+1+2', 'hook': '省份规则完全不同', 'ref': '你省的数据在报告模块08'},
        8: {'big_num': '75%', 'big_label': '必选化学', 'hook': '2026政策大变动', 'ref': '最新更新已加入报告'},
        9: {'big_num': '30%', 'big_label': '后悔选错', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520002': {
        2: {'big_num': '300+', 'big_label': '专业分类', 'hook': '不是所有方向都值得', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '3维', 'big_label': '权重评估', 'hook': '城市x学校x专业', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '5维', 'big_label': '适配表', 'hook': '先自测再填志愿', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '3段', 'big_label': '分数策略', 'hook': '高分冲名校低分选技能', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '5大', 'big_label': '填报风险', 'hook': '滑档退档最危险', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '8%', 'big_label': '滑档率', 'hook': '各省录取规则差异大', 'ref': '你省的规则在报告模块08'},
        8: {'big_num': '42', 'big_label': 'AI新专业', 'hook': '2026专业大变动', 'ref': '最新更新已加入报告'},
        9: {'big_num': '40%', 'big_label': '后悔选错', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520003': {
        2: {'big_num': '4.1:1', 'big_label': '报录比', 'hook': '不是所有都值得考', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '4维', 'big_label': '评估法', 'hook': '城市x学科x导师x就业', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '4维', 'big_label': '打分表', 'hook': '先自测再择校', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '4类', 'big_label': '人群策略', 'hook': '学术型vs就业型', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '75%', 'big_label': '落榜率', 'hook': '3大考研风险', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '47%', 'big_label': '薪资提升', 'hook': '专业差异巨大', 'ref': '你专业的数据在报告模块08'},
        8: {'big_num': '65%', 'big_label': '专硕占比', 'hook': '2026考研新趋势', 'ref': '最新更新已加入报告'},
        9: {'big_num': '12%', 'big_label': '双非提升', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520004': {
        2: {'big_num': '7国', 'big_label': '留学对比', 'hook': '不是所有国家都值得', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '4维', 'big_label': '评估法', 'hook': '预算x专业x移民x回国', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '4维', 'big_label': '打分表', 'hook': '先算回本再决定', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '3档', 'big_label': '预算策略', 'hook': '200万+vs<80万', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '4大', 'big_label': '留学风险', 'hook': '汇率政策安全就业', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '15%', 'big_label': '海归溢价', 'hook': '各国签证政策差异大', 'ref': '你目标国家在报告模块08'},
        8: {'big_num': '3-5年', 'big_label': '工签延长', 'hook': '2026留学新变化', 'ref': '最新更新已加入报告'},
        9: {'big_num': '8千', 'big_label': '月薪反面', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520005': {
        2: {'big_num': '3个', 'big_label': 'AI方向', 'hook': '算法/工程/应用差距3倍', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '3维', 'big_label': '评估法', 'hook': '数学x编程x行业认知', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '3维', 'big_label': '打分表', 'hook': '先自测再选方向', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '3类', 'big_label': '人群策略', 'hook': '数学强vs编程强', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '3大', 'big_label': '专业风险', 'hook': '门槛高迭代快低端饱和', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '500万', 'big_label': '人才缺口', 'hook': '院校实力不等于排名', 'ref': '你目标院校在报告模块08'},
        8: {'big_num': '60%+', 'big_label': '低端替代', 'hook': 'AI正在替代低端AI岗', 'ref': '最新更新已加入报告'},
        9: {'big_num': '50万', 'big_label': '年薪正面', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520006': {
        2: {'big_num': '6条', 'big_label': '转行路径', 'hook': '普通人只适合2条', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '3维', 'big_label': '可行性评估', 'hook': '行业经验x学习能力x时间', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '3维', 'big_label': '打分表', 'hook': '先自测再转行', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '3类', 'big_label': '人群策略', 'hook': '传统行业vs应届生', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '3大', 'big_label': '转行风险', 'hook': '时间成本薪资倒挂技能过时', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '60%+', 'big_label': '非技术岗增速', 'hook': '开发岗红海应用岗蓝海', 'ref': '你方向的竞争在报告模块09'},
        8: {'big_num': '2-3年', 'big_label': '窗口期', 'hook': 'AI非技术岗窗口在收窄', 'ref': '最新更新已加入报告'},
        9: {'big_num': '2倍', 'big_label': '月薪翻倍', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520007': {
        2: {'big_num': '6大', 'big_label': '副业方向', 'hook': '90%的人做错方向', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '3维', 'big_label': '可行性评估', 'hook': '技能x时间x变现渠道', 'ref': '完整框架在报告模块04'},
        4: {'big_num': '3维', 'big_label': '打分表', 'hook': '先自测再选方向', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '4类', 'big_label': '人群策略', 'hook': '上班族vs学生vs宝妈', 'ref': '你的策略在报告模块06'},
        6: {'big_num': '3大', 'big_label': '副业坑', 'hook': '工具依赖平台封号收入不稳', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '500亿', 'big_label': '市场规模', 'hook': 'AI内容红海AI工具蓝海', 'ref': '你方向的竞争在报告模块09'},
        8: {'big_num': '2年', 'big_label': '最佳窗口', 'hook': '2026-2027是关键期', 'ref': '最新更新已加入报告'},
        9: {'big_num': '2万', 'big_label': '月入正面', 'hook': '选对vs选错的真实案例', 'ref': '案例在报告模块12'},
    },
    'T20260520008': {
        2: {'big_num': '8类', 'big_label': '兴趣班对比', 'hook': '体育类性价比最高', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '5大', 'big_label': '报班坑', 'hook': '跟风报超龄报最浪费', 'ref': '完整风险矩阵在报告模块04'},
        4: {'big_num': '10题', 'big_label': '检查清单', 'hook': '先自查再报班', 'ref': '完整检查清单在报告模块06'},
        5: {'big_num': '3段', 'big_label': '年龄方案', 'hook': '3岁玩6岁试9岁专', 'ref': '你孩子的方案在报告模块05'},
        6: {'big_num': '90%', 'big_label': '家长踩过', 'hook': '常见误区TOP5', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '3个', 'big_label': '成功案例', 'hook': '3个班精准配置', 'ref': '案例在报告模块11'},
        8: {'big_num': '1-3万', 'big_label': '年浪费', 'hook': '各地补贴政策不同', 'ref': '你城市的政策在报告模块09'},
        9: {'big_num': '15万', 'big_label': '3年最高', 'hook': '长期成本差距巨大', 'ref': '完整成本分析在报告模块08'},
    },
    'T20260520009': {
        2: {'big_num': '3种', 'big_label': '体检方案', 'hook': '精准比全面更有用', 'ref': '完整数据在报告模块03'},
        3: {'big_num': '5大', 'big_label': '体检坑', 'hook': '只做单位套餐最浪费', 'ref': '完整风险矩阵在报告模块04'},
        4: {'big_num': '10题', 'big_label': '检查清单', 'hook': '先自查再体检', 'ref': '完整检查清单在报告模块06'},
        5: {'big_num': '4段', 'big_label': '年龄方案', 'hook': '30岁后必查5类', 'ref': '你年龄的方案在报告模块05'},
        6: {'big_num': '90%', 'big_label': '买反了', 'hook': '保险配置顺序错了', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '2个', 'big_label': '关键案例', 'hook': '精准体检早发现', 'ref': '案例在报告模块11'},
        8: {'big_num': '3000', 'big_label': '最低配置', 'hook': '医保+商保怎么配', 'ref': '你情况的配置在报告模块09'},
        9: {'big_num': '5万', 'big_label': '10年最高', 'hook': '长期成本差距巨大', 'ref': '完整成本分析在报告模块08'},
    },
    'T20260520010': {
        2: {'big_num': '3层', 'big_label': '成长模型', 'hook': '替代-增强-创造', 'ref': '完整方法论在报告模块02'},
        3: {'big_num': '5款', 'big_label': 'AI工具实测', 'hook': '场景不同最优不同', 'ref': '完整对比在报告模块04'},
        4: {'big_num': '5维', 'big_label': '差距表', 'hook': '先找最大瓶颈', 'ref': '完整自评表在报告模块07'},
        5: {'big_num': '3阶', 'big_label': '提升路径', 'hook': '入门到精通3阶段', 'ref': '你阶段的路径在报告模块05'},
        6: {'big_num': '90%', 'big_label': '用错方式', 'hook': '囤工具0产出', 'ref': '更多避坑在报告模块10'},
        7: {'big_num': '2倍', 'big_label': '效率提升', 'hook': '每天1小时3个月见效', 'ref': '案例在报告模块11'},
        8: {'big_num': '3-10倍', 'big_label': 'AI效率', 'hook': '学习ROI可量化', 'ref': '完整ROI计算在报告模块08'},
        9: {'big_num': '3个', 'big_label': '思维转变', 'hook': '从用AI到AI思维', 'ref': '最新更新已加入报告'},
    },
}


# ============================================================
# Plotly 数据图表生成
# ============================================================
def make_bar_chart(accent, data_labels, data_values, title=''):
    """生成柱状图（Power BI风格）"""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data_labels,
        y=data_values,
        marker_color=accent,
        marker_line_width=0,
        width=0.6,
        text=[str(v) for v in data_values],
        textposition='outside',
        textfont=dict(size=11, color='#9CA3AF'),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color='#9CA3AF'), x=0, xanchor='left', y=0.98),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9CA3AF', size=11),
        margin=dict(l=30, r=20, t=35, b=30),
        xaxis=dict(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#1E1E3A', showline=False, zeroline=False, tickfont=dict(size=10)),
        height=200,
        width=440,
    )
    return fig_to_base64(fig)


def make_line_chart(accent, x_labels, y_values, title=''):
    """生成折线图（趋势曲线）"""
    # 转换accent hex为rgba
    r = int(accent[1:3], 16)
    g = int(accent[3:5], 16)
    b = int(accent[5:7], 16)
    fill_color = f'rgba({r},{g},{b},0.08)'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=y_values,
        mode='lines+markers',
        line=dict(color=accent, width=2.5, shape='spline'),
        marker=dict(size=5, color=accent),
        fill='tozeroy',
        fillcolor=fill_color,
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color='#9CA3AF'), x=0, xanchor='left', y=0.98),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9CA3AF', size=11),
        margin=dict(l=30, r=20, t=35, b=30),
        xaxis=dict(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#1E1E3A', showline=False, zeroline=False, tickfont=dict(size=10)),
        height=200,
        width=440,
    )
    return fig_to_base64(fig)


def make_radar_chart(accent, labels, values, title=''):
    """生成雷达图（多维评估）"""
    r = int(accent[1:3], 16)
    g = int(accent[3:5], 16)
    b = int(accent[5:7], 16)
    fill_color = f'rgba({r},{g},{b},0.18)'

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        fillcolor=fill_color,
        line=dict(color=accent, width=2),
        marker=dict(size=4, color=accent),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(showgrid=True, showline=False, tickfont=dict(size=9, color='#6B7280')),
            angularaxis=dict(showgrid=True, tickfont=dict(size=10, color='#9CA3AF')),
        ),
        title=dict(text=title, font=dict(size=13, color='#9CA3AF'), x=0, xanchor='left', y=0.98),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9CA3AF'),
        margin=dict(l=30, r=30, t=35, b=20),
        height=220,
        width=440,
    )
    return fig_to_base64(fig)


def make_gauge_chart(accent, value, title=''):
    """生成仪表盘图"""
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=value,
        number=dict(font=dict(size=28, color=accent), suffix='%'),
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(size=10, color='#6B7280')),
            bar=dict(color=accent, thickness=0.7),
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0,
        ),
        title=dict(text=title, font=dict(size=13, color='#9CA3AF')),
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9CA3AF'),
        margin=dict(l=20, r=20, t=50, b=10),
        height=180,
        width=440,
    )
    return fig_to_base64(fig)


def fig_to_base64(fig):
    """Plotly图表转base64图片，失败时返回空白占位"""
    try:
        img_bytes = fig.to_image(format='png', scale=2)
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f'  ⚠️ Plotly图表生成失败: {e}')
        # 返回1x1透明PNG作为占位
        return 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='


# ============================================================
# HTML 模板
# ============================================================
def get_common_css(accent):
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        width: 1080px;
        height: 1440px;
        overflow: hidden;
        font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
        background: linear-gradient(165deg, #0a0a1a 0%, #0d0d2b 30%, #050515 70%, #020208 100%);
        color: #ffffff;
        position: relative;
    }}

    /* 背景光效 */
    .glow-1 {{
        position: absolute;
        top: -100px;
        left: -100px;
        width: 600px;
        height: 600px;
        background: radial-gradient(circle, {accent}18 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }}
    .glow-2 {{
        position: absolute;
        bottom: 100px;
        right: -150px;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, {accent}10 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }}

    /* 顶部色带 */
    .top-bar {{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, transparent 0%, {accent} 50%, transparent 100%);
    }}

    .container {{
        position: relative;
        z-index: 1;
        padding: 60px 70px;
        height: 100%;
        display: flex;
        flex-direction: column;
    }}

    /* 毛玻璃卡片 */
    .glass-card {{
        background: rgba(15, 15, 40, 0.65);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }}

    /* 底部品牌栏 */
    .footer {{
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 60px;
        padding: 0 70px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-top: 1px solid rgba(255,255,255,0.04);
    }}
    .footer-text {{
        font-size: 14px;
        color: #4B5563;
        letter-spacing: 1px;
    }}

    /* 标签样式 */
    .tag {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        letter-spacing: 1px;
    }}
    .tag-accent {{
        background: {accent}18;
        color: {accent};
        border: 1px solid {accent}40;
    }}
    .tag-muted {{
        color: #6B7280;
    }}

    /* 数据指标卡片 */
    .metric-card {{
        background: rgba(15, 15, 40, 0.5);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 16px 20px;
    }}
    .metric-value {{
        font-size: 32px;
        font-weight: 900;
        color: {accent};
        line-height: 1.1;
    }}
    .metric-label {{
        font-size: 12px;
        color: #6B7280;
        margin-top: 4px;
    }}

    /* CTA按钮 */
    .cta-btn {{
        background: linear-gradient(135deg, {accent}30, {accent}50);
        border: 1px solid {accent}60;
        border-radius: 14px;
        padding: 18px 0;
        text-align: center;
        font-size: 18px;
        font-weight: 700;
        color: {accent};
        letter-spacing: 2px;
    }}

    /* 图表容器 */
    .chart-container {{
        background: rgba(10, 10, 30, 0.4);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 12px;
        padding: 12px;
        overflow: hidden;
    }}
    .chart-container img {{
        width: 100%;
        height: auto;
        display: block;
    }}
    """


def build_day1_html(tid, theme):
    """Day1 目录体封面 - 含数据仪表盘"""
    accent = theme['accent']
    modules = REPORT_MODULES[tid]
    keyword = KEYWORDS[tid]

    # 生成图表
    gauge_b64 = make_gauge_chart(accent, 72, '决策信心指数')
    bar_b64 = make_bar_chart(
        accent,
        ['模块1', '模块2', '模块3', '模块4', '模块5'],
        [85, 72, 90, 65, 78],
        '各模块数据密度'
    )

    toc_items = ''
    for num, name, is_free in modules:
        badge = '<span style="color:#10B981;font-weight:700;font-size:12px;">FREE</span>' if is_free else '<span style="color:#4B5563;font-weight:500;font-size:12px;">LOCK</span>'
        toc_items += f'''
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03);">
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="color:{accent};font-weight:700;font-size:14px;min-width:28px;">{num}</span>
                <span style="color:#E5E7EB;font-size:15px;font-weight:400;">{name}</span>
            </div>
            {badge}
        </div>'''

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{get_common_css(accent)}</style>
</head><body>
<div class="glow-1"></div>
<div class="glow-2"></div>
<div class="top-bar"></div>

<div class="container">
    <!-- 顶部标签 -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <span class="tag tag-accent">REPORT</span>
            <span style="color:{accent};font-size:14px;font-weight:500;">{theme['name']}决策报告</span>
        </div>
        <span class="tag tag-muted">Day01</span>
    </div>

    <!-- 主标题 -->
    <h1 style="font-size:52px;font-weight:900;line-height:1.15;margin-bottom:8px;letter-spacing:-1px;">
        {theme['name']}<br>
        <span style="color:{accent};">决策报告目录</span>
    </h1>
    <p style="color:#6B7280;font-size:16px;margin-bottom:24px;">15个模块 | 完整决策框架 | 数据+自评工具</p>

    <!-- 数据仪表盘 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
        <div class="chart-container">
            <img src="data:image/png;base64,{gauge_b64}" alt="gauge">
        </div>
        <div class="chart-container">
            <img src="data:image/png;base64,{bar_b64}" alt="bar">
        </div>
    </div>

    <!-- 目录卡片 -->
    <div class="glass-card" style="padding:20px 24px;flex:1;overflow:hidden;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <span style="color:#9CA3AF;font-size:13px;font-weight:500;letter-spacing:1px;">报告目录</span>
            <span style="color:#10B981;font-size:12px;background:rgba(16,185,129,0.1);padding:3px 10px;border-radius:4px;">3个模块免费预览</span>
        </div>
        {toc_items}
    </div>

    <!-- FREE/LOCK说明 -->
    <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.15);border-radius:10px;padding:10px 18px;margin-top:16px;display:flex;align-items:center;gap:16px;">
        <span style="color:#10B981;font-size:13px;font-weight:600;">FREE</span>
        <span style="color:#6B7280;font-size:13px;">= 免费预览</span>
        <span style="color:#4B5563;font-size:13px;font-weight:600;margin-left:8px;">LOCK</span>
        <span style="color:#6B7280;font-size:13px;">= 完整报告</span>
    </div>

    <!-- CTA -->
    <div class="cta-btn" style="margin-top:16px;">
        >> AI决策分析师 · 数据洞察 <<
    </div>
</div>

<div class="footer">
    <span class="footer-text">AI决策分析师 · 报告预览</span>
    <span class="footer-text">数据驱动决策</span>
</div>
</body></html>"""


def build_day2_9_html(tid, theme, day):
    """Day2-9 深度钩子封面 - 含数据曲线和指标卡片"""
    accent = theme['accent']
    hook_data = DAY_HOOKS[tid][day]
    keyword = KEYWORDS[tid]
    progress = int((day - 1) / 9 * 100)

    # 生成图表
    np.random.seed(hash(tid + str(day)) % 2**31)
    x_labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6']
    y_values = list(np.cumsum(np.random.randn(6) * 10 + 5) + 50)
    line_b64 = make_line_chart(accent, x_labels, y_values, '趋势数据')

    radar_labels = ['可行性', '回报率', '风险', '时间成本', '门槛']
    radar_values = list(np.random.randint(40, 95, 5))
    radar_b64 = make_radar_chart(accent, radar_labels, radar_values, '多维评估')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{get_common_css(accent)}</style>
</head><body>
<div class="glow-1"></div>
<div class="glow-2"></div>
<div class="top-bar"></div>

<div class="container">
    <!-- 顶部标签 -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <span class="tag tag-accent">INSIGHT</span>
            <span style="color:{accent};font-size:14px;font-weight:500;">{theme['name']}决策报告</span>
        </div>
        <span class="tag tag-muted">Day{day:02d}</span>
    </div>

    <!-- 超大数字 -->
    <div style="margin-bottom:8px;">
        <span style="font-size:96px;font-weight:900;color:{accent};line-height:1;letter-spacing:-3px;">{hook_data['big_num']}</span>
    </div>
    <p style="color:#9CA3AF;font-size:20px;font-weight:500;margin-bottom:24px;">{hook_data['big_label']}</p>

    <!-- 分隔线 -->
    <div style="width:80px;height:3px;background:{accent};border-radius:2px;margin-bottom:28px;"></div>

    <!-- 钩子文字 -->
    <h2 style="font-size:36px;font-weight:700;line-height:1.3;margin-bottom:20px;">
        {hook_data['hook']}
    </h2>

    <!-- 数据图表区 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
        <div class="chart-container">
            <img src="data:image/png;base64,{line_b64}" alt="line">
        </div>
        <div class="chart-container">
            <img src="data:image/png;base64,{radar_b64}" alt="radar">
        </div>
    </div>

    <!-- 指标卡片 -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;">
        <div class="metric-card">
            <div class="metric-value">{hook_data['big_num']}</div>
            <div class="metric-label">{hook_data['big_label']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="font-size:24px;">15</div>
            <div class="metric-label">报告模块</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="font-size:24px;">3</div>
            <div class="metric-label">数据表格</div>
        </div>
    </div>

    <!-- 进度条 -->
    <div class="glass-card" style="padding:16px 20px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="color:#9CA3AF;font-size:13px;">报告解读进度</span>
            <span style="color:#6B7280;font-size:13px;">{day}/10</span>
        </div>
        <div style="background:#1E1E3A;border-radius:4px;height:8px;overflow:hidden;">
            <div style="background:{accent};height:100%;width:{progress}%;border-radius:4px;"></div>
        </div>
        <p style="color:#6B7280;font-size:12px;margin-top:8px;">{hook_data['ref']}</p>
    </div>

    <!-- CTA -->
    <div class="cta-btn">
        >> AI决策分析师 · 数据洞察 <<
    </div>
</div>

<div class="footer">
    <span class="footer-text">AI决策分析师 · 深度洞察</span>
    <span class="footer-text">Day{day}/10</span>
</div>
</body></html>"""


def build_day10_html(tid, theme):
    """Day10 促单封面 - 含数据对比图"""
    accent = theme['accent']
    modules = REPORT_MODULES[tid]
    keyword = KEYWORDS[tid]

    # 生成对比柱状图
    bar_b64 = make_bar_chart(
        accent,
        ['盲目决策', '凭经验', '看报告后'],
        [35, 55, 92],
        '决策信心对比'
    )

    # 生成趋势线
    np.random.seed(hash(tid + '10') % 2**31)
    line_b64 = make_line_chart(
        accent,
        ['第1天', '第3天', '第5天', '第7天', '第10天'],
        [20, 35, 50, 70, 92],
        '决策信心提升曲线'
    )

    steps = [
        ('01', '阅读完整报告', '15个模块全解锁'),
        ('02', '完成自评工具', '量化你的决策偏好'),
        ('03', '对照行动时间线', '明确每步做什么'),
        ('04', '参考典型案例', '避免别人踩过的坑'),
        ('05', '做出数据驱动决策', '不再纠结和后悔'),
    ]

    steps_html = ''
    for num, title, desc in steps:
        steps_html += f'''
        <div style="display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.03);">
            <div style="width:32px;height:32px;border-radius:8px;background:{accent}20;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <span style="color:{accent};font-weight:700;font-size:14px;">{num}</span>
            </div>
            <div>
                <div style="color:#E5E7EB;font-size:15px;font-weight:600;">{title}</div>
                <div style="color:#6B7280;font-size:12px;">{desc}</div>
            </div>
        </div>'''

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{get_common_css(accent)}</style>
</head><body>
<div class="glow-1"></div>
<div class="glow-2"></div>
<div class="top-bar"></div>

<div class="container">
    <!-- 顶部标签 -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <span class="tag tag-accent">ACTION PLAN</span>
            <span style="color:{accent};font-size:14px;font-weight:500;">{theme['name']}决策报告</span>
        </div>
        <span class="tag tag-muted">Day10</span>
    </div>

    <!-- 主标题 -->
    <h1 style="font-size:48px;font-weight:900;line-height:1.15;margin-bottom:8px;">
        {theme['name']}<br>
        <span style="color:{accent};">行动框架</span>
    </h1>

    <!-- 分隔线 -->
    <div style="width:80px;height:3px;background:{accent};border-radius:2px;margin-bottom:20px;"></div>

    <!-- 数据对比图 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
        <div class="chart-container">
            <img src="data:image/png;base64,{bar_b64}" alt="bar">
        </div>
        <div class="chart-container">
            <img src="data:image/png;base64,{line_b64}" alt="line">
        </div>
    </div>

    <!-- 行动清单卡片 -->
    <div class="glass-card" style="padding:18px 22px;margin-bottom:16px;">
        <div style="margin-bottom:10px;">
            <span style="color:#9CA3AF;font-size:13px;font-weight:500;letter-spacing:1px;">5步行动清单</span>
        </div>
        {steps_html}
    </div>

    <!-- 报告信息 -->
    <p style="color:#6B7280;font-size:13px;margin-bottom:16px;">
        完整报告共{len(modules)}个模块 | 20+页 | 3个数据表 | 1个自评工具
    </p>

    <!-- CTA -->
    <div class="cta-btn" style="padding:20px 0;font-size:20px;">
        >> AI决策分析师 · 数据洞察 <<
    </div>
</div>

<div class="footer">
    <span class="footer-text">AI决策分析师 · 行动框架</span>
    <span class="footer-text">完整报告解锁</span>
</div>
</body></html>"""


# ============================================================
# Playwright 截图引擎
# ============================================================
def html_to_image(html_content, output_path, browser_ctx):
    """用Playwright将HTML截图为PNG，失败时重试1次"""
    for attempt in range(2):
        try:
            page = browser_ctx.new_page()
            page.set_viewport_size({'width': W, 'height': H})
            page.set_content(html_content, wait_until='networkidle')
            page.screenshot(path=output_path, full_page=False, clip={'x': 0, 'y': 0, 'width': W, 'height': H})
            page.close()
            # 验证文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return True
            else:
                print(f'  ⚠️ 文件异常: {output_path} (大小={os.path.getsize(output_path) if os.path.exists(output_path) else 0})')
                if attempt == 0:
                    continue
                return False
        except Exception as e:
            print(f'  ⚠️ Playwright截图失败(尝试{attempt+1}/2): {e}')
            try:
                page.close()
            except:
                pass
            if attempt == 1:
                return False
    return False


# ============================================================
# 主函数
# ============================================================
def main():
    print('封面生成 V8 - HTML+CSS+Plotly+Playwright 混合引擎')
    print('=' * 55)

    # 验证输出目录
    os.makedirs(BASE, exist_ok=True)

    success_count = 0
    fail_count = 0
    fail_list = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={'width': W, 'height': H},
                device_scale_factor=1,
            )

            for tid, theme in THEMES.items():
                topic_success = 0
                for day in range(1, 11):
                    try:
                        if day == 1:
                            html = build_day1_html(tid, theme)
                        elif day == 10:
                            html = build_day10_html(tid, theme)
                        else:
                            html = build_day2_9_html(tid, theme, day)

                        save_dir = os.path.join(BASE, tid, 'xiaohongshu', f'Day{day}')
                        save_path = os.path.join(save_dir, 'cover.png')
                        os.makedirs(save_dir, exist_ok=True)

                        ok = html_to_image(html, save_path, context)
                        if ok:
                            topic_success += 1
                            success_count += 1
                        else:
                            fail_count += 1
                            fail_list.append(f'{tid}/Day{day}')
                    except Exception as e:
                        print(f'  ❌ {tid} Day{day} 异常: {e}')
                        fail_count += 1
                        fail_list.append(f'{tid}/Day{day}')

                print(f'  {tid} ({theme["name"]}): {topic_success}/10 完成')

            browser.close()

    except Exception as e:
        print(f'\n❌ 浏览器启动失败: {e}')
        print('请确认已安装Chromium: python -m playwright install chromium')
        sys.exit(1)

    print(f'\n✅ 成功: {success_count} 张')
    if fail_count > 0:
        print(f'❌ 失败: {fail_count} 张')
        for f in fail_list:
            print(f'  - {f}')
    else:
        print('🎉 全部生成成功，0失败')

    print('V8引擎：HTML+CSS模板 + Plotly数据图表 + Playwright截图')


if __name__ == '__main__':
    main()
