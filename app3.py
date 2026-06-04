import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# 1. 網頁初始設定 (維持大寬幅配置)
st.set_page_config(page_title="SMART MES 產線即時戰情看板", layout="wide", initial_sidebar_state="collapsed")

# 🎨 核心風格注入：全面改寫為工業暗色調（深藍黑背景 + 科技藍綠/霓虹紅配色）
st.markdown("""
    <style>
        /* 基礎背景與文字顏色設定 */
        .stApp {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        /* 大標題客製化科技感 */
        .main-title {
            font-size: 2rem;
            font-weight: 800;
            color: #58a6ff;
            text-shadow: 0px 0px 10px rgba(88, 166, 255, 0.3);
            margin-bottom: 0rem;
        }
        /* 左側與右側副標題 */
        h3 {
            color: #f0f6fc !important;
            font-size: 1.2rem !important;
            border-left: 4px solid #58a6ff;
            padding-left: 8px;
            margin-top: 1rem !important;
        }
        /* 工業級半透明 KPI 卡片 (玻璃質感) */
        div[data-testid="stMetric"] {
            background-color: rgba(22, 27, 34, 0.8) !important;
            padding: 15px !important;
            border-radius: 6px !important;
            border: 1px solid #30363d !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            margin-bottom: 0.8rem !important;
        }
        /* 客製化下拉選單樣式適應暗色調 */
        div[data-baseweb="select"] {
            background-color: #21262d !important;
            color: #ffffff !important;
            border-radius: 6px !important;
        }
        /* 智慧摘要卡片客製化 */
        .custom-alert-success {
            background-color: rgba(56, 139, 60, 0.15);
            border: 1px solid #2ea043;
            padding: 12px;
            border-radius: 6px;
            color: #56d364;
        }
        .custom-alert-warning {
            background-color: rgba(187, 128, 9, 0.15);
            border: 1px solid #d29922;
            padding: 12px;
            border-radius: 6px;
            color: #e3b341;
        }
    </style>
""", unsafe_allow_html=True)

# 2. 一次性資料清洗與前處理模組 (精準解析與清洗 PRD-001.csv)
@st.cache_data
def load_and_clean_data(file_path):
    df = pd.read_csv(file_path)
    
    # 清洗：支援多種日期格式，標準化為字串格式 'YYYY-MM-DD'
    df['日期_clean'] = pd.to_datetime(df['日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=['日期_clean'])
    
    # 清洗：修正班別與目標欄位錯位
    mask = df['班別'].astype(str).str.contains('項目') & df['目標'].astype(str).isin(['A', 'B', 'C'])
    df.loc[mask, ['班別', '目標']] = df.loc[mask, ['目標', '擺放項目']].values if '擺放項目' in df.columns else df.loc[mask, ['目標', '擺放項目']].values if '擺放項目' in df.columns else df.loc[mask, ['目標', '班別']].values
    
    # 清洗：確保產量為數值
    df['產量'] = pd.to_numeric(df['產量'], errors='coerce').fillna(0)
    
    # POC 目標產量對應
    target_mapping = {'項目1': 500, '項目2': 400, '項目3': 300, 'A': 450, 'B': 350, 'C': 300}
    df['目標產量'] = df['目標'].map(target_mapping).fillna(350)
    
    return df

# 載入清洗後的資料
df_clean = load_and_clean_data("PRD-001.csv")

# 取得所有真正有資料的日期清單
all_valid_dates = sorted(list(df_clean['日期_clean'].unique()), reverse=True) # 由新到舊排序

# --- 3. 網頁頂部標頭與控制區 ---
st.markdown('<p class="main-title">📊 SMART MES 產線即時戰情看板 (POC)</p>', unsafe_allow_html=True)
st.markdown("<hr style='margin: 0.5rem 0; border-color: #30363d;'/>", unsafe_allow_html=True)

# 嚴格保持現有排版：左邊 30% 放控制與指標，右邊 70% 完整平鋪兩大圖表
left_col, right_col = st.columns([30, 70])

# --- 左半邊：下拉選單選單、戰情摘要與 KPI 指標 ---
with left_col:
    st.subheader("⚙️ 數據檢視控制")
    
    selected_date = st.selectbox(
        "請選擇檢視日期：",
        options=all_valid_dates,
        label_visibility="collapsed" # 隱藏標籤讓畫面更乾淨
    )
    
    # 依據選定的日期，撈取當日數據
    df_today = df_clean[df_clean['日期_clean'] == selected_date]
    
    # 當日數據彙整與指標計算
    today_summary = df_today.groupby('產線').agg(
        實際產量=('產量', 'sum'),
        目標產量=('目標產量', 'sum')
    ).reset_index().sort_values('產線')
    today_summary['達成率(%)'] = (today_summary['實際產量'] / today_summary['目標產量'] * 100).round(1)
    
    st.subheader("💡 產能落後診斷摘要")
    
    lagging_lines = today_summary[today_summary['達成率(%)'] < 80]
    if lagging_lines.empty:
        st.markdown(f"""
            <div class="custom-alert-success">
                <b>✅ 運作正常 ({selected_date})</b><br>
                當前所有產線產能均在安全範圍內，進度皆能順利追上預期目標。
            </div>
        """, unsafe_allow_html=True)
    else:
        summary_html = f'<div class="custom-alert-warning"><b>⚠️ 產能落後告警 ({selected_date})</b><br>'
        for _, row in lagging_lines.iterrows():
            if row['達成率(%)'] < 50:
                summary_html += f"• <b>{row['產線']}</b> 嚴重落後 (達成率 {row['達成率(%)']}%，評估下班前<b>無法追上</b>)。<br>"
            else:
                summary_html += f"• <b>{row['產線']}</b> 微幅落後 (達成率 {row['達成率(%)']}%，下班前<b>仍有機會追上</b>)。<br>"
        summary_html += '</div>'
        st.markdown(summary_html, unsafe_allow_html=True)

    st.subheader("📊 各線當日彙整指標")
    
    # 由上往下平鋪當日各產線的 KPI 指標卡片
    for idx, row in today_summary.iterrows():
        st.metric(
            label=f"📌 {row['產線']} 當前達成率",
            value=f"{row['達成率(%)']}%",
            delta=f"實際: {int(row['實際產量'])} / 目標: {int(row['目標產量'])}",
            delta_color="normal" if row['達成率(%)'] >= 80 else "inverse"
        )

# --- 右半邊：兩大圖表直接「左右並列」，不切換分頁 ---
with right_col:
    st.subheader("📈 數據視覺化圖表看板")
    
    # 歷史最近 5 個有開工的日期趨勢 (由舊到新排序)
    active_dates_asc = sorted(all_valid_dates[-5:])
    df_multi = df_clean[df_clean['日期_clean'].isin(active_dates_asc)]
    multi_summary = df_multi.groupby(['日期_clean', '產線'])['產量'].sum().unstack().fillna(0)

    # 保持並列排版
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown(f"**📊 當日實際 vs 預期產能對比 ({selected_date})**")
        
        # 使用 Plotly 繪製暗色調科技感「並排」長條圖
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=today_summary['產線'],
            y=today_summary['實際產量'],
            name='實際產量',
            marker_color='#388bfd' # 科技亮藍
        ))
        fig.add_trace(go.Bar(
            x=today_summary['產線'],
            y=today_summary['目標產量'],
            name='目標產量',
            marker_color='#f778ba' # 霓虹洋紅 (對應落後/預期標記)
        ))
        
        fig.update_layout(
            template='plotly_dark', # 調用 Plotly 原生暗色範本
            paper_bgcolor='rgba(0,0,0,0)', # 背景透明以融入網頁
            plot_bgcolor='rgba(0,0,0,0)',
            barmode='group',
            height=430,
            margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor='#30363d'),
            yaxis=dict(gridcolor='#30363d'),
            xaxis_title="產線",
            yaxis_title="產量 (pcs)"
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
    with chart_col2:
        st.markdown("**📈 歷史多日期產量彙總趨勢 (最近五日)**")
        
        # 為了搭配暗色調風格，歷史趨勢圖我們也升級為 Plotly 曲線圖，視覺一致性更高
        fig_line = go.Figure()
        colors = ['#58a6ff', '#388bfd', '#ff7b72', '#79c0ff', '#ffa657'] # 霓虹科技配色清單
        for i, col_name in enumerate(multi_summary.columns):
            fig_line.add_trace(go.Scatter(
                x=multi_summary.index,
                y=multi_summary[col_name],
                mode='lines+markers',
                name=col_name,
                line=dict(width=3, color=colors[i % len(colors)]),
                marker=dict(size=8)
            ))
            
        fig_line.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=430,
            margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor='#30363d'),
            yaxis=dict(gridcolor='#30363d'),
            xaxis_title="日期",
            yaxis_title="總產量 (pcs)"
        )
        st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})