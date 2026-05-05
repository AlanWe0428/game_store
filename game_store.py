import streamlit as st
import pandas as pd
import requests
import time

# --- 1. 讀取與初始化 ---
try:
    SHEET_ID = "1BnNF9vQntWgERSq1inqEOYXQywskIPAf_fROcZOEJRU"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    GAS_URL = st.secrets["GAS_URL"]
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        st.session_state.teachers = sorted(df["老師"].unique().tolist())
    else:
        st.session_state.teachers = ["MLB"]
except:
    st.error("讀取失敗")
    st.stop()

# --- 2. 多場賽事錄入介面 ---
with st.expander("📝 錄入新注單 (支援串關/多場)", expanded=False):
    with st.form("multi_match_form"):
        f_t = st.text_input("老師姓名")
        f_date = st.date_input("日期")
        
        # 使用一個 list 來存放這一張單的所有賽事
        num_matches = st.number_input("這張單有幾場比賽？", min_value=1, max_value=10, value=1)
        
        match_data = []
        for i in range(int(num_matches)):
            st.markdown(f"**第 {i+1} 場賽事**")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            m = c1.text_input(f"對戰組合", key=f"m_{i}")
            p = c2.text_input(f"預測內容", key=f"p_{i}")
            s = c3.text_input(f"實際比分", key=f"s_{i}")
            r = c4.selectbox(f"結果", ["正確", "錯誤"], key=f"r_{i}")
            match_data.append({"match": m, "pred": p, "score": s, "result": r})
            
        if st.form_submit_button("確認提交整張注單"):
            # 產生一個唯一的注單編號 (時間戳記)
            slip_id = f"SLIP-{int(time.time())}"
            
            payload = {
                "teacher": f_t,
                "date": f_date.strftime("%Y-%m-%d"),
                "slipId": slip_id,
                "matches": match_data
            }
            
            response = requests.post(GAS_URL, json=payload)
            if response.status_code == 200:
                st.success("整張注單已同步！")
                st.rerun()

st.divider()

# --- 3. 核心計算邏輯：單場 vs 注單 ---
cur_t = st.session_state.current_teacher # 假設已有切換老師邏輯
df_t = df[df["老師"] == cur_t]

if not df_t.empty:
    # A. 單場統計
    total_m = len(df_t)
    wins_m = len(df_t[df_t["結果"] == "正確"])
    
    # B. 注單統計 (串關)
    # 根據「注單編號」分組，如果該組內有任何一個「錯誤」，該注單就是錯誤
    slip_stats = df_t.groupby("注單編號")["結果"].apply(lambda x: "正確" if all(x == "正確") else "錯誤")
    total_s = len(slip_stats)
    wins_s = len(slip_stats[slip_stats == "正確"])
    
    # UI 顯示
    c1, c2 = st.columns(2)
    with c1:
        st.metric("單場勝率", f"{(wins_m/total_m*100):.1f}%", f"{wins_m}/{total_m} 場")
    with c2:
        st.metric("注單勝率 (串關)", f"{(wins_s/total_s*100):.1f}%", f"{wins_s}/{total_s} 張")
    
    st.table(df_t.iloc[::-1])
