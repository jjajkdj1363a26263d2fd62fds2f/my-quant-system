import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import akshare as ak

# ================= 页面配置 =================
st.set_page_config(page_title="大宗商品量化联动系统", layout="wide")
st.title("🌍 大宗商品全球量化联动与情报系统")

# ================= 真实数据获取模块 (AKShare) =================
@st.cache_data(ttl=3600)  # 缓存1小时，避免频繁请求被限流
def generate_mock_prices(symbol, days=365):
    """
    接入 AKShare 获取国内期货主力连续合约真实日线数据
    注：保留原函数名，以便不改动下游其他模块的逻辑
    """
    # 中文品种名与 AKShare 期货代码的映射
    symbol_map = {
        '豆粕': 'M0', '菜粕': 'RM0', '豆油': 'Y0', '棕榈油': 'P0',
        '原油': 'SC0', '燃油': 'FU0', '沥青': 'BU0', 'PTA': 'TA0',
        '螺纹钢': 'RB0', '热卷': 'HC0', '铁矿石': 'I0', '焦炭': 'J0',
        '玻璃': 'FG0', '纯碱': 'SA0', '生猪': 'LH0', '玉米': 'C0'
    }
    
    if symbol not in symbol_map:
        return pd.DataFrame()
    
    try:
        # 获取最近两年的数据，再截取，防止历史数据不够计算指标
        start_date = (datetime.now() - timedelta(days=days + 100)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        df = ak.futures_main_sina(symbol=symbol_map[symbol], start_date=start_date, end_date=end_date)
        
        # 兼容不同版本的 AKShare 返回的列名
        if '日期' in df.columns:
            df = df.rename(columns={'日期': 'date', '收盘价': 'price'})
        elif 'date' in df.columns:
            df = df.rename(columns={'date': 'date', 'close': 'price'})
            
        df['date'] = pd.to_datetime(df['date'])
        df = df[['date', 'price']].dropna()
        
        # 截取最近 N 天
        df = df.tail(days).reset_index(drop=True)
        df['symbol'] = symbol
        return df
        
    except Exception as e:
        st.error(f"❌ 获取 {symbol} 真实数据失败: {str(e)}")
        return pd.DataFrame()

# ================= 核心策略定义 =================
ARBITRAGE_STRATEGIES = {
    "大豆压榨利润": {
        "desc": "监控大豆压榨厂的理论利润空间 (豆油*0.2 + 豆粕*0.8 - 大豆成本)",
        "components": ['豆油', '豆粕'], 
        "weights": [0.2, 0.8]
    },
    "纯碱-玻璃价差": {
        "desc": "监控纯碱与玻璃的产业链利润分配",
        "components": ['纯碱', '玻璃'],
        "weights": [1, -1]
    },
    "豆菜粕替代价差": {
        "desc": "捕捉饲料蛋白原料的替代机会",
        "components": ['豆粕', '菜粕'],
        "weights": [1, -1]
    }
}

# ================= 业务逻辑函数 =================
def calculate_arbitrage(strategy_name):
    """计算价差、均值及Z-Score"""
    strategy = ARBITRAGE_STRATEGIES[strategy_name]
    components = strategy["components"]
    weights = strategy["weights"]
    
    dfs = []
    for symbol in components:
        df = generate_mock_prices(symbol)
        if df.empty: return pd.DataFrame()
        df.rename(columns={'price': f'price_{symbol}'}, inplace=True)
        dfs.append(df[['date', f'price_{symbol}']])
    
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on='date', how='inner')
    
    if merged.empty:
        return pd.DataFrame()
        
    # 计算加权价差
    spread = np.zeros(len(merged))
    for i, symbol in enumerate(components):
        spread += weights[i] * merged[f'price_{symbol}'].values
    merged['spread'] = spread
    
    # 计算统计指标 (滚动窗口)
    window = 20
    merged['mean'] = merged['spread'].rolling(window=window).mean()
    merged['std'] = merged['spread'].rolling(window=window).std()
    
    merged['z_score'] = (merged['spread'] - merged['mean']) / merged['std']
    merged.dropna(inplace=True)
    
    return merged

# ================= 侧边栏导航 =================
tab_option = st.sidebar.selectbox(
    "功能导航",
    ["🔗 静态联动矩阵", "📈 动态历史回测", "🎯 价差套利监控", "📰 宏观情报分析", "⚙️ 系统设置"]
)

# ================= 选项卡 1：静态联动矩阵 =================
if tab_option == "🔗 静态联动矩阵":
    st.subheader("🔗 产业链联动逻辑可视化")
    st.info("展示预设的宏观能源锚与微观产业链传导关系。")
    
    selected_macro = st.selectbox("选择宏观锚点", ["原油", "焦煤"])
    
    data = {
        "下游品种": ["燃油", "沥青", "PTA", "合成橡胶"],
        "联动强度": [0.85, 0.72, 0.65, 0.58],
        "传导周期": ["即时", "1-3天", "3-7天", "1周以上"]
    }
    df_matrix = pd.DataFrame(data)
    st.dataframe(df_matrix, use_container_width=True)
    
    fig = go.Figure(go.Bar(x=df_matrix["下游品种"], y=df_matrix["联动强度"], marker_color='teal'))
    fig.update_layout(title=f"{selected_macro} 对下游品种的联动强度分布", height=400)
    st.plotly_chart(fig, use_container_width=True)

# ================= 选项卡 2：动态历史回测 =================
elif tab_option == "📈 动态历史回测":
    st.subheader("📈 跨品种相关性动态演变")
    
    col1, col2 = st.columns(2)
    sym_a = col1.selectbox("品种 A", list(ARBITRAGE_STRATEGIES['豆菜粕替代价差']['components']))
    sym_b = col2.selectbox("品种 B", list(ARBITRAGE_STRATEGIES['豆菜粕替代价差']['components']), index=1)
    
    if sym_a != sym_b:
        df_a = generate_mock_prices(sym_a)
        df_b = generate_mock_prices(sym_b)
        
        if not df_a.empty and not df_b.empty:
            merged = pd.merge(df_a[['date','price']], df_b[['date','price']], on='date', suffixes=('_a', '_b'))
            merged['ret_a'] = merged['price_a'].pct_change()
            merged['ret_b'] = merged['price_b'].pct_change()
            merged['corr_30d'] = merged['ret_a'].rolling(30).corr(merged['ret_b'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=merged['date'], y=merged['corr_30d'], name='30日滚动相关系数', line=dict(color='blue')))
            fig.update_layout(title=f"{sym_a} vs {sym_b} 动态相关性", yaxis_range=[-1, 1], height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("数据加载失败，请稍后重试。")
    else:
        st.warning("请选择两个不同的品种进行对比。")

# ================= 选项卡 3：价差套利监控 (已修复) =================
elif tab_option == "🎯 价差套利监控":
    st.subheader("🎯 跨品种价差套利监控")
    st.markdown("监控产业链上下游利润空间及替代品价差，捕捉均值回归的套利机会。")
    
    strategy = st.selectbox("选择套利策略", list(ARBITRAGE_STRATEGIES.keys()))
    st.caption(f"📖 策略逻辑：{ARBITRAGE_STRATEGIES[strategy]['desc']}")
    
    arb_df = calculate_arbitrage(strategy)
    
    if not arb_df.empty:
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
        
        if z_score > 2: 
            st.error("🚨 **极端高估预警**：当前价差显著高于历史均值，存在做空价差的均值回归机会。")
        elif z_score < -2: 
            st.success("🟢 **极端低估预警**：当前价差显著低于历史均值，存在做多价差的均值回归机会。")
        else: 
            st.info("⏳ 当前价差处于历史正常波动区间，建议继续观望。")
    else:
        st.warning("⚠️ 当前策略无法计算出有效数据，请检查数据源或策略参数。")

# ================= 选项卡 4 & 5：占位符 =================
elif tab_option == "📰 宏观情报分析":
    st.subheader("📰 全球宏观情报聚合")
    st.info("此处将接入新闻API，分析OPEC+会议、美联储决议等事件对大宗商品的影响。")
    
elif tab_option == "⚙️ 系统设置":
    st.subheader("⚙️ 系统参数配置")
    st.slider("数据刷新频率 (分钟)", 1, 60, 60)
    st.checkbox("开启实时推送通知")
