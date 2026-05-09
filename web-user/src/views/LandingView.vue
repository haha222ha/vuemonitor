<template>
  <div class="landing">
    <header class="nav" :class="{ scrolled: navScrolled }">
      <div class="nav-inner">
        <div class="logo">
          <span class="logo-mark">X</span>
          <span class="logo-text">XHS365</span>
        </div>
        <nav class="nav-links">
          <a href="#features">功能</a>
          <a href="#platforms">平台</a>
          <a href="#cases">案例</a>
          <a href="#pricing">价格</a>
        </nav>
        <div class="nav-actions">
          <router-link to="/login" class="btn-ghost">登录</router-link>
          <router-link to="/register" class="btn-primary">免费开始</router-link>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="hero-bg">
        <div class="hero-mesh"></div>
        <div class="hero-orb orb-1"></div>
        <div class="hero-orb orb-2"></div>
        <div class="hero-orb orb-3"></div>
        <div class="hero-grid-lines"></div>
      </div>
      <div class="hero-inner">
        <div class="hero-badge" v-observe>
          <span class="badge-pulse"></span>
          <span class="badge-dot"></span>
          AI驱动的选品决策系统
        </div>
        <h1 class="hero-title" v-observe>
          多源数据采集 + AI分析<br/>
          <span class="gradient-text">爆品预测引擎</span>
        </h1>
        <p class="hero-desc" v-observe>
          实时监控商品动态，AI智能分析趋势，提前7天发现潜力商品<br/>
          从数据采集到决策建议，一站式选品决策平台
        </p>
        <div class="hero-actions" v-observe>
          <router-link to="/register" class="btn-primary btn-lg">
            免费开始使用
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </router-link>
          <a href="#features" class="btn-outline btn-lg">了解更多</a>
        </div>
        <div class="hero-stats" v-observe>
          <div class="stat-item">
            <div class="stat-num" ref="stat1">0</div>
            <div class="stat-suffix">+</div>
            <div class="stat-label">监控商品</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num" ref="stat2">0</div>
            <div class="stat-suffix">%</div>
            <div class="stat-label">爆品预测准确率</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num" ref="stat3">0</div>
            <div class="stat-suffix">天</div>
            <div class="stat-label">提前发现潜力商品</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num" ref="stat4">0</div>
            <div class="stat-suffix">+</div>
            <div class="stat-label">每日新增监测</div>
          </div>
        </div>
        <div class="hero-preview" v-observe>
          <div class="preview-frame">
            <div class="preview-bar">
              <div class="preview-dots"><span></span><span></span><span></span></div>
              <div class="preview-url">app.xhs365.cn/dashboard</div>
            </div>
            <div class="preview-body">
              <div class="preview-sidebar">
                <div class="ps-item active"><div class="ps-icon"></div><div class="ps-text"></div></div>
                <div class="ps-item"><div class="ps-icon"></div><div class="ps-text"></div></div>
                <div class="ps-item"><div class="ps-icon"></div><div class="ps-text"></div></div>
                <div class="ps-item"><div class="ps-icon"></div><div class="ps-text"></div></div>
                <div class="ps-item"><div class="ps-icon"></div><div class="ps-text"></div></div>
              </div>
              <div class="preview-main">
                <div class="pm-topbar">
                  <div class="pm-search"></div>
                  <div class="pm-actions"><div class="pm-avatar"></div></div>
                </div>
                <div class="pm-cards">
                  <div class="pm-card" v-for="i in 4" :key="i">
                    <div class="pmc-label"></div>
                    <div class="pmc-value" :class="['s','m','','l'][i-1]"></div>
                    <div class="pmc-chart">
                      <div class="pmc-bar" v-for="j in 7" :key="j" :style="{height: (20 + Math.random()*70).toFixed(0) + '%'}"></div>
                    </div>
                  </div>
                </div>
                <div class="pm-chart-area">
                  <svg viewBox="0 0 400 100" class="pm-line-chart">
                    <defs>
                      <linearGradient id="heroChartFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="rgba(99,102,241,0.25)"/>
                        <stop offset="100%" stop-color="rgba(99,102,241,0)"/>
                      </linearGradient>
                    </defs>
                    <path d="M0,80 Q50,70 80,55 T160,45 T240,30 T320,35 T400,15 L400,100 L0,100Z" fill="url(#heroChartFill)"/>
                    <path d="M0,80 Q50,70 80,55 T160,45 T240,30 T320,35 T400,15" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round"/>
                    <path d="M0,90 Q50,85 80,80 T160,70 T240,65 T320,60 T400,50 L400,100 L0,100Z" fill="rgba(244,114,182,0.1)"/>
                    <path d="M0,90 Q50,85 80,80 T160,70 T240,65 T320,60 T400,50" fill="none" stroke="#f472b6" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.6"/>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="trust-section">
      <div class="trust-inner" v-observe>
        <p class="trust-label">受到各平台电商从业者信赖</p>
        <div class="trust-logos">
          <span class="trust-logo"><span class="trust-icon">📕</span>小红书</span>
          <span class="trust-logo"><span class="trust-icon">🛒</span>淘宝</span>
          <span class="trust-logo"><span class="trust-icon">🏪</span>京东</span>
          <span class="trust-logo"><span class="trust-icon">💰</span>拼多多</span>
          <span class="trust-logo"><span class="trust-icon">🎵</span>抖音</span>
          <span class="trust-logo"><span class="trust-icon">🎬</span>快手</span>
        </div>
      </div>
    </section>

    <section id="features" class="section features-section">
      <div class="section-inner">
        <div class="section-header" v-observe>
          <div class="section-tag">核心功能</div>
          <h2>从采集到分析，覆盖选品全链路</h2>
          <p>四大核心模块，构建你的智能选品闭环</p>
        </div>
        <div class="waterfall">
          <div class="waterfall-col">
            <div class="wf-card wf-card-tall" v-observe>
              <div class="wf-card-glow glow-indigo"></div>
              <div class="wf-card-content">
                <div class="wf-icon-wrap icon-indigo">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                </div>
                <h3>商品监控</h3>
                <p>添加关注的商品，实时追踪价格、销量、评价等关键指标变化。支持小红书、淘宝、京东、拼多多、抖音等多平台同步监控。</p>
                <div class="wf-tags">
                  <span class="wf-tag">小红书</span>
                  <span class="wf-tag">淘宝</span>
                  <span class="wf-tag">京东</span>
                  <span class="wf-tag">拼多多</span>
                  <span class="wf-tag">抖音</span>
                </div>
                <div class="wf-mock-monitor">
                  <div class="mock-row" v-for="i in 5" :key="i">
                    <div class="mock-dot" :class="{ up: i % 3 !== 0, down: i % 3 === 0 }"></div>
                    <div class="mock-bar" :style="{width: (35 + Math.random()*55).toFixed(0) + '%'}"></div>
                    <div class="mock-val">{{ i % 3 !== 0 ? '↑' : '↓' }} {{ (Math.random()*30).toFixed(1) }}%</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="wf-card" v-observe>
              <div class="wf-card-glow glow-pink"></div>
              <div class="wf-card-content">
                <div class="wf-icon-wrap icon-pink">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 0 1 4 4c0 1.95-1.4 3.58-3.25 3.93"/><path d="M8.56 6.22A4 4 0 0 1 12 2"/><path d="M15 8a4 4 0 0 1 1 2.5"/><path d="M12 12v10"/><path d="M8 22h8"/></svg>
                </div>
                <h3>AI智能分析</h3>
                <p>基于采集数据，AI自动生成趋势评分、爆品预测、风险预警等决策建议，让数据驱动你的每一个选品决策。</p>
                <div class="wf-ai-score">
                  <div class="ai-ring">
                    <svg viewBox="0 0 80 80">
                      <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="6"/>
                      <circle cx="40" cy="40" r="34" fill="none" stroke="url(#scoreGrad)" stroke-width="6" stroke-dasharray="160 214" stroke-linecap="round" transform="rotate(-90 40 40)"/>
                      <defs><linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#6366f1"/><stop offset="100%" stop-color="#f472b6"/></linearGradient></defs>
                    </svg>
                    <div class="ai-num">85</div>
                  </div>
                  <div class="ai-labels">
                    <span class="ai-label"><span class="dot dot-green"></span>流量评分 92</span>
                    <span class="ai-label"><span class="dot dot-blue"></span>增长评分 88</span>
                    <span class="ai-label"><span class="dot dot-purple"></span>竞争评分 76</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="waterfall-col">
            <div class="wf-card" v-observe>
              <div class="wf-card-glow glow-purple"></div>
              <div class="wf-card-content">
                <div class="wf-icon-wrap icon-purple">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <h3>定时采集</h3>
                <p>自动定时获取最新数据，无需手动刷新。支持5分钟到自定义间隔的灵活配置，数据采集永不停歇。</p>
                <div class="wf-progress">
                  <div class="progress-row">
                    <span class="progress-label">采集频率</span>
                    <div class="progress-bar"><div class="progress-fill" style="width:85%"></div></div>
                    <span class="progress-val">5min</span>
                  </div>
                  <div class="progress-row">
                    <span class="progress-label">数据完整度</span>
                    <div class="progress-bar"><div class="progress-fill" style="width:98%"></div></div>
                    <span class="progress-val">98%</span>
                  </div>
                  <div class="progress-row">
                    <span class="progress-label">稳定性</span>
                    <div class="progress-bar"><div class="progress-fill" style="width:99%"></div></div>
                    <span class="progress-val">99%</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="wf-card wf-card-tall" v-observe>
              <div class="wf-card-glow glow-blue"></div>
              <div class="wf-card-content">
                <div class="wf-icon-wrap icon-blue">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
                </div>
                <h3>数据看板</h3>
                <p>可视化展示监控数据、趋势图表、AI评分，一目了然掌握商品动态。支持自定义看板布局和数据导出。</p>
                <div class="wf-chart">
                  <div class="chart-area">
                    <svg viewBox="0 0 200 60" preserveAspectRatio="none" class="chart-svg">
                      <defs>
                        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stop-color="rgba(99,102,241,0.3)"/>
                          <stop offset="100%" stop-color="rgba(99,102,241,0)"/>
                        </linearGradient>
                      </defs>
                      <path d="M0,50 L30,42 L60,45 L90,30 L120,35 L150,18 L180,22 L200,10 L200,60 L0,60Z" fill="url(#chartFill)"/>
                      <path d="M0,50 L30,42 L60,45 L90,30 L120,35 L150,18 L180,22 L200,10" fill="none" stroke="#6366f1" stroke-width="2"/>
                    </svg>
                  </div>
                  <div class="chart-legend">
                    <span class="legend-item"><span class="legend-dot" style="background:#6366f1"></span>销量趋势</span>
                    <span class="legend-item"><span class="legend-dot" style="background:#f472b6"></span>价格走势</span>
                  </div>
                </div>
                <div class="wf-dashboard-grid">
                  <div class="mini-dash-card" v-for="i in 4" :key="i">
                    <div class="mini-dash-label">{{ ['日销量','均价','评分','排名'][i-1] }}</div>
                    <div class="mini-dash-value">{{ ['2,847','¥89.5','4.8','Top3'][i-1] }}</div>
                    <div class="mini-dash-change" :class="{up: i!==4, down: i===4}">{{ ['+12.5%','-3.2%','+0.3%','-2'][i-1] }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="platforms" class="section platforms-section">
      <div class="section-inner">
        <div class="section-header" v-observe>
          <div class="section-tag">多平台支持</div>
          <h2>一个平台，覆盖全渠道数据</h2>
          <p>无缝对接主流电商平台，数据一站式管理</p>
        </div>
        <div class="platforms-waterfall">
          <div class="platform-card" v-observe>
            <div class="platform-card-inner platform-xhs">
              <div class="platform-icon">📕</div>
              <h3>小红书</h3>
              <p>笔记数据采集、商品销量追踪、达人分析、种草趋势监控</p>
              <div class="platform-features"><span>笔记监控</span><span>商品追踪</span><span>达人分析</span><span>趋势预警</span></div>
            </div>
          </div>
          <div class="platform-card" v-observe>
            <div class="platform-card-inner platform-taobao">
              <div class="platform-icon">🛒</div>
              <h3>淘宝/天猫</h3>
              <p>商品价格监控、销量趋势分析、竞品对比、店铺数据追踪</p>
              <div class="platform-features"><span>价格监控</span><span>销量分析</span><span>竞品对比</span><span>店铺追踪</span></div>
            </div>
          </div>
          <div class="platform-card" v-observe>
            <div class="platform-card-inner platform-jd">
              <div class="platform-icon">🏪</div>
              <h3>京东</h3>
              <p>商品评价分析、价格波动追踪、促销活动监控、库存预警</p>
              <div class="platform-features"><span>评价分析</span><span>价格追踪</span><span>促销监控</span><span>库存预警</span></div>
            </div>
          </div>
          <div class="platform-card" v-observe>
            <div class="platform-card-inner platform-pdd">
              <div class="platform-icon">💰</div>
              <h3>拼多多</h3>
              <p>爆款发现、拼团数据追踪、价格趋势、类目热度分析</p>
              <div class="platform-features"><span>爆款发现</span><span>拼团追踪</span><span>价格趋势</span><span>类目分析</span></div>
            </div>
          </div>
          <div class="platform-card" v-observe>
            <div class="platform-card-inner platform-douyin">
              <div class="platform-icon">🎵</div>
              <h3>抖音</h3>
              <p>短视频带货数据、直播间监控、达人带货分析、商品热度追踪</p>
              <div class="platform-features"><span>带货数据</span><span>直播监控</span><span>达人分析</span><span>热度追踪</span></div>
            </div>
          </div>
          <div class="platform-card" v-observe>
            <div class="platform-card-inner platform-kuaishou">
              <div class="platform-icon">🎬</div>
              <h3>快手</h3>
              <p>直播数据采集、商品销量监控、达人合作分析、选品推荐</p>
              <div class="platform-features"><span>直播数据</span><span>销量监控</span><span>达人合作</span><span>选品推荐</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="cases" class="section cases-section">
      <div class="section-inner">
        <div class="section-header" v-observe>
          <div class="section-tag">数据案例</div>
          <h2>真实数据，真实效果</h2>
          <p>来自真实用户的使用效果对比（数据已脱敏）</p>
        </div>
        <div class="cases-waterfall">
          <div class="case-col">
            <div class="case-card" v-observe>
              <div class="case-card-inner">
                <div class="case-header">
                  <div class="case-avatar">L</div>
                  <div><div class="case-name">林小姐 · 淘宝店主</div><div class="case-role">女装类目</div></div>
                </div>
                <div class="case-compare">
                  <div class="compare-item before">
                    <div class="compare-label">使用前</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val">2h</span><span class="metric-name">每日选品</span></div>
                      <div class="metric"><span class="metric-val">23%</span><span class="metric-name">爆款率</span></div>
                      <div class="metric"><span class="metric-val">3款</span><span class="metric-name">月上新</span></div>
                    </div>
                  </div>
                  <div class="compare-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></div>
                  <div class="compare-item after">
                    <div class="compare-label">使用后</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val highlight">20min</span><span class="metric-name">每日选品</span></div>
                      <div class="metric"><span class="metric-val highlight">67%</span><span class="metric-name">爆款率</span></div>
                      <div class="metric"><span class="metric-val highlight">12款</span><span class="metric-name">月上新</span></div>
                    </div>
                  </div>
                </div>
                <div class="case-improvement"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg> 选品效率提升 300%</div>
              </div>
            </div>
            <div class="case-card" v-observe>
              <div class="case-card-inner">
                <div class="case-header">
                  <div class="case-avatar" style="background:linear-gradient(135deg,#22c55e,#14b8a6)">Z</div>
                  <div><div class="case-name">张女士 · 小红书博主</div><div class="case-role">家居类目</div></div>
                </div>
                <div class="case-compare">
                  <div class="compare-item before">
                    <div class="compare-label">使用前</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val">3h</span><span class="metric-name">选品时间</span></div>
                      <div class="metric"><span class="metric-val">8%</span><span class="metric-name">爆文率</span></div>
                      <div class="metric"><span class="metric-val">5个</span><span class="metric-name">月合作</span></div>
                    </div>
                  </div>
                  <div class="compare-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></div>
                  <div class="compare-item after">
                    <div class="compare-label">使用后</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val highlight">30min</span><span class="metric-name">选品时间</span></div>
                      <div class="metric"><span class="metric-val highlight">35%</span><span class="metric-name">爆文率</span></div>
                      <div class="metric"><span class="metric-val highlight">18个</span><span class="metric-name">月合作</span></div>
                    </div>
                  </div>
                </div>
                <div class="case-improvement"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg> 爆文率提升 337%</div>
              </div>
            </div>
          </div>
          <div class="case-col">
            <div class="case-card" v-observe>
              <div class="case-card-inner">
                <div class="case-header">
                  <div class="case-avatar" style="background:linear-gradient(135deg,#f59e0b,#f97316)">W</div>
                  <div><div class="case-name">王先生 · 抖音带货</div><div class="case-role">食品类目</div></div>
                </div>
                <div class="case-compare">
                  <div class="compare-item before">
                    <div class="compare-label">使用前</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val">1.5h</span><span class="metric-name">选品调研</span></div>
                      <div class="metric"><span class="metric-val">15%</span><span class="metric-name">转化率</span></div>
                      <div class="metric"><span class="metric-val">¥2k</span><span class="metric-name">月利润</span></div>
                    </div>
                  </div>
                  <div class="compare-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></div>
                  <div class="compare-item after">
                    <div class="compare-label">使用后</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val highlight">15min</span><span class="metric-name">选品调研</span></div>
                      <div class="metric"><span class="metric-val highlight">42%</span><span class="metric-name">转化率</span></div>
                      <div class="metric"><span class="metric-val highlight">¥12k</span><span class="metric-name">月利润</span></div>
                    </div>
                  </div>
                </div>
                <div class="case-improvement"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg> 月利润提升 500%</div>
              </div>
            </div>
            <div class="case-card" v-observe>
              <div class="case-card-inner">
                <div class="case-header">
                  <div class="case-avatar" style="background:linear-gradient(135deg,#6366f1,#8b5cf6)">C</div>
                  <div><div class="case-name">陈总 · 电商团队</div><div class="case-role">多品类运营</div></div>
                </div>
                <div class="case-compare">
                  <div class="compare-item before">
                    <div class="compare-label">使用前</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val">5人</span><span class="metric-name">选品团队</span></div>
                      <div class="metric"><span class="metric-val">30%</span><span class="metric-name">选品成功率</span></div>
                      <div class="metric"><span class="metric-val">20款</span><span class="metric-name">月上新</span></div>
                    </div>
                  </div>
                  <div class="compare-arrow"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></div>
                  <div class="compare-item after">
                    <div class="compare-label">使用后</div>
                    <div class="compare-metrics">
                      <div class="metric"><span class="metric-val highlight">2人</span><span class="metric-name">选品团队</span></div>
                      <div class="metric"><span class="metric-val highlight">72%</span><span class="metric-name">选品成功率</span></div>
                      <div class="metric"><span class="metric-val highlight">65款</span><span class="metric-name">月上新</span></div>
                    </div>
                  </div>
                </div>
                <div class="case-improvement"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg> 人力成本降低 60%</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="pricing" class="section pricing-section">
      <div class="section-inner">
        <div class="section-header" v-observe>
          <div class="section-tag">价格方案</div>
          <h2>选择适合你的方案</h2>
          <p>从免费体验到专业级AI决策，灵活升级</p>
        </div>
        <div class="pricing-grid">
          <div class="pricing-card" v-observe>
            <div class="pricing-card-inner">
              <div class="pricing-plan">Free</div>
              <div class="pricing-name">免费版</div>
              <div class="pricing-price"><span class="price-amount">¥0</span><span class="price-period">/月</span></div>
              <div class="pricing-desc">体验核心功能，快速上手</div>
              <ul class="pricing-features">
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>3个商品监控</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>基础趋势图</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>手动采集</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>每日3次AI分析</li>
                <li class="disabled"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>爆品预测</li>
                <li class="disabled"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>风险预警</li>
              </ul>
              <router-link to="/register" class="btn-outline btn-block">免费开始</router-link>
            </div>
          </div>
          <div class="pricing-card pricing-popular" v-observe>
            <div class="pricing-badge">最受欢迎</div>
            <div class="pricing-card-inner">
              <div class="pricing-plan">Pro</div>
              <div class="pricing-name">专业版</div>
              <div class="pricing-price"><span class="price-amount">¥99</span><span class="price-period">/月</span></div>
              <div class="pricing-desc">AI驱动选品，效率翻倍</div>
              <ul class="pricing-features">
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>50个商品监控</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>高级趋势 + 对比</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>定时自动采集</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>无限AI分析</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>爆品预测</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>AI评分报告</li>
              </ul>
              <router-link to="/register" class="btn-primary btn-block">立即升级</router-link>
            </div>
          </div>
          <div class="pricing-card" v-observe>
            <div class="pricing-card-inner">
              <div class="pricing-plan">Premium</div>
              <div class="pricing-name">高级版</div>
              <div class="pricing-price"><span class="price-amount">¥299</span><span class="price-period">/月</span></div>
              <div class="pricing-desc">完整AI决策能力</div>
              <ul class="pricing-features">
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>无限商品监控</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>全维度数据分析</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>爆品预测 + 风险预警</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>多维评分体系</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>自定义看板</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>数据导出</li>
              </ul>
              <router-link to="/register" class="btn-outline btn-block">选择方案</router-link>
            </div>
          </div>
          <div class="pricing-card" v-observe>
            <div class="pricing-card-inner">
              <div class="pricing-plan">Enterprise</div>
              <div class="pricing-name">企业版</div>
              <div class="pricing-price"><span class="price-amount">定制</span><span class="price-period"></span></div>
              <div class="pricing-desc">私有部署 + 定制模型</div>
              <ul class="pricing-features">
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>全部Premium功能</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>API接口开放</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>私有化部署</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>定制AI模型</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>团队协作</li>
                <li><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>专属客服</li>
              </ul>
              <a href="mailto:contact@xhs365.cn" class="btn-outline btn-block">联系我们</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="cta-section">
      <div class="cta-inner" v-observe>
        <div class="cta-bg">
          <div class="cta-orb cta-orb-1"></div>
          <div class="cta-orb cta-orb-2"></div>
        </div>
        <h2>开始你的智能选品之旅</h2>
        <p>免费注册，立即体验AI驱动的选品决策</p>
        <div class="cta-actions">
          <router-link to="/register" class="btn-primary btn-lg">
            免费开始使用
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </router-link>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-top">
          <div class="footer-brand">
            <div class="logo">
              <span class="logo-mark">X</span>
              <span class="logo-text">XHS365</span>
            </div>
            <p>AI驱动的选品决策系统<br/>从数据采集到决策建议，一站式平台</p>
          </div>
          <div class="footer-links">
            <div class="footer-col">
              <h4>产品</h4>
              <a href="#features">核心功能</a>
              <a href="#pricing">价格方案</a>
              <a href="#platforms">平台支持</a>
            </div>
            <div class="footer-col">
              <h4>支持</h4>
              <a href="#">帮助中心</a>
              <a href="#">使用教程</a>
              <a href="#">API文档</a>
            </div>
            <div class="footer-col">
              <h4>法律</h4>
              <a href="#">服务条款</a>
              <a href="#">隐私政策</a>
              <a href="#">Cookie政策</a>
            </div>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2026 XHS365. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import "../assets/landing.css";

const navScrolled = ref(false);
const stat1 = ref<HTMLElement>();
const stat2 = ref<HTMLElement>();
const stat3 = ref<HTMLElement>();
const stat4 = ref<HTMLElement>();

const vObserve = {
  mounted(el: HTMLElement) {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("visible");
          observer.unobserve(el);
        }
      },
      { threshold: 0.06, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(el);
  },
};

function animateNumber(el: HTMLElement, target: number, suffix: string = "", duration: number = 2000) {
  const start = 0;
  const startTime = performance.now();
  function update(currentTime: number) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (target - start) * eased);
    el.textContent = current.toLocaleString() + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

const statsObserver = ref<IntersectionObserver>();

onMounted(() => {
  const handleScroll = () => {
    navScrolled.value = window.scrollY > 20;
  };
  window.addEventListener("scroll", handleScroll, { passive: true });

  statsObserver.value = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        if (stat1.value) animateNumber(stat1.value, 200000, "");
        if (stat2.value) animateNumber(stat2.value, 92, "");
        if (stat3.value) animateNumber(stat3.value, 7, "");
        if (stat4.value) animateNumber(stat4.value, 50000, "");
        statsObserver.value?.disconnect();
      }
    },
    { threshold: 0.3 }
  );

  const statsEl = document.querySelector(".hero-stats");
  if (statsEl) statsObserver.value.observe(statsEl);
});

onUnmounted(() => {
  statsObserver.value?.disconnect();
});
</script>
