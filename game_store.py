import streamlit as st
import pandas as pd
import requests
import time

st.title("🏆 賽事雲端統計看板")

# 1. 讀取資料
try:
    SHEET_ID = "1BnNF9vQntWgERSq1inqEOYXQywskIPAf_fROcZOEJRU"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    GAS_URL = st.secrets["GAS_URL"]
    df = pd.read_csv(CSV_URL)
    
    # 基本清理
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        # 確保「注單編號」存在，若不存在則補空值避免報錯
        if "注單編號" not in df.columns:
            df["注單編號"] = "無編號"
        
        st.session_state.teachers = sorted(df["老師"].unique().tolist())
    else:
        st.session_state.teachers = ["MLB"]
except Exception as e:
    st.error(f"讀取失敗：{e}")
    st.stop()

# 老師切換邏輯
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

# --- 2. UI 錄入表單 (支援多場/串關) ---
with st.expander("📝 錄入新注單 (串關/多場)", expanded=False):
    with st.form("multi_form", clear_on_submit=True):
        f_t = st.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = st.date_input("日期")
        num_m = st.number_input("這張單有幾場比賽？", 1, 10, 1)
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"--- **賽事 {i+1}** ---")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            m_val = c1.text_input("對戰組合", key=f"m_{i}")
            p_val = c2.text_input("預測內容", key=f"p_{i}")
            s_val = c3.text_input("實際比分", key=f"s_{i}")
            r_val = c4.selectbox("結果", ["正確", "錯誤"], key=f"r_{i}")
            m_list.append({"match": m_val, "pred": p_val, "score": s_val, "result": r_val})
            
        if st.form_submit_button("確認提交整張注單"):
            s_id = f"SLIP-{int(time.time())}" # 建立唯一編號
            payload = {"teacher": f_t, "date": f_date.strftime("%Y-%m-%d"), "slipId": s_id, "matches": m_list}
            res = requests.post(GAS_URL, json=payload)
            if res.status_code == 200:
                st.success("存檔成功！")
                st.rerun()

st.divider()

# --- 3. 顯示按鈕與統計 ---
cols = st.columns(len(st.session_state.teachers))
for i, t in enumerate(st.session_state.teachers):
    with cols[i]:
        if st.button(t, type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t]

if not df_display.empty:
    # 單場勝率
    t_m = len(df_display)
    w_m = len(df_display[df_display["結果"] == "正確"])
    
    # 注單(串關)勝率邏輯
    # 以「注單編號」分組，每一組必須「全部正確」才算這張單過關
    slip_results = df_display.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
    t_s = len(slip_results)
    w_s = sum(slip_results)

    m1, m2 = st.columns(2)
    m1.metric("單場總勝率", f"{(w_m/t_m*100):.1f}%", f"{w_m}/{t_m} 場")
    m2.metric("注單(串關)勝率", f"{(w_s/t_s*100):.1f}%", f"{int(w_s)}/{t_s} 張")

    st.subheader(f"📍 {cur_t} 的歷史記錄")
    st.table(df_display.iloc[::-1])
