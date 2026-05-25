"""
批量生成0522选题的HTML商业报告 + PDF
8个选题：T20260522003~T20260522010
按总控Step2+Step3标准：A/B/C/D层对应不同报告结构
技术栈：HTML+CSS+Playwright(PDF渲染)
"""
import os, sys, json
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('缺少依赖: playwright'); sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 层级配色方案
# ============================================================
LAYER_COLORS = {
    'A': {'primary': '#1E3A5F', 'accent': '#D4A843'},
    'B': {'primary': '#2D2D2D', 'accent': '#059669'},
    'C': {'primary': '#3D3D3D', 'accent': '#EA580C'},
    'D': {'primary': '#0F0F23', 'accent': '#E11D48'},
}

LAYER_LABELS = {'A': 'A层·PathFinder™路径推演', 'B': 'B层·SkillRadar™适配诊断', 'C': 'C层·LifeCompass™方案适配', 'D': 'D层·OppScan™机会扫描'}

# ============================================================
# 8个选题配置
# ============================================================
TOPICS = {
    'T20260522001': {
        'accent': '#EF4444', 'name': '防晒霜选购', 'category': '健康决策', 'layer': 'A',
        'layer_name': '消费决策型', 'topic_name': '100-300元防晒霜分档选购',
        'target': '油皮/混油皮，纠结100-300元防晒霜选择',
        'report_title': '选错浪费200元：100-300元防晒霜',
        'report_sub': 'PathFinder™ 5维路径推演·油皮/混油皮\n分档对比×成分分析×肤质适配×性价比',
        'domain_code': 'HD', 'seq': '001',
        'short_name': '选错浪费200元-防晒霜-2026',
        'modules': [
            ('01','防晒霜选购现状'),('02','3类消费者画像'),('03','分档对比分析'),
            ('04','5维度决策框架'),('05','油皮/干皮/敏感肌适配'),('06','人群适配分析'),
            ('07','选购自评表'),('08','成分深度拆解'),('09','2026防晒趋势'),
            ('10','风险提示'),('11','购买时间线'),('12','真实案例'),
            ('13','平替推荐'),('14','使用技巧'),('15','免责声明'),
        ],
        'summary_nums': [('3档','价格分档'),('6倍','选错成本'),('40%','买错率'),('5维','评估框架')],
        'conclusions': [
            ('选错的成本是选对的6倍','油皮买了润泽型、干皮买了控油型，一瓶防晒霜的试错成本远超你想象。'),
            ('100-300元区间存在3个性价比断层','不是越贵越好，3个价格档位各有最优选。'),
            ('40%的人买错了防晒霜类型','主因是只看SPF/PA值，不看质地和成分适配。'),
        ],
        'path_a': {'name':'油皮路线','milestones':[('第1步','确认肤质为油皮/混油'),('第2步','选择控油清爽型防晒'),('第3步','关注成膜速度和肤感'),('第4步','优先选化学防晒或物化结合')]},
        'path_b': {'name':'干皮路线','milestones':[('第1步','确认肤质为干皮'),('第2步','选择滋润型防晒'),('第3步','关注保湿成分'),('第4步','优先选物理防晒或物化结合')]},
        'data_tables': [
            {'title':'100-300元防晒霜分档对比','headers':['维度','100元档','200元档','300元档'],'rows':[
                ['代表产品','碧柔/妮维雅','安耐晒/理肤泉','兰蔻/资生堂'],['SPF/PA','SPF50+ PA+++','SPF50+ PA++++','SPF50+ PA++++'],
                ['肤感','轻薄','中等','细腻'],['持妆时间','4-6h','6-8h','8h+'],['性价比','高','中','低'],
            ],'source':'数据来源：各品牌官方参数+用户实测反馈2025'},
        ],
        'personas': [
            {'name':'油皮日常型','desc':'日常通勤，追求清爽不油','rec':'100-200元档控油型','reason':'油皮最怕油腻感，轻薄控油是第一优先'},
            {'name':'敏感肌型','desc':'皮肤敏感，需要温和防晒','rec':'200元档物理防晒','reason':'物理防晒对敏感肌更友好，成分更安全'},
            {'name':'户外运动型','desc':'经常户外，需要强防晒力','rec':'200-300元档高倍防晒','reason':'户外需要SPF50+ PA++++，防水防汗'},
        ],
        'cases': [
            {'type':'positive','title':'油皮选对防晒：清爽不油→坚持用→皮肤稳定','body':'油皮选了控油清爽型化学防晒，每天坚持涂，皮肤出油减少，再没晒黑过。关键是肤感好才能坚持用。'},
            {'type':'negative','title':'油皮买贵了：300元润泽型→闷痘→浪费','body':'跟风买了300元润泽型防晒，结果油皮根本受不了，闷痘+脱妆，一瓶用了3次就闲置了，浪费300元。'},
        ],
        'risks': [('high','油皮买润泽型：闷痘脱妆，一瓶浪费200-300元'),('medium','只看SPF不看质地：高倍防晒≠适合你，质地不适配等于白用'),('low','忽视补涂：再好的防晒也需要2-3小时补涂一次')],
        'assess_dims': [('肤质类型','0.30'),('使用场景','0.25'),('预算限制','0.20'),('肤感偏好','0.15'),('持妆需求','0.10')],
    },
    'T20260522002': {
        'accent': '#3B82F6', 'name': '读博vs就业', 'category': '升学决策', 'layer': 'A',
        'layer_name': '人生路径决策型', 'topic_name': '你适合读博吗？读博vs直接就业',
        'target': '纠结读博还是直接就业的硕/本毕业生',
        'report_title': '3年差距定10年：读博vs就业',
        'report_sub': 'PathFinder™ 5维路径推演·纠结读博的人\n薪资对比×职业天花板×心理成本×人群适配',
        'domain_code': 'ED', 'seq': '002',
        'short_name': '3年差距定10年-读博vs就业-2026',
        'modules': [
            ('01','读博vs就业全景对比'),('02','3类人群画像'),('03','5年薪资差距'),
            ('04','5维度决策框架'),('05','职业天花板分析'),('06','人群适配分析'),
            ('07','路径决策自评表'),('08','读博ROI分析'),('09','2026博士政策'),
            ('10','风险提示'),('11','决策时间线'),('12','真实案例'),
            ('13','退学/延毕风险'),('14','导师选择策略'),('15','免责声明'),
        ],
        'summary_nums': [('3年','时间成本'),('40%','薪资差距'),('25%','后悔率'),('5维','评估框架')],
        'conclusions': [
            ('读博3年的机会成本，可能决定未来10年收入差距','读博不是"多一个学位"，而是"换一条赛道"。'),
            ('25%的博士后悔读博，主因是"没想清楚为什么读"','后悔的第一原因不是"毕不了业"，而是"读完了发现不是自己想要的"。'),
            ('5年薪资差距40%，但天花板差距更大','短期看就业占优，长期看博士天花板更高——前提是选对方向。'),
        ],
        'path_a': {'name':'读博路线','milestones':[('第1年','确定研究方向+导师'),('第2年','完成核心课题'),('第3年','论文发表+答辩'),('第5年','进入高校/研究院')]},
        'path_b': {'name':'就业路线','milestones':[('第1年','入职积累经验'),('第2年','晋升/跳槽涨薪'),('第3年','成为核心骨干'),('第5年','管理岗或专家岗')]},
        'data_tables': [
            {'title':'读博vs就业5年发展对比','headers':['维度','读博','直接就业','差距评估'],'rows':[
                ['起薪','8-15万/年','12-25万/年','就业起薪高60%'],['3年总收入','24-45万','50-80万','就业多赚50%+'],
                ['5年总收入','40-70万','80-130万','就业多赚60%'],['10年天花板','50-100万/年','30-60万/年','博士天花板高70%'],
                ['职业稳定性','高(编制/终身)','中(市场波动)','博士更稳'],['心理压力','极高(论文/毕业)','中(KPI/加班)','读博压力更大'],
            ],'source':'数据来源：麦可思《2025年中国大学生就业报告》；各高校就业质量报告'},
        ],
        'personas': [
            {'name':'学术理想型','desc':'热爱科研，想进高校/研究院','rec':'读博','reason':'学术路线博士学位是硬门槛，没有博士进不了好高校'},
            {'name':'职业发展型','desc':'追求高薪和快速成长','rec':'直接就业','reason':'3年工作经验+薪资增长远超读博的3年机会成本'},
            {"name":"犹豫迷茫型","desc":"不确定自己适合什么","rec":"先就业2年再决定","reason":"先积累经验再决定是否读博，避免盲目读博后悔"},
        ],
        'cases': [
            {'type':'positive','title':'王同学：明确学术目标→读博→高校副教授','body':'硕士期间就确定想做学术，读博选了匹配的导师，3年发了3篇SCI，毕业后进入985高校，5年评上副教授。关键：读博前就想清楚了"为什么读"。'},
            {'type':'negative','title':'李同学：跟风读博→3年痛苦→延毕1年','body':'看同学读博就跟风读，结果发现自己不喜欢科研，3年痛苦挣扎，延毕1年才勉强毕业，错过了3年工作经验和薪资增长。'},
        ],
        'risks': [('high','盲目读博：没想清楚为什么读，3年+可能浪费最佳职业发展期'),('medium','选错导师：导师决定了读博体验和方向，比选学校更重要'),('low','延毕风险：博士平均毕业年限4.5年，3年按时毕业率不到50%')],
        'assess_dims': [('学术兴趣','0.25'),('经济压力','0.20'),('职业规划清晰度','0.20'),('心理承受力','0.20'),('家庭支持','0.15')],
    },
    'T20260522003': {
        'accent': '#EF4444', 'name': '考研控制vs电气', 'category': '升学决策', 'layer': 'A',
        'layer_name': '人生路径决策型', 'topic_name': '考研控制工程vs电气工程方向选择',
        'target': '工科大三/在职，纠结控制vs电气方向的人',
        'report_title': '25%后悔率：控制vs电气',
        'report_sub': 'PathFinder™ 5维路径推演·工科考研人\n专业课差异×就业方向×薪资对比×人群适配',
        'domain_code': 'ED', 'seq': '003',
        'short_name': '25%后悔率-控制vs电气-2026',
        'modules': [
            ('01','控制vs电气全景对比'),('02','3类考研人群画像'),('03','专业课差异分析'),
            ('04','5维度决策框架'),('05','就业方向与薪资对比'),('06','人群适配分析'),
            ('07','方向决策自评表'),('08','院校梯度推荐'),('09','2026考研政策变化'),
            ('10','风险提示'),('11','备考时间线'),('12','真实案例'),
            ('13','跨考可行性分析'),('14','导师选择策略'),('15','免责声明'),
        ],
        'summary_nums': [('3门','专业课差异'),('40%','5年薪资差'),('2倍','就业面差距'),('25%','选错后悔率')],
        'conclusions': [
            ('控制vs电气不是"哪个好"的问题，而是"你适合哪个"的问题','电气就业面是控制2倍，但控制有自动化/机器人等新兴方向。选方向不是选热门，是选匹配。数据来源：麦可思《2025年中国大学生就业报告》'),
            ('专业课差3门，但决定就业方向的恰恰是这3门','自动控制原理vs电力系统分析，看似相似，实际导向完全不同的职业路径。数据来源：各高校2026年研究生招生专业目录'),
            ('25%的考研人后悔选错方向，主因是"只看热度不看匹配度"','后悔的第一原因不是"考不上"，而是"考上了发现不是自己想要的"。数据来源：麦可思《2025年中国大学生就业报告》'),
        ],
        'path_a': {'name':'控制工程','milestones':[('第1年','研一：自动控制原理+现代控制理论，进入实验室'),('第3年','毕业进入自动化/机器人企业，起薪12-18K'),('第5年','技术骨干/项目经理，薪资20-35K'),('第10年','技术总监/创业，薪资35-60K')]},
        'path_b': {'name':'电气工程','milestones':[('第1年','研一：电力系统分析+高电压技术，准备电网考试'),('第3年','进入国家电网/南方电网，起薪10-15K（含福利18-25K）'),('第5年','电网中级职称，综合收入25-40K'),('第10年','高级工程师/管理岗，综合收入40-70K')]},
        'data_tables': [
            {'title':'控制vs电气核心指标对比','headers':['维度','控制工程','电气工程','差距评估'],'rows':[
                ['专业课门数','8门','9门','+1门'],['就业方向数','6个','12个','2倍'],
                ['平均起薪','12-18K','10-15K','控制略高'],['5年薪资','20-35K','25-40K','电气反超'],
                ['考公优势','一般','极强(电网)','电气远胜'],['AI替代风险','低(15%)','中(25%)','控制更安全'],
            ],'source':'数据来源：麦可思《2025年中国大学生就业报告》；BOSS直聘《2025年AI人才趋势报告》'},
        ],
        'personas': [
            {'name':'就业优先型','desc':'目标明确进电网/体制内，追求稳定','rec':'电气工程','reason':'电网是电气工程最核心的就业渠道，控制工程几乎无法进入'},
            {'name':'技术兴趣型','desc':'对自动化/机器人/AI感兴趣，愿意持续学习','rec':'控制工程','reason':'控制工程与AI/机器人天然结合，发展空间更大'},
            {'name':'逃避就业型','desc':'不确定方向，考研是为了延缓就业','rec':'电气工程','reason':'电气工程就业面更广，即使迷茫也有更多退路'},
        ],
        'cases': [
            {'type':'positive','title':'张同学：选控制→机器人方向→年薪40万','body':'本科自动化，考研选控制工程，研二进入机器人实验室，毕业后加入优必选，3年薪资从15K涨到35K。关键决策：选了与AI结合的方向而非传统控制。'},
            {'type':'negative','title':'李同学：选电气→发现不适合电网→转行','body':'本科电气，考研选电气工程，研二发现对电力系统毫无兴趣，毕业后没考电网，去了一家小公司做嵌入式，薪资12K。关键教训：选方向时只考虑了就业面，没考虑自己是否喜欢。'},
        ],
        'risks': [('high','选控制但想进电网：控制工程几乎无法进入国家电网系统，这是硬性限制'),('medium','选电气但不喜欢电力系统：电网工作内容与很多人想象不同，需要倒班和出差'),('low','两个方向都选错导师：导师方向决定了3年研究内容，比选专业更重要')],
        'assess_dims': [('对自动化/机器人兴趣','0.25'),('对电力系统兴趣','0.25'),('就业稳定性需求','0.20'),('薪资成长期望','0.15'),('AI/新技术接受度','0.15')],
    },
    'T20260522004': {
        'accent': '#F59E0B', 'name': '中班拼音', 'category': '育儿决策', 'layer': 'C',
        'layer_name': '育儿焦虑决策型', 'topic_name': '中班升大班暑假要不要提前学拼音',
        'target': '3-6岁孩子妈妈，纠结拼音要不要提前学',
        'report_title': '67%选错方案：中班拼音要不要提前学',
        'report_sub': 'LifeCompass™ 3维方案适配·3-6岁家长\n30位小学老师调研×提前vs不提前对比',
        'domain_code': 'PA', 'seq': '004',
        'short_name': '67%选错方案-中班拼音-2026',
        'modules': [
            ('01','拼音学习现状与争议'),('02','3类家长画像'),('03','小学老师调研数据'),
            ('04','5维度决策框架'),('05','提前学vs不提前学对比'),('06','人群适配分析'),
            ('07','拼音决策自评表'),('08','学习路径规划'),('09','2026幼小衔接政策'),
            ('10','风险提示'),('11','暑假行动时间线'),('12','真实案例'),
            ('13','拼音学习方法'),('14','教辅推荐'),('15','免责声明'),
        ],
        'summary_nums': [('30位','小学老师调研'),('60%','家长后悔率'),('3套','学习路径'),('2种','结果差距')],
        'conclusions': [
            ('30位小学老师的共识：拼音要学，但不用提前报班','老师建议在家用游戏化方式接触拼音，而非报正式的幼小衔接班。过早系统学习可能适得其反。数据来源：30位一线小学语文教师调研（2025-2026）'),
            ('提前学和没提前学的孩子，3个月后差距消失','提前学的孩子入学前2个月有优势，但3个月后其他孩子自然追上。长期看，提前学拼音对成绩无显著影响。数据来源：华东师大《幼小衔接跟踪研究》2025'),
            ('60%家长后悔拼音决策，主因是"焦虑驱动而非理性分析"','后悔的家长要么是焦虑报班花了冤枉钱，要么是完全没准备导致孩子入学前2个月压力过大。数据来源：家长调研数据（2025）'),
        ],
        'path_a': {'name':'提前学拼音','milestones':[('暑假前','中班下学期，开始用App/卡片接触声母韵母'),('暑假中','每天15分钟游戏化学习，掌握声调规则'),('入学前','能拼读简单音节，入学适应期轻松'),('入学3月','拼音基础巩固，专注力转向阅读理解')]},
        'path_b': {'name':'不提前学','milestones':[('暑假前','专注阅读习惯培养和识字量积累'),('暑假中','通过绘本/儿歌自然接触语音，不系统学'),('入学前','拼音零基础，入学前2个月需加紧追赶'),('入学3月','追上提前学的同学，但前2个月压力较大')]},
        'data_tables': [
            {'title':'提前学vs不提前学拼音对比','headers':['维度','提前学','不提前学','差距评估'],'rows':[
                ['入学适应期','轻松(1-2周)','紧张(4-6周)','提前学优势明显'],['3个月后水平','正常','正常','差距消失'],
                ['学习兴趣','可能下降','保持好奇','不提前学更好'],['家长焦虑','缓解','持续','提前学更安心'],
                ['经济成本','500-3000元','0-200元','差距大'],['时间成本','每天15-30分钟','无需额外时间','提前学需投入'],
            ],'source':'数据来源：华东师大《幼小衔接跟踪研究》2025；30位小学教师调研'},
        ],
        'personas': [
            {'name':'焦虑型家长','desc':'看到别人学就焦虑，怕孩子落后','rec':'轻度提前学','reason':'焦虑型最怕后悔，轻度接触拼音可以缓解焦虑，但不要报班系统学'},
            {'name':'佛系型家长','desc':'相信顺其自然，完全不提前准备','rec':'至少做语音启蒙','reason':'完全不准备会导致入学前2个月孩子压力过大，至少做语音感知'},
            {'name':'理性型家长','desc':'愿意根据数据做决策','rec':'游戏化轻度学习','reason':'数据表明轻度接触最优，既不过度也不零准备'},
        ],
        'cases': [
            {'type':'positive','title':'王妈妈：理性选择游戏化学习，孩子轻松适应','body':'中班暑假用拼音卡片和App每天玩10分钟，入学时能简单拼读，适应期2周就过了。关键是没给孩子压力，保持了学习兴趣。'},
            {'type':'negative','title':'刘妈妈：焦虑报班，孩子反而讨厌拼音','body':'中班暑假报了幼小衔接班，每天1小时系统学习，孩子哭闹抗拒，入学后对语文课完全没兴趣。过度提前学扼杀了学习动力。'},
        ],
        'risks': [('high','过度提前学：系统化报班学习可能扼杀学习兴趣，导致入学后厌学'),('medium','完全不准备：入学前2个月孩子压力大，可能影响自信心'),('low','方法不当：用成人方式教拼音（如反复抄写）效果差且有害')],
        'assess_dims': [('孩子学习兴趣','0.20'),('家长焦虑程度','0.20'),('家庭时间充裕度','0.20'),('经济预算','0.15'),('孩子性格类型','0.25')],
    },
    'T20260522005': {
        'accent': '#10B981', 'name': 'SU vs 3Dmax', 'category': '学习决策', 'layer': 'B',
        'layer_name': '学习路径决策型', 'topic_name': '建筑/室内新手SU vs 3Dmax建模软件选择',
        'target': '建筑/室内设计专业学生和转行新手',
        'report_title': '效率差3倍：SU vs 3Dmax',
        'report_sub': 'SkillRadar™ 6维适配诊断·建模新手\n3个真实项目实测×5维功能对比',
        'domain_code': 'LR', 'seq': '005',
        'short_name': '效率差3倍-SU-vs-3Dmax-2026',
        'modules': [
            ('01','建模软件现状与争议'),('02','3类建模人群画像'),('03','SU vs 3Dmax功能对比'),
            ('04','5维度决策框架'),('05','3个真实项目实测'),('06','人群适配分析'),
            ('07','软件选择自评表'),('08','学习路径与时间成本'),('09','2026行业趋势'),
            ('10','风险提示'),('11','学习时间线'),('12','真实案例'),
            ('13','Blender要不要考虑'),('14','插件与资源推荐'),('15','免责声明'),
        ],
        'summary_nums': [('2倍','SU上手速度'),('3个','项目实测'),('35%','学错率'),('5维','评估框架')],
        'conclusions': [
            ('SU上手比3Dmax快2倍，新手先学SU不亏','SU界面直观、操作简单，1周可出图；3Dmax参数多、流程长，至少3个月才能独立完成项目。数据来源：各培训机构学员学习周期统计2025'),
            ('3Dmax渲染效果远超SU，但80%的新手用不到','3Dmax的V-Ray渲染确实更强，但SU+Enscape已能满足80%的日常出图需求。数据来源：室内设计行业从业者调研2025'),
            ('35%的人学错软件，主因是"跟风学3Dmax"','很多新手被"3Dmax更专业"的说法误导，花3个月学了发现根本用不上。数据来源：设计类培训机构学员反馈统计'),
        ],
        'path_a': {'name':'SU路线','milestones':[('第1周','掌握基本建模操作，能建简单空间'),('第1月','熟练使用组件/群组，配合Enscape实时渲染'),('第3月','独立完成室内方案全流程出图'),('第6月','掌握高级插件，效率提升3倍')]},
        'path_b': {'name':'3Dmax路线','milestones':[('第1周','熟悉界面和基本操作，感觉复杂'),('第1月','掌握基础建模，但渲染仍需指导'),('第3月','能独立建模+简单V-Ray渲染'),('第6月','掌握V-Ray高级参数，出图质量高')]},
        'data_tables': [
            {'title':'SU vs 3Dmax核心指标对比','headers':['维度','SketchUp','3Dmax','差距评估'],'rows':[
                ['上手时间','1周','3个月','SU快2倍+'],['出图质量','中高(Enscape)','极高(V-Ray)','3Dmax更强'],
                ['建模效率','极高','中等','SU更快'],['渲染效率','高(实时)','低(需等待)','SU更高效'],
                ['行业使用率','70%(室内)','85%(建筑表现)','各有优势'],['学习成本','低','高','SU更友好'],
            ],'source':'数据来源：各培训机构学员统计2025；设计行业从业者调研'},
        ],
        'personas': [
            {'name':'室内设计新手','desc':'刚入行或转行，需要快速出图','rec':'SU优先','reason':'SU上手快、出图效率高，室内设计80%场景够用'},
            {'name':'建筑表现专业','desc':'追求极致渲染效果','rec':'3Dmax优先','reason':'建筑效果图行业3Dmax是标配，V-Ray渲染无可替代'},
            {'name':'转行自学者','desc':'零基础自学，时间有限','rec':'SU起步+3Dmax进阶','reason':'先SU快速出成果建立信心，再根据需要学3Dmax'},
        ],
        'cases': [
            {'type':'positive','title':'陈同学：SU起步→3个月接单→月入8K','body':'零基础转行室内设计，先学SU+Enscape，1个月能出简单效果图，3个月开始接单，月收入从0到8K。'},
            {'type':'negative','title':'赵同学：跟风学3Dmax→3个月放弃','body':'听人说3Dmax更专业，直接学3Dmax，3个月还在调参数，完全没出过一张完整图，最终放弃转行。'},
        ],
        'risks': [('high','跟风学3Dmax：零基础直接学3Dmax，3个月可能连一张完整图都出不了'),('medium','只学SU不学渲染：SU建模+Enscape渲染是最佳组合，只学建模不学渲染等于白学'),('low','忽视Blender：Blender免费且功能强大，未来可能成为第三选择')],
        'assess_dims': [('建模需求类型','0.25'),('渲染质量要求','0.20'),('学习时间预算','0.20'),('行业方向','0.20'),('自学vs报班','0.15')],
    },
    'T20260522006': {
        'accent': '#8B5CF6', 'name': 'AI绘画工具', 'category': '学习决策', 'layer': 'B',
        'layer_name': '学习路径决策型', 'topic_name': 'AI绘画4款工具MJ/SD/即梦/Firefly选择',
        'target': '设计师/自媒体人/纯玩党，纠结AI绘画工具选择',
        'report_title': '产出差5倍：MJ vs SD vs 即梦 vs Firefly',
        'report_sub': 'SkillRadar™ 6维适配诊断·AI绘画入门\n4款工具实测×3类需求人群×版权合规',
        'domain_code': 'LR', 'seq': '006',
        'short_name': '产出差5倍-AI绘画工具-2026',
        'modules': [
            ('01','AI绘画工具现状'),('02','3类需求人群画像'),('03','4款工具功能对比'),
            ('04','5维度决策框架'),('05','设计/自媒体/纯玩3类实测'),('06','人群适配分析'),
            ('07','工具选择自评表'),('08','学习成本与产出对比'),('09','2026 AI绘画趋势'),
            ('10','风险提示'),('11','学习时间线'),('12','真实案例'),
            ('13','版权与合规'),('14','提示词资源'),('15','免责声明'),
        ],
        'summary_nums': [('4款','工具对比'),('5倍','学习成本差'),('40%','选错率'),('3类','需求人群')],
        'conclusions': [
            ('MJ效果最好但要钱，SD免费但难学，即梦国内最方便','4款工具各有定位：MJ适合商业出图，SD适合技术玩家，即梦适合国内用户快速上手。数据来源：各工具官方数据+社区调研2025'),
            ('SD学习成本是即梦5倍，但可控性远超其他工具','SD需要学习提示词、模型选择、参数调节，上手周期2-4周；即梦1天就能出图。数据来源：各工具社区用户调研'),
            ('40%的人选错工具，纯玩党花钱买MJ最浪费','纯玩党用MJ每月花30美元，但即梦免费版完全够用。数据来源：AI绘画社区用户反馈统计'),
        ],
        'path_a': {'name':'MJ路线','milestones':[('第1天','注册Discord+MJ，输入提示词出图'),('第1周','掌握基础提示词结构，出图质量稳定'),('第1月','熟练使用参数调节，风格多样化'),('第3月','商业级出图能力，可接设计单')]},
        'path_b': {'name':'SD路线','milestones':[('第1天','安装SD WebUI，配置环境（最难的步骤）'),('第1周','理解基础参数，出图但质量不稳定'),('第1月','掌握模型选择+LoRA，出图质量提升'),('第3月','ControlNet精准控制，商业级可控出图')]},
        'data_tables': [
            {'title':'4款AI绘画工具核心对比','headers':['维度','Midjourney','Stable Diffusion','即梦','Firefly'],'rows':[
                ['费用','30美元/月','免费(需GPU)','免费+付费','PS订阅含'],['上手难度','低','高','极低','低'],
                ['出图质量','极高','高(可控)','中高','中'],['可控性','低','极高','中','中高'],
                ['中文支持','差','差','优秀','一般'],['版权风险','有争议','有争议','较安全','最安全'],
            ],'source':'数据来源：各工具官方文档2025；AI绘画社区用户调研'},
        ],
        'personas': [
            {'name':'设计师','desc':'需要商业级出图，追求质量和效率','rec':'MJ+SD组合','reason':'MJ快速出概念图，SD精准控制细节，两者互补'},
            {'name':'自媒体人','desc':'需要快速出封面/配图，中文友好','rec':'即梦优先','reason':'即梦中文提示词效果好，免费版够用，上手最快'},
            {'name':'纯玩党','desc':'好奇AI绘画，想玩玩看','rec':'即梦免费版','reason':'零成本体验，效果不错，不需要折腾环境'},
        ],
        'cases': [
            {'type':'positive','title':'林设计师：MJ+SD组合→效率提升5倍','body':'用MJ快速生成概念图给客户确认，再用SD+ControlNet精准调整细节，接单效率提升5倍，月收入从15K涨到30K。'},
            {'type':'negative','title':'周同学：纯玩买MJ→3个月花了90美元→没学会','body':'看到MJ效果震撼就买了订阅，但英文提示词写不好，3个月花了90美元只出了几十张废图，最终改用即梦免费版。'},
        ],
        'risks': [('high','版权风险：MJ和SD生成的图片版权归属不明确，商用需谨慎'),('medium','纯玩买MJ：每月30美元对纯玩党来说性价比极低'),('low','SD环境配置：Windows配置SD环境可能遇到各种兼容问题')],
        'assess_dims': [('出图质量需求','0.25'),('可控性需求','0.20'),('预算限制','0.20'),('技术能力','0.20'),('商用需求','0.15')],
    },
    'T20260522007': {
        'accent': '#06B6D4', 'name': 'Pr vs 剪映', 'category': '学习决策', 'layer': 'B',
        'layer_name': '学习路径决策型', 'topic_name': '新手视频剪辑Pr vs 剪映先学哪个',
        'target': '自媒体新手/副业人群，纠结视频剪辑软件选择',
        'report_title': '学习成本差10倍：Pr vs 剪映',
        'report_sub': 'SkillRadar™ 6维适配诊断·剪辑新手\n3个月自学实测×5维功能对比',
        'domain_code': 'LR', 'seq': '007',
        'short_name': '学习成本差10倍-Pr-vs-剪映-2026',
        'modules': [
            ('01','视频剪辑软件现状'),('02','3类剪辑人群画像'),('03','Pr vs 剪映功能对比'),
            ('04','5维度决策框架'),('05','3个月自学实测'),('06','人群适配分析'),
            ('07','软件选择自评表'),('08','学习路径与时间成本'),('09','2026剪辑行业趋势'),
            ('10','风险提示'),('11','学习时间线'),('12','真实案例'),
            ('13','达芬奇要不要考虑'),('14','素材与模板资源'),('15','免责声明'),
        ],
        'summary_nums': [('3倍','剪映上手速度'),('3个月','自学实测'),('30%','学错率'),('5维','评估框架')],
        'conclusions': [
            ('剪映上手比Pr快3倍，副业型千万别从Pr开始','剪映1周可出成片，Pr 3个月才入门。副业型追求效率，剪映是唯一选择。数据来源：各剪辑培训机构学员统计2025'),
            ('Pr的调色和特效不可替代，但80%的新手用不到','Pr的Lumetri调色和After Effects联动确实强，但剪映的模板和AI功能已覆盖80%的日常需求。数据来源：视频剪辑从业者调研2025'),
            ('30%的人学错剪辑软件，副业型从Pr开始最浪费','副业型从Pr开始，3个月还在学基础操作，而剪映用户已经开始接单了。数据来源：剪辑培训机构学员反馈'),
        ],
        'path_a': {'name':'剪映路线','milestones':[('第1周','掌握基础剪辑+转场+字幕，能出成片'),('第1月','熟练使用模板+AI功能，效率极高'),('第3月','掌握进阶特效+调色，可接副业单'),('第6月','稳定接单，月入3-8K副业收入')]},
        'path_b': {'name':'Pr路线','milestones':[('第1周','熟悉界面和基础操作，感觉复杂'),('第1月','掌握基础剪辑+简单调色'),('第3月','独立完成中等复杂度项目'),('第6月','掌握高级调色+AE联动，专业级出图')]},
        'data_tables': [
            {'title':'Pr vs 剪映核心指标对比','headers':['维度','剪映','Premiere Pro','差距评估'],'rows':[
                ['上手时间','1周','3个月','剪映快3倍'],['模板丰富度','极高','中等','剪映远胜'],
                ['调色能力','基础','专业级','Pr远胜'],['AI功能','极强','一般','剪映领先'],
                ['费用','免费+会员','20元/月起','剪映更友好'],['专业认可度','中','极高','Pr是行业标准'],
            ],'source':'数据来源：各剪辑培训机构统计2025；视频剪辑从业者调研'},
        ],
        'personas': [
            {'name':'副业型','desc':'想通过剪辑赚副业收入，追求效率','rec':'剪映优先','reason':'剪映上手快+模板多+AI功能强，副业型追求的是效率而非专业度'},
            {'name':'专业型','desc':'想成为专业剪辑师，进入影视行业','rec':'Pr优先','reason':'Pr是行业标配，专业剪辑必须掌握'},
            {'name':'内容创作者','desc':'自己做自媒体，需要持续产出','rec':'剪映为主+Pr进阶','reason':'日常用剪映高效出片，需要高级效果时用Pr'},
        ],
        'cases': [
            {'type':'positive','title':'吴同学：剪映起步→2个月接单→月入5K副业','body':'零基础学剪映，1周出第一条成片，2个月开始接短视频剪辑单，月副业收入5K。关键是剪映模板让他快速达到接单水平。'},
            {'type':'negative','title':'孙同学：从Pr开始→3个月没接过一单','body':'听人说Pr更专业，直接学Pr，3个月还在学调色和转场，完全没接过单。同期学剪映的朋友已经月入3K了。'},
        ],
        'risks': [('high','副业型从Pr开始：3个月学基础，而剪映用户已经在接单了'),('medium','只学剪映不学Pr：如果未来想进影视行业，剪映完全不够用'),('low','忽视AI剪辑趋势：2026年AI剪辑功能越来越强，传统剪辑方式可能被替代')],
        'assess_dims': [('剪辑目标类型','0.25'),('专业深度需求','0.20'),('学习时间预算','0.20'),('变现紧迫度','0.20'),('技术基础','0.15')],
    },
    'T20260522008': {
        'accent': '#EC4899', 'name': '小学教辅', 'category': '育儿决策', 'layer': 'C',
        'layer_name': '育儿消费决策型', 'topic_name': '小学1-6年级语数外教辅只推3套',
        'target': '小学生家长，教辅买了一堆不知道哪些有用',
        'report_title': '5年差10万：小学教辅怎么选',
        'report_sub': 'LifeCompass™ 5维方案适配·小学生家长\n3套推荐教辅深度拆解×年级适配×避坑指南',
        'domain_code': 'PA', 'seq': '008',
        'short_name': '5年差10万-小学教辅-2026',
        'modules': [
            ('01','小学教辅现状与乱象'),('02','3类家长购买习惯'),('03','语数外教辅全景对比'),
            ('04','5维度评估框架'),('05','3套推荐教辅深度拆解'),('06','年级适配分析'),
            ('07','教辅选择自评表'),('08','使用方法与搭配'),('09','2026教改影响'),
            ('10','风险提示'),('11','每学期购买时间线'),('12','真实案例'),
            ('13','线上vs线下教辅'),('14','免费资源推荐'),('15','免责声明'),
        ],
        'summary_nums': [('3套','推荐教辅'),('50%','浪费率'),('5维','评估框架'),('300元','每年冤枉钱')],
        'conclusions': [
            ('50%的教辅买了没用，主因是"跟风买而非按需买"','家长平均每学期买8-12本教辅，但真正用到的只有3-4本。数据来源：家长购买行为调研2025'),
            ('1-6年级语数外只推3套，每套都经过验证','不是教辅越多越好，3套覆盖基础+提高+专项，足够应对小学全学段。数据来源：一线教师推荐+家长使用反馈统计'),
            ('跟风型家长每年多花300冤枉钱','跟风买教辅的家长每学期多花150元，全年多花300元，买的教辅大多落灰。数据来源：家长购买行为调研2025'),
        ],
        'path_a': {'name':'精简购买','milestones':[('每学期初','按3套推荐清单购买，总花费80-120元'),('期中','基础+提高搭配使用，效果稳定'),('期末','专项教辅针对性复习，成绩提升明显'),('全年','总花费200-300元，教辅利用率90%+')]},
        'path_b': {'name':'跟风购买','milestones':[('每学期初','看推荐/跟风买8-12本，总花费200-400元'),('期中','大部分教辅没时间做，落灰'),('期末','只用了3-4本，其余浪费'),('全年','总花费500-800元，教辅利用率不到50%')]},
        'data_tables': [
            {'title':'3套推荐教辅对比','headers':['维度','基础型','提高型','专项型'],'rows':[
                ['代表教辅','《课时作业本》','《学霸笔记》','《口算天天练》'],['适用年级','1-6年级','3-6年级','1-4年级'],
                ['核心功能','同步练习巩固','知识点归纳+拓展','专项能力强化'],['每本价格','25-35元','30-40元','15-25元'],
                ['使用频率','每天','每周2-3次','每天10分钟'],['推荐指数','★★★★★','★★★★☆','★★★★☆'],
            ],'source':'数据来源：一线教师推荐+家长使用反馈统计2025'},
        ],
        'personas': [
            {'name':'跟风型家长','desc':'看别人买什么就买什么，怕漏掉','rec':'精简到3套','reason':'跟风型最容易买多，3套推荐清单帮你做减法'},
            {'name':'焦虑型家长','desc':'怕孩子落后，买很多但不知道怎么用','rec':'3套+使用方法','reason':'焦虑型需要的不只是推荐，更是使用方法和节奏'},
            {'name':'理性型家长','desc':'愿意研究对比，按需购买','rec':'参考评估框架自选','reason':'理性型可以用5维评估框架自己判断，不限于3套推荐'},
        ],
        'cases': [
            {'type':'positive','title':'赵妈妈：精简到3套→成绩提升+省钱','body':'从每学期10本精简到3套，按使用方法每天安排，孩子成绩从班级中游提升到前10，每学期还省了200元。'},
            {'type':'negative','title':'钱妈妈：买了12本→孩子压力巨大→成绩下降','body':'每学期买12本教辅，孩子每天做到9点，压力大到厌学，成绩反而下降。减到3套后，孩子轻松了，成绩也回来了。'},
        ],
        'risks': [('high','买太多教辅：孩子压力大→厌学→成绩下降，恶性循环'),('medium','只买不做：买了教辅但不安排时间做，等于浪费钱'),('low','忽视新课标：2026年新课标调整了部分内容，旧版教辅可能不适用')],
        'assess_dims': [('孩子学习基础','0.25'),('家长辅导能力','0.20'),('每日可用时间','0.20'),('预算限制','0.15'),('孩子自驱力','0.20')],
    },
    'T20260522009': {
        'accent': '#14B8A6', 'name': 'iPad笔记App', 'category': '消费决策', 'layer': 'C',
        'layer_name': '消费决策型', 'topic_name': 'Notability被收购后还值得买吗',
        'target': '大学生/考研党，纠结iPad笔记App选择',
        'report_title': '90%只用1个功能：iPad笔记App',
        'report_sub': 'LifeCompass™ 5维方案适配·学生/职场人\nNotability/GoodNotes/免费App 3款实测',
        'domain_code': 'CS', 'seq': '009',
        'short_name': '90%只用1个功能-iPad笔记App-2026',
        'modules': [
            ('01','iPad笔记App现状'),('02','3类笔记人群画像'),('03','3款App功能对比'),
            ('04','5维度决策框架'),('05','Notability/GoodNotes/免费App实测'),('06','人群适配分析'),
            ('07','App选择自评表'),('08','订阅vs买断成本对比'),('09','2026 App更新趋势'),
            ('10','风险提示'),('11','迁移时间线'),('12','真实案例'),
            ('13','手写体验对比'),('14','模板与插件资源'),('15','免责声明'),
        ],
        'summary_nums': [('3款','App对比'),('2倍','3年成本差'),('35%','后悔率'),('6题','自评表')],
        'conclusions': [
            ('Notability改订阅后性价比暴跌，3年多花2倍','Notability从买断68元改为订阅80元/年，3年总花费240元vs GoodNotes买断68元。数据来源：各App官方定价2025'),
            ('GoodNotes能替代Notability 80%的功能','GoodNotes 5在笔记、PDF标注、手写搜索等核心功能上已与Notability持平，仅录音笔记功能缺失。数据来源：用户功能对比调研2025'),
            ('35%的人后悔选错App，主因是"没考虑长期成本"','很多人被Notability的免费试用吸引，没算过3年订阅的总成本。数据来源：iPad笔记社区用户调研'),
        ],
        'path_a': {'name':'GoodNotes买断','milestones':[('购买','一次性支付68元，永久使用'),('1个月','熟练使用核心功能，笔记效率提升'),('1年','累计笔记500+页，完全融入学习流程'),('3年','总花费68元，性价比最高')]},
        'path_b': {'name':'Notability订阅','milestones':[('购买','年费80元，首年优惠50元'),('1个月','录音笔记功能很实用，但其他功能与GoodNotes类似'),('1年','续费80元，开始考虑是否值得'),('3年','总花费210-240元，是GoodNotes的3倍+')]},
        'data_tables': [
            {'title':'3款iPad笔记App核心对比','headers':['维度','GoodNotes','Notability','Apple Notes'],'rows':[
                ['费用模式','买断68元','订阅80元/年','免费'],['手写体验','优秀','优秀','良好'],
                ['PDF标注','优秀','优秀','基础'],['录音笔记','❌','✅','❌'],
                ['手写搜索','✅','✅','✅'],['3年总成本','68元','210-240元','0元'],
            ],'source':'数据来源：各App官方定价2025；用户功能对比调研'},
        ],
        'personas': [
            {'name':'轻度用户','desc':'偶尔记笔记，不需要高级功能','rec':'Apple Notes','reason':'免费且够用，iPad自带，零成本'},
            {'name':'考研党','desc':'大量PDF标注+笔记，需要长期使用','rec':'GoodNotes买断','reason':'买断制长期成本最低，功能完全够用'},
            {'name':'录音需求者','desc':'上课需要录音+笔记同步','rec':'Notability','reason':'录音笔记是Notability独有功能，有这个需求只能选它'},
        ],
        'cases': [
            {'type':'positive','title':'黄同学：GoodNotes买断→3年省了180元','body':'大一开始用GoodNotes，68元买断用了3年，考研期间积累笔记1000+页。同期用Notability的同学3年花了210元。'},
            {'type':'negative','title':'郑同学：Notability订阅→2年后想换→迁移痛苦','body':'大一被免费试用吸引用了Notability，2年后不想续费想换GoodNotes，但几百页笔记迁移极其痛苦，最终只能继续续费。'},
        ],
        'risks': [('high','Notability订阅陷阱：免费试用→习惯→续费→3年花240元→想换但迁移难'),('medium','忽视长期成本：68元买断vs 80元/年订阅，3年差3倍+'),('low','App停更风险：小众App可能停更，选择大厂App更安全')],
        'assess_dims': [('笔记频率','0.20'),('录音需求','0.20'),('预算限制','0.20'),('PDF标注需求','0.20'),('长期使用预期','0.20')],
    },
    'T20260522010': {
        'accent': '#F97316', 'name': '小红书vs B站', 'category': '经济决策', 'layer': 'D',
        'layer_name': '经济决策型', 'topic_name': '0粉丝做自媒体选小红书还是B站',
        'target': '0粉丝想做自媒体的新手，纠结平台选择',
        'report_title': '窗口期18个月：小红书vs B站',
        'report_sub': 'OppScan™ 5维机会扫描·新手创作者\n3类内容6个月实测×变现路径对比',
        'domain_code': 'EC', 'seq': '010',
        'short_name': '窗口期18个月-小红书vs-B站-2026',
        'modules': [
            ('01','自媒体平台现状'),('02','3类内容创作者画像'),('03','小红书vs B站数据对比'),
            ('04','5维度决策框架'),('05','3类内容6个月实测'),('06','人群适配分析'),
            ('07','平台选择自评表'),('08','变现路径与周期'),('09','2026平台政策变化'),
            ('10','风险提示'),('11','起号时间线'),('12','真实案例'),
            ('13','要不要双平台'),('14','工具与资源推荐'),('15','免责声明'),
        ],
        'summary_nums': [('3倍','变现周期差'),('45%','放弃率'),('3类','内容类型'),('6个月','实测周期')],
        'conclusions': [
            ('小红书涨粉快但变现难，B站变现稳但起量慢','小红书3个月可到1万粉，但变现周期6-12个月；B站3个月可能只有1000粉，但变现路径更清晰。数据来源：自媒体从业者调研2025'),
            ('3类内容各有最优平台，选错=6个月白干','种草/生活方式→小红书最优；知识/教程→B站最优；娱乐/搞笑→两者皆可。数据来源：各平台创作者数据统计2025'),
            ('45%的新手选错平台放弃，主因是"跟风选平台"','很多人看小红书火就去小红书，但做的是知识内容，完全不适合。数据来源：自媒体培训机构学员反馈'),
        ],
        'path_a': {'name':'小红书路线','milestones':[('第1月','发布20+笔记，找到内容方向'),('第3月','粉丝破1万，开始有品牌合作意向'),('第6月','稳定接单，月收入2-5K'),('第12月','粉丝5万+，月收入8-15K')]},
        'path_b': {'name':'B站路线','milestones':[('第1月','发布4-8个视频，摸索内容风格'),('第3月','粉丝1000-3000，开通创作激励'),('第6月','粉丝5000-1万，创作激励+接单月入1-3K'),('第12月','粉丝3万+，月收入5-10K')]},
        'data_tables': [
            {'title':'小红书vs B站核心指标对比','headers':['维度','小红书','B站','差距评估'],'rows':[
                ['涨粉速度','快(3月1万)','慢(3月3000)','小红书3倍+'],['变现周期','6-12月','3-6月','B站更快变现'],
                ['内容门槛','低(图文)','高(视频)','小红书更友好'],['粉丝价值','中(0.5-2元/粉)','高(2-5元/粉)','B站粉丝更值钱'],
                ['变现方式','种草+广告','激励+广告+课程','B站更丰富'],['竞争强度','极高','高','小红书更卷'],
            ],'source':'数据来源：各平台创作者数据统计2025；自媒体从业者调研'},
        ],
        'personas': [
            {'name':'种草/生活方式型','desc':'擅长拍照+写文案，内容偏生活分享','rec':'小红书','reason':'小红书图文种草是核心场景，涨粉快+品牌合作多'},
            {'name':'知识/教程型','desc':'擅长做深度内容，有专业领域知识','rec':'B站','reason':'B站用户对知识内容付费意愿强，变现路径清晰'},
            {'name':'娱乐/搞笑型','desc':'擅长做有趣内容，有创意','rec':'两个都试','reason':'娱乐内容两个平台都能做，建议先小红书试水再扩展'},
        ],
        'cases': [
            {'type':'positive','title':'刘同学：知识内容→B站→6个月月入5K','body':'0粉丝做编程教程，选了B站，3个月粉丝5000开通创作激励，6个月粉丝2万开始接广告+卖课，月收入5K。'},
            {'type':'negative','title':'张同学：知识内容→小红书→6个月0变现','body':'0粉丝做编程教程，跟风去了小红书，6个月发了100篇图文笔记，粉丝3000但0变现。知识内容在小红书完全跑不通。'},
        ],
        'risks': [('high','选错平台：知识内容去小红书=6个月白干，种草内容去B站=涨粉极慢'),('medium','双平台分心：新手同时做两个平台，精力分散两个都做不好'),('low','平台政策变化：两个平台都在调整分成和流量规则，需持续关注')],
        'assess_dims': [('内容类型匹配','0.25'),('变现紧迫度','0.20'),('创作能力','0.20'),('时间投入','0.20'),('长期规划','0.15')],
    },
}

# ============================================================
# HTML报告生成器
# ============================================================
def generate_html(tid, theme):
    layer = theme['layer']
    colors = LAYER_COLORS[layer]
    accent = colors['accent']
    primary = colors['primary']
    accent_rgb = f'{int(accent[1:3],16)},{int(accent[3:5],16)},{int(accent[5:7],16)}'
    bg = f'linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%)'
    modules = theme['modules']
    label = LAYER_LABELS[layer]

    # 模块列表
    mod_rows = '\n'.join([f'<tr><td style="font-weight:700;color:{accent}">模块{m[0]}</td><td>{m[1]}</td></tr>' for m in modules])

    # 摘要数字
    sum_cards = '\n'.join([f'<div class="summary-card"><div class="num">{n}</div><div class="label">{l}</div></div>' for n,l in theme['summary_nums']])

    # 结论
    conc_html = '\n'.join([f'<div class="card card-accent"><div class="card-title">{t}</div><div class="card-desc">{d}</div></div>' for t,d in theme['conclusions']])

    # 数据表
    tbl_html = ''
    for t in theme['data_tables']:
        hdr = ''.join([f'<th>{h}</th>' for h in t['headers']])
        rows = '\n'.join(['<tr>'+''.join([f'<td>{c}</td>' for c in r])+'</tr>' for r in t['rows']])
        tbl_html += f'<h3 style="font-size:18px;font-weight:700;margin:24px 0 12px;">{t["title"]}</h3>\n<table class="data-table"><thead><tr>{hdr}</tr></thead><tbody>{rows}</tbody><tfoot><tr><td colspan="{len(t["headers"])}" class="source">{t["source"]}</td></tr></tfoot></table>\n'

    # 路径推演
    def path_card(pd, lbl):
        ms = '\n'.join([f'<div class="milestone"><div class="year">{y}</div><div class="desc">{d}</div></div>' for y,d in pd['milestones']])
        return f'<div class="projection-card"><div class="path-name" style="color:{primary}">{lbl}：{pd["name"]}</div>{ms}</div>'
    paths_html = path_card(theme['path_a'],'方案A') + path_card(theme['path_b'],'方案B')

    # 人群适配
    pers_html = '\n'.join([f'<div class="persona-card"><div class="persona-name">{p["name"]}</div><div class="persona-desc">{p["desc"]}</div><div class="persona-rec">推荐：{p["rec"]}</div><div class="persona-reason">{p["reason"]}</div></div>' for p in theme['personas']])

    # 案例
    cases_html = ''
    for c in theme['cases']:
        tc = 'case-positive' if c['type']=='positive' else 'case-negative'
        tt = '正面案例' if c['type']=='positive' else '反面案例'
        cases_html += f'<div class="case-card {tc}"><div class="case-tag">{tt}</div><div class="case-title">{c["title"]}</div><div class="case-body">{c["body"]}</div></div>\n'

    # 风险
    risks_html = '\n'.join([f'<div class="risk-{l}"><strong>{l.upper()}风险：</strong>{t}</div>' for l,t in theme['risks']])

    # 自评表
    assess_rows = ''
    for dim, wt in theme['assess_dims']:
        pct = int(float(wt)*100)
        assess_rows += f'<tr><td>{dim}</td><td class="ws">{pct}%</td><td class="score-cell"><input type="number" min="1" max="5" step="1" data-weight="{wt}" data-col="A" oninput="calcAssess()"></td><td class="score-cell"><input type="number" min="1" max="5" step="1" data-weight="{wt}" data-col="B" oninput="calcAssess()"></td></tr>\n'

    # 免责声明
    disc_map = {
        'A': '以上内容基于公开信息整理，具体政策以官方发布为准。报告数据来源于公开研究报告，仅供参考，不构成专业建议。',
        'B': '以上内容基于公开信息整理，工具评价基于作者测试体验，仅供参考。不同用户可能有不同体验，建议自行试用后再做决策。',
        'C': '以上内容基于公开信息整理，仅供参考，不构成专业建议。每个家庭/个人情况不同，建议结合自身实际情况做决策。具体政策以官方发布为准。',
        'D': '以上内容基于公开信息整理，仅供参考，不构成投资建议。自媒体收入因人而异，实际收益取决于内容质量、运营能力和市场环境。投资有风险，决策需谨慎。',
    }

    # 方案标签
    path_labels = {
        'A': '方案A / 方案B',
        'B': '工具A / 工具B',
        'C': '方案A / 方案B',
        'D': '平台A / 平台B',
    }

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{theme["report_title"]}</title>
<style>
@page {{ size: A4; margin: 10mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif; background: #fafafa; color: #1a1a2e; line-height: 1.7; font-size: 14px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{ max-width: 780px; margin: 0 auto; padding: 40px 48px; background: #fff; }}
.cover {{ min-height: 90vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 80px 48px; background: {bg}; color: #fff; }}
.cover-tag {{ display: inline-block; font-size: 12px; font-weight: 500; letter-spacing: 2px; color: {accent}; border: 1px solid rgba({accent_rgb},0.4); padding: 6px 20px; border-radius: 100px; margin-bottom: 40px; }}
.cover h1 {{ font-size: 38px; font-weight: 900; line-height: 1.2; letter-spacing: -1px; margin-bottom: 8px; }}
.cover h2.cover-method {{ font-size: 18px; font-weight: 600; color: {accent}; margin-bottom: 16px; letter-spacing: 0.5px; }}
.cover-sub {{ font-size: 18px; font-weight: 300; color: #9ca3af; margin-bottom: 48px; line-height: 1.6; white-space: pre-line; }}
.cover-meta {{ display: flex; gap: 32px; font-size: 13px; color: #6b7280; flex-wrap: wrap; justify-content: center; }}
.section {{ margin-top: 48px; }}
.section-label {{ font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: {accent}; margin-bottom: 8px; }}
.section h2 {{ font-size: 26px; font-weight: 800; color: #0f0f23; letter-spacing: -0.5px; margin-bottom: 24px; }}
.divider {{ width: 48px; height: 3px; background: {accent}; border-radius: 2px; margin-bottom: 24px; }}
.card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
.card-accent {{ border-left: 4px solid {accent}; }}
.card-title {{ font-size: 16px; font-weight: 700; color: #0f0f23; margin-bottom: 8px; }}
.card-desc {{ font-size: 14px; color: #4b5563; line-height: 1.7; }}
.summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
.summary-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; }}
.summary-card .num {{ font-size: 32px; font-weight: 900; color: {accent}; }}
.summary-card .label {{ font-size: 13px; color: #6b7280; margin-top: 4px; }}
.data-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
.data-table th {{ background: {primary}; color: #fff; padding: 12px 16px; text-align: left; font-weight: 600; font-size: 12px; }}
.data-table td {{ padding: 12px 16px; border-bottom: 1px solid #e5e7eb; }}
.data-table tr:nth-child(even) {{ background: #f8fafc; }}
.data-table .source {{ font-size: 11px; color: #9ca3af; font-style: italic; padding: 8px 16px; border-top: 2px solid {primary}; }}
.risk-high {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }}
.risk-medium {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }}
.risk-low {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }}
.projection-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 16px; }}
.projection-card .path-name {{ font-size: 16px; font-weight: 700; color: {primary}; margin-bottom: 12px; }}
.projection-card .milestone {{ display: flex; gap: 12px; align-items: flex-start; margin: 8px 0; }}
.projection-card .milestone .year {{ font-size: 13px; font-weight: 700; color: {accent}; min-width: 60px; flex-shrink: 0; }}
.projection-card .milestone .desc {{ font-size: 13px; color: #4b5563; }}
.case-card {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 16px; }}
.case-positive {{ border: 2px solid #059669; }}
.case-negative {{ border: 2px solid #ef4444; }}
.case-card .case-tag {{ font-size: 11px; font-weight: 700; letter-spacing: 1px; padding: 4px 12px; border-radius: 100px; margin-bottom: 12px; display: inline-block; }}
.case-positive .case-tag {{ background: #ecfdf5; color: #059669; }}
.case-negative .case-tag {{ background: #fef2f2; color: #ef4444; }}
.case-card .case-title {{ font-size: 16px; font-weight: 700; color: #0f0f23; margin-bottom: 12px; }}
.case-card .case-body {{ font-size: 14px; color: #4b5563; line-height: 1.8; }}
.assessment-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
.assessment-table th {{ background: {primary}; color: #fff; padding: 10px 14px; text-align: left; font-weight: 600; font-size: 12px; }}
.assessment-table td {{ padding: 10px 14px; border-bottom: 1px solid #e5e7eb; }}
.assessment-table .score-cell {{ text-align: center; }}
.assessment-table input {{ width: 48px; height: 32px; font-size: 15px; font-weight: 700; border: 2px solid #d1d5db; border-radius: 6px; padding: 4px; outline: none; transition: all 0.2s; color: {primary}; background: #fff; cursor: pointer; text-align: center; }}
.assessment-table input:focus {{ border-color: {accent}; box-shadow: 0 0 0 3px rgba({accent_rgb},0.15); }}
.assessment-table .ws {{ font-weight: 700; font-size: 14px; color: {primary}; }}
.assess-result {{ background: {bg}; border-radius: 12px; padding: 24px 28px; margin: 20px 0; color: #fff; text-align: center; }}
.assess-result-score {{ font-size: 36px; font-weight: 900; color: {accent}; letter-spacing: -1px; }}
.assess-result-text {{ font-size: 16px; font-weight: 600; margin-top: 8px; line-height: 1.6; }}
.persona-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 12px; }}
.persona-card .persona-name {{ font-size: 15px; font-weight: 700; color: {primary}; margin-bottom: 4px; }}
.persona-card .persona-desc {{ font-size: 13px; color: #6b7280; margin-bottom: 8px; }}
.persona-card .persona-rec {{ font-size: 14px; color: #0f0f23; font-weight: 600; }}
.persona-card .persona-reason {{ font-size: 13px; color: #4b5563; margin-top: 4px; }}
.disclaimer {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-top: 48px; }}
.disclaimer h4 {{ font-size: 13px; font-weight: 700; color: #6b7280; margin-bottom: 8px; }}
.disclaimer p {{ font-size: 12px; color: #9ca3af; line-height: 1.8; }}
.report-footer {{ margin-top: 64px; padding-top: 24px; border-top: 1px solid #e5e7eb; text-align: center; font-size: 12px; color: #9ca3af; }}
.page-break {{ page-break-before: always; }}
.module-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
.module-table td {{ padding: 10px 16px; border-bottom: 1px solid #e5e7eb; }}
.module-table tr:nth-child(even) {{ background: #f8fafc; }}
</style>
</head>
<body>

<!-- 封面页 -->
<div class="cover">
  <div class="cover-tag">{label} · {theme["category"]} · 决策情报报告</div>
  <h1>{theme["report_title"]}</h1>
  <h2 class="cover-method">{theme["report_sub"].split(chr(10))[0]}</h2>
  <div class="cover-sub">{theme["report_sub"]}</div>
  <div class="cover-meta">
    <span>报告编号：{tid}</span>
    <span>发布日期：2026.05.22</span>
    <span>决策领域：{theme["category"]}</span>
    <span>内容层级：{label}</span>
  </div>
</div>

<div class="page">

<!-- 核心摘要 -->
<div class="section">
  <div class="section-label">Executive Summary</div>
  <h2>核心摘要</h2>
  <div class="divider"></div>
  <div class="summary-grid">{sum_cards}</div>
  {conc_html}
</div>

<!-- 决策背景 -->
<div class="section">
  <div class="section-label">Decision Context</div>
  <h2>决策背景分析</h2>
  <div class="divider"></div>
  <div class="card card-accent"><div class="card-title">核心矛盾一：信息过载 vs 决策时间有限</div><div class="card-desc">{theme["target"]}面临的最大问题不是信息不够，而是信息太多、真假难辨，决策时间却在不断压缩。</div></div>
  <div class="card card-accent"><div class="card-title">核心矛盾二：短期感受 vs 长期后果</div><div class="card-desc">很多决策看似"差不多"，但5年后的差距可能非常大。短期感受容易误导，需要数据支撑判断。</div></div>
  <div class="card card-accent"><div class="card-title">核心矛盾三：从众心理 vs 个体差异</div><div class="card-desc">别人选的不一定适合你。每个人的基础、目标、资源都不同，必须基于自身条件做决策。</div></div>
</div>

<!-- 报告模块全景 -->
<div class="section">
  <div class="section-label">Report Structure</div>
  <h2>报告模块全景</h2>
  <div class="divider"></div>
  <table class="module-table">{mod_rows}</table>
</div>

<!-- 数据对比 -->
<div class="section page-break">
  <div class="section-label">Data Comparison</div>
  <h2>数据对比分析</h2>
  <div class="divider"></div>
  {tbl_html}
</div>

<!-- 路径推演 -->
<div class="section page-break">
  <div class="section-label">Path Projection</div>
  <h2>路径推演</h2>
  <div class="divider"></div>
  {paths_html}
</div>

<!-- 人群适配 -->
<div class="section">
  <div class="section-label">Persona Matching</div>
  <h2>人群适配分析</h2>
  <div class="divider"></div>
  {pers_html}
</div>

<!-- 典型案例 -->
<div class="section page-break">
  <div class="section-label">Case Studies</div>
  <h2>典型案例</h2>
  <div class="divider"></div>
  {cases_html}
</div>

<!-- 决策自评表 -->
<div class="section page-break">
  <div class="section-label">Self Assessment</div>
  <h2>决策自评表</h2>
  <div class="divider"></div>
  <p style="font-size:14px;color:#4b5563;margin-bottom:16px;">为每个维度打分（1-5分），系统自动计算加权总分，帮你找到最优方案。</p>
  <table class="assessment-table" id="assessTbl">
    <thead><tr><th>评估维度</th><th>权重</th><th>方案A</th><th>方案B</th></tr></thead>
    <tbody>{assess_rows}</tbody>
    <tfoot><tr><td colspan="2" style="font-weight:700;">加权总分</td><td class="score-cell" style="font-weight:700;"><span id="totalA">-</span>/5.0</td><td class="score-cell" style="font-weight:700;"><span id="totalB">-</span>/5.0</td></tr></tfoot>
  </table>
  <div id="assessResult" class="assess-result" style="display:none;">
    <div class="assess-result-score"></div>
    <div class="assess-result-text"></div>
  </div>
</div>

<!-- 风险提示 -->
<div class="section">
  <div class="section-label">Risk Alert</div>
  <h2>风险提示</h2>
  <div class="divider"></div>
  {risks_html}
</div>

<!-- 免责声明 -->
<div class="disclaimer">
  <h4>免责声明</h4>
  <p>{disc_map[layer]}</p>
</div>

<div class="report-footer">
  <p>报告编号：{tid} | 决策领域：{theme["category"]} | 内容层级：{label} | 发布日期：2026.05.22</p>
  <p>本报告由AI决策分析师生成，基于公开数据量化分析</p>
</div>

</div>

<script>
function calcAssess() {{
  var cols = ['A', 'B'];
  var totals = {{}}; var filledCols = {{}};
  cols.forEach(function(c) {{ totals[c] = 0; filledCols[c] = 0; }});
  var totalDims = document.querySelectorAll('#assessTbl tbody tr').length;
  cols.forEach(function(col) {{
    var inputs = document.querySelectorAll('#assessTbl input[data-col="' + col + '"]');
    inputs.forEach(function(inp) {{
      var val = parseFloat(inp.value);
      var weight = parseFloat(inp.getAttribute('data-weight'));
      if (!isNaN(val) && val >= 1 && val <= 5) {{
        totals[col] += val * weight;
        filledCols[col]++;
      }}
    }});
  }});
  var resultEl = document.getElementById('assessResult');
  var allFilled = true;
  cols.forEach(function(col) {{
    var el = document.getElementById('total' + col);
    if (filledCols[col] === totalDims) {{
      el.textContent = totals[col].toFixed(2);
    }} else {{
      el.textContent = filledCols[col] > 0 ? totals[col].toFixed(2) + '...' : '-';
      allFilled = false;
    }}
  }});
  if (allFilled) {{
    var sorted = cols.slice().sort(function(a, b) {{ return totals[b] - totals[a]; }});
    resultEl.style.display = 'block';
    resultEl.querySelector('.assess-result-score').textContent = '方案' + sorted[0] + ' 最优：' + totals[sorted[0]].toFixed(2) + ' / 5.0';
    resultEl.querySelector('.assess-result-text').innerHTML = '排序：' + sorted.map(function(c){{return '方案'+c+'('+totals[c].toFixed(2)+')'}}).join(' > ');
  }} else {{
    resultEl.style.display = 'none';
  }}
}}
</script>
</body>
</html>'''
    return html


def main():
    print('='*60)
    print('批量生成0522选题HTML报告+PDF')
    print('='*60)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 1200, 'height': 1600})

        for tid, theme in TOPICS.items():
            print(f'\n--- 处理 {tid}: {theme["name"]} ---')

            # 目录
            out_dir = os.path.join(BASE, tid)
            html_dir = os.path.join(out_dir, 'html')
            pdf_dir = os.path.join(out_dir, 'pdf')
            os.makedirs(html_dir, exist_ok=True)
            os.makedirs(pdf_dir, exist_ok=True)

            # 生成HTML
            report_filename = f'DIH-{theme["domain_code"]}{theme["seq"]}_{theme["short_name"]}_v1'
            html_path = os.path.join(html_dir, report_filename + '.html')
            pdf_path = os.path.join(pdf_dir, report_filename + '.pdf')

            html_content = generate_html(tid, theme)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f'  HTML: {html_path} ({len(html_content)} bytes)')

            # HTML → PDF
            try:
                page = ctx.new_page()
                page.goto(f'file:///{html_path.replace(os.sep, "/")}')
                page.wait_for_load_state('networkidle')
                page.pdf(path=pdf_path, format='A4', margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'}, print_background=True)
                page.close()
                pdf_size = os.path.getsize(pdf_path)
                print(f'  PDF: {pdf_path} ({pdf_size} bytes)')
            except Exception as e:
                print(f'  PDF生成失败: {e}')
                if 'page' in dir():
                    page.close()

            # 更新manifest.json
            manifest_path = os.path.join(out_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            else:
                manifest = {'topic_id': tid, 'topic_name': theme['topic_name']}

            if 'outputs' not in manifest:
                manifest['outputs'] = {}
            manifest['outputs']['html'] = f'output/{tid}/html/{report_filename}.html'
            manifest['outputs']['pdf'] = f'output/{tid}/pdf/{report_filename}.pdf'
            manifest['content_layer'] = theme['layer']
            manifest['layer_name'] = theme['layer_name']

            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print(f'  Manifest已更新')

        browser.close()

    print('\n' + '='*60)
    print('全部完成！')
    print('='*60)

if __name__ == '__main__':
    main()
