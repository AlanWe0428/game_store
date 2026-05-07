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

# 2. 從 Secrets 讀取資料
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    # --- 球隊記憶邏輯 ---
    team_options = [""]
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        df["注單編號"] = df["注單編號"].fillna("無編號").astype(str)
        df["日期"] = df["日期"].fillna("未知日期").astype(str)
        
        # 從歷史「對戰組合」中提取球隊名稱 (拆分 A vs B)
        all_matches = df["對戰組合"].dropna().astype(str).tolist()
        unique_teams = set()
        for m in all_matches:
            if " vs " in m:
                teams = m.split(" vs ")
                unique_teams.update([t.strip() for t in teams])
            else:
                unique_teams.add(m.strip())
        team_options += sorted(list(unique_teams))
        
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗，請確認 Secrets 設定。")
    st.stop()

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 (主客隊拆分) ---
with st.expander("📝 錄入新注單 (支援單場或串關)", expanded=False):
    num_m = st.number_input("這張注單包含幾場比賽？", min_value=1, max_value=10, value=1)
    
    with st.form("multi_match_form", clear_on_submit=True):
        f_t = st.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = st.date_input("日期")
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"--- **📍 賽事 {i+1}** ---")
            
            # 主客隊選擇與輸入
            st.write("對戰組合 (主隊 vs 客隊)")
            col_t1, col_vs, col_t2 = st.columns([4, 1, 4])
            with col_t1:
                t1_sel = st.selectbox(f"選取主隊", options=team_options, key=f"t1_s_{i}")
                t1_new = st.text_input(f"或手動輸入新主隊", key=f"t1_n_{i}")
                final_t1 = t1_new if t1_new else t1_sel
            with col_vs:
                st.markdown("<h3 style='text-align: center; padding-top: 25px;'>VS</h3>", unsafe_allow_html=True)
            with col_t2:
                t2_sel = st.selectbox(f"選取客隊", options=team_options, key=f"t2_s_{i}")
                t2_new = st.text_input(f"或手動輸入新客隊", key=f"t2_n_{i}")
                final_t2 = t2_new if t2_new else t2_sel

            # 預測內容、比分、結果
            c1, c2, c3 = st.columns([4, 4, 2])
            p_v = c1.text_input("預測內容", key=f"p_{i}")
            s_v = c2.text_input("實際比分", key=f"s_{i}")
            r_v = c3.selectbox("結果", ["正確", "錯誤"], key=f"r_{i}")
            
            m_list.append({
                "match": f"{final_t1} vs {final_t2}", 
                "pred": p_v, "score": s_v, "result": r_v
            })
        
        if st.form_submit_button("🚀 確認提交整張注單"):
            if not f_t or not final_t1 or not final_t2:
                st.error("請確保老師姓名與對戰組合已填寫")
            else:
                s_id = f"SLIP-{int(time.time())}"
                payload = {
                    "teacher": f_t, 
                    "date": f_date.strftime("%Y-%m-%d"), 
                    "slipId": s_id, 
                    "matches": m_list
                }
                try:
                    res = requests.post(GAS_URL, json=payload, timeout=10)
                    if res.status_code == 200:
                        st.success("✅ 存檔成功！")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 連線異常：{e}")

st.divider()

# --- 4. 老師切換按鈕 ---
btn_cols = st.columns(len(all_teachers))
for i, t in enumerate(all_teachers):
    with btn_cols[i]:
        if st.button(t, key=f"btn_{t}", use_container_width=True, 
                     type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# --- 5. 數據統計與收合顯示 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # 勝率統計
    t_m = len(df_display)
    w_m = len(df_display[df_display["結果"] == "正確"])
    slip_res = df_display.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
    t_s = len(slip_res)
    w_s = sum(slip_res)

    c1, c2 = st.columns(2)
    c1.metric("單場勝率", f"{(w_m/t_m*100):.1f}%", f"{w_m}/{t_m} 場")
    c2.metric("注單勝率 (串關)", f"{(w_s/t_s*100 if t_s > 0 else 0):.1f}%", f"{int(w_s)}/{t_s} 張")

    st.subheader(f"📍 {cur_t} 歷史明細 (按注單收合)")
    
    unique_slips = [s for s in df_display["注單編號"].unique() if str(s) != "nan"][::-1]
    
    for sid in unique_slips:
        slip_data = df_display[df_display["注單編號"] == sid]
        if slip_data.empty: continue
            
        is_win = all(slip_data["結果"] == "正確")
        date_str = slip_data["日期"].iloc[0]
        icon = "✅" if is_win else "❌"
        
        with st.expander(f"{icon} 日期：{date_str} | 注單：{sid} ({len(slip_data)} 場)"):
            st.table(slip_data[["對戰組合", "預測內容", "實際比分", "結果"]])
            
            # 刪除功能
            c_space, c_del = st.columns([5, 1])
            with c_del:
                with st.popover("🗑️ 刪除", use_container_width=True):
                    st.warning("確定要刪除嗎？")
                    if st.button("確認", key=f"del_{sid}", type="primary"):
                        try:
                            requests.post(GAS_URL, json={"action": "delete", "slipId": sid}, timeout=10)
                            st.rerun()
                        except:
                            st.error("失敗")
else:
    st.info("尚無數據紀錄")
