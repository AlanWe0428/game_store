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

# 2. 讀取資料與安全性處理 (含補齊欄位邏輯)
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    # 自動補齊舊資料缺少的欄位，防止計算崩潰
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

    # 數據清理
    df["下注總額"] = pd.to_numeric(df["下注總額"], errors='coerce').fillna(0)
    df["領回金額"] = pd.to_numeric(df["領回金額"], errors='coerce').fillna(0)
    df["結果"] = df["結果"].astype(str).str.strip()
    df["老師"] = df["老師"].astype(str).str.strip()
    df["注單編號"] = df["注單編號"].fillna("無編號").astype(str).str.strip()

    # 記憶選單提取
    team_options = [""]
    player_options = [""]
    if not df.empty:
        all_m = df["對戰組合"].dropna().astype(str).tolist()
        u_t = set()
        for m in all_m:
            if " vs " in m: u_t.update([t.strip() for t in m.split(" vs ")])
            else: u_t.add(m.strip())
        team_options += sorted(list(u_t))
        
        u_p = set(df["特定球員"].dropna().astype(str).tolist())
        player_options += sorted([p for p in u_p if p.strip() != "" and p != "nan"])
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗，請確認 Secrets 設定。")
    st.stop()

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
                t1_n = st.text_input(f"手輸主隊", key=f"t1n_{i}")
                final_t1 = t1_n if t1_n else t1_s
            with c_vs: st.markdown("<p style='text-align:center; padding-top:35px;'>VS</p>", unsafe_allow_html=True)
            with c_t2:
                t2_s = st.selectbox(f"選客隊", team_options, key=f"t2s_{i}")
                t2_n = st.text_input(f"手輸客隊", key=f"t2n_{i}")
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
                    res = requests.post(GAS_URL, json=payload, timeout=20) 
                    
                    if res.status_code == 200:
                        st.success("✅ 存檔成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ 伺服器回傳錯誤代碼: {res.status_code}")
                
            except requests.exceptions.ReadTimeout:
                   st.warning("⚠️ 處理時間較長，資料可能已存檔，請重新整理網頁檢查。")
                
            except Exception as e:
                   st.error(f"❌ 連線發生預料外的異常：{e}")

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

# --- 5. 數據統計與顯示 (恢復注單勝率並保留損益) ---
cur_t = st.session_state.current_teacher
df_disp = df[df["老師"] == cur_t].copy()

if not df_disp.empty:
    # A. 單場勝率
    w_m = len(df_disp[df_disp["結果"] == "正確"])
    rate_m = (w_m / len(df_disp) * 100)
    
    # B. 注單(串關)與損益統計邏輯
    df_calc = df_disp.copy()
    mask = (df_calc["注單編號"] == "無編號") | (df_calc["注單編號"].isna())
    df_calc.loc[mask, "注單編號"] = [f"TEMP-{i}" for i in range(mask.sum())]
    
    slip_money = df_calc.groupby("注單編號").first()
    t_cost = slip_money["下注總額"].sum()
    t_ret = slip_money["領回金額"].sum()
    profit = t_ret - t_cost
    roi = (profit / t_cost * 100) if t_cost > 0 else 0
    
    slip_res = df_calc.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
    w_s = sum(slip_res)
    rate_s = (w_s / len(slip_res) * 100)

    # --- 重要：指標卡改為 4 個 ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("單場勝率", f"{rate_m:.1f}%", f"{w_m}/{len(df_disp)} 場")
    m2.metric("注單勝率 (串關)", f"{rate_s:.1f}%", f"{int(w_s)}/{len(slip_res)} 張")
    m3.metric("累積損益", f"${profit:,.0f}", f"投資額 ${t_cost:,.0f}")
    m4.metric("總投報率 ROI", f"{roi:.1f}%")

    st.subheader(f"📍 {cur_t} 歷史明細")
    u_slips = df_calc["注單編號"].unique()[::-1]
    
    for sid in u_slips:
        s_data = df_calc[df_calc["注單編號"] == sid]
        if s_data.empty: continue
        cost_val = s_data["下注總額"].iloc[0]
        ret_val = s_data["領回金額"].iloc[0]
        
        icon = "💰" if ret_val > cost_val else ("❌" if ret_val < cost_val else "➖")
        
        with st.expander(f"{icon} 日期：{s_data['日期'].iloc[0]} | 成本：{cost_val} | 回收：{ret_val}"):
            cols = ["對戰組合", "特定球員", "預測內容", "實際比分", "結果"]
            st.table(s_data[[c for c in cols if c in s_data.columns]])
            
            if st.button("確認刪除此單", key=f"del_{sid}", type="primary"):
                requests.post(GAS_URL, json={"action": "delete", "slipId": sid}, timeout=10)
                st.rerun()
else:
    st.info(f"老師 {cur_t} 尚無數據。")
