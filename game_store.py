import streamlit as st
import pandas as pd
import requests
import time

# 1. 頁面基本設定
st.set_page_config(page_title="Sports Dashboard", layout="wide")

# --- 隱藏 Manage app 與頂部工具列 ---
st.markdown("""
    <style>
    header {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    footer {display: none !important;}
    .stAppDeployButton {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 賽事雲端統計看板")

# 2. 讀取資料並進行安全性檢查
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    # --- 重要：欄位自動補齊機制 (防止 IndexError) ---
    # 確保所有程式需要的欄位都存在，如果不存在就補 0 或空字串
    required_cols = {
        "特定球員": "",
        "下注總額": 0,
        "領回金額": 0,
        "結果": "錯誤",
        "老師": "未知"
    }
    for col, default_val in required_cols.items():
        if col not in df.columns:
            df[col] = default_val

    # 數據型態強制轉換
    df["下注總額"] = pd.to_numeric(df["下注總額"], errors='coerce').fillna(0)
    df["領回金額"] = pd.to_numeric(df["領回金額"], errors='coerce').fillna(0)
    df["老師"] = df["老師"].astype(str)
    df["注單編號"] = df["注單編號"].fillna("無編號").astype(str)

    # --- 記憶選單提取 ---
    team_options = [""]
    player_options = [""]
    
    if not df.empty:
        # 球隊記憶
        all_matches = df["對戰組合"].dropna().astype(str).tolist()
        u_teams = set()
        for m in all_matches:
            if " vs " in m:
                u_teams.update([t.strip() for t in m.split(" vs ")])
            else:
                u_teams.add(m.strip())
        team_options += sorted(list(u_teams))
        
        # 球員記憶
        u_players = set(df["特定球員"].dropna().astype(str).tolist())
        player_options += sorted([p for p in u_players if p.strip() != "" and p != "nan"])
        
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗：請檢查試算表欄位或網路連線。")
    st.stop()

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 ---
with st.expander("📝 錄入新注單", expanded=False):
    num_m = st.number_input("比賽場數", 1, 10, 1)
    with st.form("multi_form", clear_on_submit=True):
        c_t, c_d = st.columns(2)
        f_t = c_t.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = c_d.date_input("日期")
        
        c_cost, c_ret = st.columns(2)
        f_cost = c_cost.number_input("下注總額 (成本)", min_value=0, value=0)
        f_ret = c_ret.number_input("領回總額 (回收)", min_value=0, value=0)
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"--- **賽事 {i+1}** ---")
            c_t1, c_vs, c_t2 = st.columns([4, 1, 4])
            with c_t1:
                t1 = st.selectbox(f"選主隊", team_options, key=f"t1_{i}")
                t1_n = st.text_input(f"手輸主隊", key=f"t1n_{i}")
                final_t1 = t1_n if t1_n else t1
            with c_vs: st.write("VS")
            with c_t2:
                t2 = st.selectbox(f"選客隊", team_options, key=f"t2_{i}")
                t2_n = st.text_input(f"手輸客隊", key=f"t2n_{i}")
                final_t2 = t2_n if t2_n else t2
            
            c_p1, c_p2 = st.columns(2)
            p_sel = c_p1.selectbox(f"選球員", player_options, key=f"ps_{i}")
            p_new = c_p2.text_input(f"手輸球員", key=f"pn_{i}")
            final_p = p_new if p_new else p_sel

            c1, c2, c3 = st.columns([4, 4, 2])
            p_v = c1.text_input("預測", key=f"p_{i}")
            s_v = c2.text_input("結果/比分", key=f"s_{i}")
            r_v = c3.selectbox("判定", ["正確", "錯誤"], key=f"r_{i}")
            
            m_list.append({
                "match": f"{final_t1} vs {final_t2}",
                "player": final_p, "pred": p_v, "score": s_v, "result": r_v
            })
        
        if st.form_submit_button("🚀 確認提交"):
            s_id = f"SLIP-{int(time.time())}"
            payload = {
                "teacher": f_t, "date": f_date.strftime("%Y-%m-%d"), 
                "slipId": s_id, "matches": m_list,
                "cost": f_cost, "returnVal": f_ret
            }
            res = requests.post(GAS_URL, json=payload, timeout=10)
            if res.status_code == 200:
                st.success("存檔成功！")
                time.sleep(1)
                st.rerun()

st.divider()

# --- 4. 顯示邏輯 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # 損益統計
    slip_money = df_display.groupby("注單編號").first()
    t_cost = slip_money["下注總額"].sum()
    t_ret = slip_money["領回金額"].sum()
    profit = t_ret - t_cost
    roi = (profit / t_cost * 100) if t_cost > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("單場勝率", f"{(len(df_display[df_display['結果']=='正確'])/len(df_display)*100):.1f}%")
    c2.metric("累積損益", f"${profit:,.0f}")
    c3.metric("ROI", f"{roi:.1f}%")

    unique_slips = [s for s in df_display["注單編號"].unique() if str(s) != "nan"][::-1]
    for sid in unique_slips:
        slip_data = df_display[df_display["注單編號"] == sid]
        s_cost = slip_data["下注總額"].iloc[0]
        s_ret = slip_data["領回金額"].iloc[0]
        status = "💰" if s_ret > s_cost else ("❌" if s_ret < s_cost else "➖")
        
        with st.expander(f"{status} 日期：{slip_data['日期'].iloc[0]} | 成本：{s_cost} | 回收：{s_ret}"):
            # 這裡就是修正 IndexError 的關鍵：只顯示存在的欄位
            cols = ["對戰組合", "特定球員", "預測內容", "實際比分", "結果"]
            display_cols = [c for c in cols if c in slip_data.columns]
            st.table(slip_data[display_cols])
            
            if st.button("確認刪除", key=f"del_{sid}", type="primary"):
                requests.post(GAS_URL, json={"action": "delete", "slipId": sid}, timeout=10)
                st.rerun()
else:
    st.info("尚無數據")
