import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ================= 配置区 =================
st.set_page_config(page_title="大宗商品全球量化联动系统", layout="wide", page_icon="🌍")

COMMODITIES = [
    "菜粕", "豆粕", "豆一", "豆二", "豆油", "菜油", 
    "生猪", "PVC", "锰硅", "硅铁", "纯碱", "玻璃", 
    "合成橡胶", "天然橡胶", "原油", "焦煤"
]

# 宏观与微观影响因子
MACRO_FACTORS = {
    "原油": {"合成橡胶": 0.95, "PVC": 0.75, "豆油": 0.85, "菜油": 0.80},
    "焦煤": {"锰硅": 0.90, "硅铁": 0.88, "PVC": 0.65}
}
MICRO_FACTORS = {
    "豆二": {"豆粕": 0.92, "豆油": -0.85, "菜粕": 0.60},
    "纯碱": {"玻璃": 0.95, "PVC": 0.20},
    "天然橡胶": {"合成橡胶": 0.70},
    "豆粕": {"生猪": 0.88, "菜粕": 0.75}
}
RELATION_DESC = {
    ("原油", "合成橡胶"): "极强正相关：原油→丁二烯→合成橡胶成本传导",
    ("原油", "豆油"): "极强正相关：生物柴油替代逻辑，能源属性强化",
    ("纯碱", "玻璃"): "极强正相关：上下游刚性成本传导，地产竣工链绑定",
    ("豆二", "豆粕"): "强正相关：进口大豆压榨成本直接推升",
    ("豆二", "豆油"): "强负相关：压榨跷跷板效应，油强粕弱",
    ("豆粕", "生猪"): "强正相关：饲料成本占养殖成本60%以上",
    ("焦煤", "锰硅"): "极强正相关：冶炼核心燃料，黑色系成本基石",
    ("天然橡胶", "合成橡胶"): "强替代博弈：价差过大触发轮胎厂配方调整",
}

# ================= 模拟历史数据生成 =================
@st.cache_data
def generate_mock_prices(symbol, days=365):
    np.random.seed(hash(symbol) % (2**32))
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq='B')
    prices = 100 + np.cumsum(np.random.randn(days) * 0.5)
    return pd.DataFrame({"date": dates, "price": prices})

# ================= 核心回测函数 =================
def calculate_rolling_correlation(symbol1, symbol2, window=30):
    df1 = generate_mock_prices(symbol1)
    df2 = generate_mock_prices(symbol2)
    merged = pd.merge(df1, df2, on='date', suffixes=(f'_{symbol1}', f'_{symbol2}'))
    merged[f'ret_{symbol1}'] = merged[f'price_{symbol1}'].pct_change()
    merged[f'ret_{symbol2}'] = merged[f'price_{symbol2}'].pct_change()
    merged['rolling_corr'] = merged[f'ret_{symbol1}'].rolling(window=window).corr(merged[f'ret_{symbol2}'])
    return merged.dropna()

# ================= 价差套利监控模块 =================
ARBITRAGE_STRATEGIES = {
    "大豆压榨利润": {"formula": "0.2 * 豆油 + 0.8 * 豆粕 - 1.0 * 豆二", "desc": "经典压榨套利：100%大豆 ≈ 18.5%豆油 + 78.5%豆粕 + 3%损耗", "components": ["豆油", "豆粕", "豆二"], "weights": [0.2, 0.8, -1.0]},
    "纯碱-玻璃成本价差": {"formula": "玻璃 - 1.2 * 纯碱", "desc": "上下游利润空间：玻璃价格扣除纯碱成本后的毛利空间", "components": ["玻璃", "纯碱"], "weights": [1.0, -1.2]},
    "豆菜粕替代价差": {"formula": "豆粕 - 1.0 * 菜粕", "desc": "饲料替代博弈：当价差过大时，饲料厂会增加菜粕替代比例", "components": ["豆粕", "菜粕"], "weights": [1.0, -1.0]}
}

def calculate_arbitrage(strategy_name):
    strategy = ARBITRAGE_STRATEGIES[strategy_name]
    dfs = [generate_mock_prices(sym) for sym in strategy["components"]]
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on='date', suffixes=('', '_y'))
        merged = merged.loc[:, ~merged.columns.str.endswith('_y')]
    merged['spread'] = 0
    for comp, weight in zip(strategy["components"], strategy["weights"]):
        merged['spread'] += merged[f'price_{comp}'] * weight if f'price_{comp}' in merged.columns else merged['price'] * weight
    merged['mean'] = merged['spread'].expanding().mean()
    merged['std'] = merged['spread'].expanding().std()
    merged['z_score'] = (merged['spread'] - merged['mean']) / merged['std']
    return merged

# ================= 多因子择时模块 =================
def calculate_timing_factors():
    dates = pd.date_range(end=pd.Timestamp.today(), periods=100, freq='B')
    np.random.seed(42)
    data = {
        "date": dates,
        "估值因子": np.random.uniform(-0.5, 0.8, 100),
        "资金因子": np.random.uniform(-0.8, 0.9, 100),
        "情绪因子": np.random.uniform(-0.9, 0.9, 100),
        "基本面因子": np.random.uniform(-0.6, 0.7, 100),
        "技术因子": np.random.uniform(-0.7, 0.8, 100),
    }
    df = pd.DataFrame(data)
    factor_cols = ["估值因子", "资金因子", "情绪因子", "基本面因子", "技术因子"]
    df['综合得分'] = df[factor_cols].mean(axis=1)
    return df, factor_cols

# ================= 🌟 新增：全球宏观情报与新闻联动模块 =================
def get_global_news():
    """
    模拟全球实时新闻情报流。
    实际应用中，可替换为调用 Finimize API、Bloomberg API 或新闻爬虫接口。
    """
    news_data = [
        {
            "time": "2026-07-06 20:15",
            "category": "🌾 农产品",
            "headline": "USDA最新库存报告：美国玉米与小麦库存低于预期",
            "summary": "美国农业部(USDA)最新数据显示，6月1日玉米和小麦库存低于市场预期，受较小作物产量及种植面积下降影响。",
            "sentiment": "利多",
            "impact_assets": ["豆粕", "菜粕", "豆油"]
        },
        {
            "time": "2026-07-06 18:30",
            "category": "⚙️ 工业金属",
            "headline": "中国国有铁矿石买家收紧对Fortescue的采购规则",
            "summary": "由于长期价格谈判陷入僵局，部分中国钢厂被要求暂停购买新的美元计价Super Special Fines货物。",
            "sentiment": "利空",
            "impact_assets": ["锰硅", "硅铁", "焦煤"]
        },
        {
            "time": "2026-07-06 15:00",
            "category": "🛢️ 能源化工",
            "headline": "OPEC+同意8月起上调原油配额18.8万桶/日",
            "summary": "尽管地缘局势缓和导致WTI跌至70美元下方，OPEC+仍维持增产轨迹，供给恢复惯性压制油价。",
            "sentiment": "利空",
            "impact_assets": ["原油", "合成橡胶", "PVC"]
        },
        {
            "time": "2026-07-06 12:00",
            "category": "🏛️ 宏观政策",
            "headline": "美国商务部宣布对印、印尼、老挝光伏组件征收反补贴税",
            "summary": "美国将大幅加征关税，印度税率125.87%，印尼104.38%，老挝80.67%。",
            "sentiment": "利空",
            "impact_assets": ["纯碱", "玻璃"]
        }
    ]
    return pd.DataFrame(news_data)

# ================= UI 界面 =================
st.title("🌍 大宗商品全球量化联动与情报系统")
st.caption("联动矩阵 | 滚动回测 | 价差套利 | 多因子择时 | 全球情报联动 | 数据仅供研究参考")

st.sidebar.header("⚙️ 分析控制面板")
tab_option = st.sidebar.radio("选择分析模块", [
    "🔗 静态联动矩阵", 
    "📈 动态历史回测", 
    "🎯 价差套利监控", 
    "🧭 多因子择时",
    "📰 全球情报联动"
])

# 选项卡 1：静态联动矩阵
if tab_option == "🔗 静态联动矩阵":
    st.subheader("🔗 品种联动关系分析")
    col1, col2 = st.columns([1, 1])
    with col1:
        impact_type = st.radio("选择影响维度", ["微观产业链", "宏观能源锚"], horizontal=True)
        selected_comms = st.multiselect("选择关注品种", COMMODITIES, default=["合成橡胶", "原油", "纯碱", "玻璃"])
    with col2:
        st.markdown("### 📝 核心驱动逻辑")
        if selected_comms:
            factors = MACRO_FACTORS if "宏观" in impact_type else MICRO_FACTORS
            logic_found = False
            for comm in selected_comms:
                for factor, relations in factors.items():
                    if comm in relations:
                        key = (factor, comm) if factor in COMMODITIES else (comm, factor)
                        desc = RELATION_DESC.get(key, f"{factor} 与 {comm} 存在显著联动")
                        strength = relations[comm]
                        color = "🟢" if strength > 0.7 else ("🟡" if strength > 0.4 else "⚪")
                        st.markdown(f"""
                        <div style="padding:10px; border-radius:5px; background:#f0f2f6; margin-bottom:8px;">
                            <strong>{color} {comm} ↔ {factor}</strong><br>
                            <small>{desc}</small><br>
                            <small style="color:#666;">强度: {strength:.2f}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        logic_found = True
            if not logic_found: st.info("当前组合在【{}】维度下暂无强逻辑关联。".format(impact_type))
        else: st.info("👈 请在左侧选择至少一个品种")

# 选项卡 2：动态历史回测
elif tab_option == "📈 动态历史回测":
    st.subheader("📈 滚动相关系数回测 (Rolling Correlation)")
    c1, c2, c3 = st.columns(3)
    with c1: sym1 = st.selectbox("品种 A", COMMODITIES, index=COMMODITIES.index("合成橡胶"))
    with c2: sym2 = st.selectbox("品种 B", COMMODITIES, index=COMMODITIES.index("原油"))
    with c3: window = st.slider("滚动窗口 (天)", min_value=10, max_value=90, value=30, step=5)
    if sym1 != sym2:
        corr_df = calculate_rolling_correlation(sym1, sym2, window)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=corr_df['date'], y=corr_df['rolling_corr'], mode='lines', name=f'{window}日滚动相关系数', line=dict(color='royalblue', width=2)))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(title=f"{sym1} 与 {sym2} 的历史联动关系", xaxis_title="日期", yaxis_title="相关系数", yaxis=dict(range=[-1, 1]), height=500)
        st.plotly_chart(fig, use_container_width=True)
        avg_corr = corr_df['rolling_corr'].mean()
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("平均相关系数", f"{avg_corr:.2f}")
        mc2.metric("最高相关系数", f"{corr_df['rolling_corr'].max():.2f}")
        mc3.metric("最低相关系数", f"{corr_df['rolling_corr'].min():.2f}")

# 选项卡 3：价差套利监控
elif tab_option == "🎯 价差套利监控":
    st.subheader("🎯 跨品种价差套利监控")
    st.markdown("监控产业链上下游利润空间及替代品价差，捕捉均值回归的套利机会。")
    strategy = st.selectbox("选择套利策略", list(ARBITRAGE_STRATEGIES.keys()))
    st.caption(f"📖 策略逻辑：{ARBITRAGE_STRATEGIES[strategy]['desc']}")
    arb_df = calculate_arbitrage(strategy)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=arb_df['date'], y=arb_df['spread'], mode='lines', name='当前价差', line=dict(color='purple', width=2)))
    fig.add_trace(go.Scatter(x=arb_df['date'], y=arb_df['mean'], mode='lines', name='历史均值', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=arb_df['date'], y=arb_df['mean'] + arb_df['std'], mode='lines', name='+1 Std', line=dict(color='green', dash='dot', width=1)))
    fig.add_trace(go.Scatter(x=arb_df['date'], y=arb_df['mean'] - arb_df['std'], mode='lines', name='-1 Std', line=dict(color='red', dash='dot', width=1)))
    fig.update_layout(title=f"{strategy} 历史价差走势与均值回归", xaxis_title="日期", yaxis_title="价差利润", height=500)
    st.plotly_chart(fig, use_container_width=True)
    latest = arb_df.iloc[-1]
    z_score = latest['z_score']
    c1, c2, c3 = st.columns(3)
    c1.metric("当前价差", f"{latest['spread']:.2f}")
    c2.metric("历史均值", f"{latest['mean']:.2f}")
    c3.metric("Z-Score", f"{z_score:.2f}")
    if z_score > 2: st.error("🚨 **极端高估预警**：当前价差显著高于历史均值，存在做空价差的均值回归机会。")
    elif z_score < -2: st.success("🟢 **极端低估预警**：当前价差显著低于历史均值，存在做多价差的均值回归机会。")
    else: st.info("⏳ 当前价差处于历史正常波动区间，建议继续观望。")

# 选项卡 4：多因子择时
elif tab_option == "🧭 多因子择时":
    st.subheader("🧭 多因子择时与仓位决策")
    st.markdown("通过五维因子共同投票，决定当前市场整体方向与仓位建议。")
    timing_df, factor_cols = calculate_timing_factors()
    latest_score = timing_df['综合得分'].iloc[-1]
    c1, c2 = st.columns([1, 1])
    with c1:
        radar_data = [{"因子": col, "当前得分": timing_df[col].iloc[-1]} for col in factor_cols]
        radar_df = pd.DataFrame(radar_data)
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=radar_df['当前得分'], theta=radar_df['因子'], fill='toself', name='当前因子状态'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[-1, 1])), showlegend=False, height=400)
        st.plotly_chart(fig_radar, use_container_width=True)
    with c2:
        fig_score = go.Figure()
        fig_score.add_trace(go.Scatter(x=timing_df['date'], y=timing_df['综合得分'], mode='lines', name='综合得分', line=dict(color='blue', width=2)))
        fig_score.add_hline(y=0.3, line_dash="dash", line_color="green", annotation_text="重仓区")
        fig_score.add_hline(y=-0.3, line_dash="dash", line_color="red", annotation_text="空仓区")
        fig_score.update_layout(title="综合择时得分走势", xaxis_title="日期", yaxis_title="综合得分", height=400)
        st.plotly_chart(fig_score, use_container_width=True)
    st.markdown("### 🎯 择时决策输出")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("当前综合得分", f"{latest_score:.3f}")
    if latest_score > 0.3:
        mc2.metric("建议仓位", "80% - 100% (满仓/重仓)", delta="多头趋势")
        st.success("🟢 **多头共振**：多数因子看多，建议顺势做多或保持高仓位。")
    elif latest_score < -0.3:
        mc2.metric("建议仓位", "0% - 20% (空仓/轻仓)", delta="空头趋势")
        st.error("🔴 **空头共振**：多数因子看空，建议规避风险或逢高做空。")
    else:
        mc2.metric("建议仓位", "40% - 60% (半仓)", delta="震荡市")
        st.warning("🟡 **多空分歧**：因子信号不一致，建议降低仓位，寻找结构性套利机会。")

# 🌟 选项卡 5：全球情报联动
elif tab_option == "📰 全球情报联动":
    st.subheader("📰 全球宏观情报与新闻联动")
    st.markdown("实时追踪海外宏观政策、产业动态与突发事件，量化新闻情绪并映射至国内商品盘面。")
    
    news_df = get_global_news()
    
    # 情绪过滤
    filter_sentiment = st.multiselect("筛选新闻情绪", ["利多", "利空"], default=["利多", "利空"])
    filtered_news = news_df[news_df['sentiment'].isin(filter_sentiment)]
    
    for _, row in filtered_news.iterrows():
        # 情绪颜色标记
        sentiment_color = "🟢" if row['sentiment'] == "利多" else "🔴"
        impact_tags = " ".join([f"`{asset}`" for asset in row['impact_assets']])
        
        st.markdown(f"""
        <div style="padding:15px; border-radius:8px; border-left:5px solid {'#28a745' if row['sentiment']=='利多' else '#dc3545'}; background:#f8f9fa; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="font-size:16px;">{sentiment_color} {row['headline']}</strong>
                <span style="background:#e9ecef; padding:3px 8px; border-radius:4px; font-size:12px;">{row['category']}</span>
            </div>
            <p style="margin:8px 0; color:#555;">{row['summary']}</p>
            <div style="font-size:13px; color:#333;">
                <strong>⚡ 冲击标的：</strong> {impact_tags} | 
                <strong>⏱️ 时间：</strong> {row['time']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    st.caption("💡 **情报使用提示**：当突发新闻引发关联品种跳空高开/低开时，建议结合【价差套利监控】模块

