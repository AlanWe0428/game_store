import streamlit as st
import pandas as pd
import requests
import time

# 1. 頁面基本設定
st.set_page_config(page_title="Sports Dashboard", layout="wide")

# --- 隱藏 Manage app 與頂部工具列 CSS ---
st.markdown("""
    <style>
    header {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    footer {display: none !important;}
    .stAppDeployButton {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    .st-emotion-cache-zq5wms {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 賽事雲端統計看板")

# 2. 讀取資料與安全性處理
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    # --- 重要：自動補齊欄位，防止舊資料導致 IndexError ---
    # 這是確保您以前「沒編號、沒金額」的資料也能正常顯示與計算的關鍵
    required_cols = {
        "注單編號": "無編號",
        "特定球員": "",
        "下注總額": 0,
        "領回金額": 0,
        "結果": "錯誤",
        "老師": "未知"
    }
    for col, default_val in required_cols.items():
        if col not in df.columns:
            df[col] = default_val

    # 數據整理與型態轉換
    df["下注總額"] = pd.to_numeric(df["下注總額"], errors='coerce').fillna(0)
    df["領回金額"] = pd.to_numeric(df["領回金額"], errors='coerce').fillna(0)
    df["結果"] = df["結果"].astype(str).str.strip()
    df["老師"] = df["老師"].astype(str).str.strip()
    df["注單編號"] = df["注單編號"].fillna("無編號").astype(str).str.strip()

    # --- 記憶選單提取 ---
    team_options = [""]
    player_options = [""]
    if not df.empty:
        # 球隊記憶
        all_m = df["對戰組合"].dropna().astype(str).tolist()
        u_t = set()
        for m in all_m:
            if " vs " in m: u_t.update([t.strip() for t in m.split(" vs ")])
            else: u_t.add(m.strip())
        team_options += sorted(list(u_t))
        
        # 球員記憶
        u_p = set(df["特定球員"].dropna().astype(str).tolist())
        player_options += sorted([p for p in u_p if p.strip() != "" and p != "nan"])
        
        # 老師名單
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗，請確認 Secrets 或試算表標題順序。")
    st.stop()

# 初始化選中的老師
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 ---
with st.expander("📝 錄入新注單 (自動記憶球隊/球員)", expanded=False):
    num_m = st.number_input("這張單有幾場比賽？", 1, 10, 1)
    with st.form("multi_form", clear_on_submit=True):
        c_t, c_d = st.columns(2)
        f_t = c_t.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = c_d.date_input("日期")
        
        c_cost, c_ret = st.columns(2)
        f_cost = c_cost.number_input("下注總額 (成本)", min_value=0, value=0)
        f_ret = c_ret.number_input("領回總額 (回收)", min_value=0, value=0)
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"--- **📍 賽事 {i+1}** ---")
            c_t1, c_vs, c_t2 = st.columns([4, 1, 4])
            with c_t1:
                t1_s = st.selectbox(f"選主隊", team_options, key=f"t1s_{i}")
                t1_n = st.text_input(f"或手輸", key=f"t1n_{i}", placeholder="新主隊")
                final_t1 = t1_n if t1_n else t1_s
            with c_vs: st.markdown("<p style='text-align:center; padding-top:35px;'>VS</p>", unsafe_allow_html=True)
            with c_t2:
                t2_s = st.selectbox(f"選客隊", team_options, key=f"t2s_{i}")
                t2_n = st.text_input(f"或手輸", key=f"t2n_{i}", placeholder="新客隊")
                final_t2 = t2_n if t2_n else t2_s
            
            c_p1, c_p2 = st.columns(2)
            p_s = c_p1.selectbox(f"選球員", player_options, key=f"ps_{i}")
            p_n = c_p2.text_input(f"或手輸新球員", key=f"pn_{i}")
            final_p = p_n if p_n else p_s

            c1, c2, c3 = st.columns([4, 4, 2])
            p_v = c1.text_input("預測內容", key=f"p_{i}")
            s_v = c2.text_input("實際數據", key=f"s_{i}")
            r_v = c3.selectbox("結果", ["正確", "錯誤"], key=f"r_{i}")
            
            m_list.append({
                "match": f"{final_t1} vs {final_t2}",
                "player": final_p, "pred": p_v, "score": s_v, "result": r_v
            })
        
        if st.form_submit_button("🚀 確認提交整張注單"):
            s_id = f"SLIP-{int(time.time())}"
            payload = {
                "teacher": f_t, "date": f_date.strftime("%Y-%m-%d"), 
                "slipId": s_id, "matches": m_list,
                "cost": f_cost, "returnVal": f_ret
            }
            try:
                res = requests.post(GAS_URL, json=payload, timeout=10)
                if res.status_code == 200:
                    st.success("✅ 存檔成功！")
                    time.sleep(1)
                    st.rerun()
            except:
                st.error("❌ 連線異常")

st.divider()

# --- 4. 老師切換按鈕區 ---
st.write("👤 **切換老師視角：**")
t_cols = st.columns(len(all_teachers))
for i, t_name in enumerate(all_teachers):
    with t_cols[i]:
        is_active = st.session_state.current_teacher == t_name
        if st.button(t_name, key=f"btn_{t_name}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.current_teacher = t_name
            st.rerun()

st.divider()

# --- 5. 數據統計與收合顯示 ---
cur_t = st.session_state.current_teacher
df_disp = df[df["老師"] == cur_t].copy()

if not df_disp.empty:
    # A. 單場勝率
    w_m = len(df_disp[df_disp["結果"] == "正確"])
    rate_m = (w_m / len(df_disp) * 100)
    
    # B. 注單(串關)與損益統計
    # 這裡做一個補強：如果舊資料沒編號，給它一個臨時編號以便單獨計算
    df
