import streamlit as st
import pandas as pd
import requests
import time

# 必須在最前面初始化頁面
st.set_page_config(page_title="賽事雲端看板", layout="wide")
st.title("🏆 賽事雲端統計看板")

# 1. 讀取資料
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    # 自動轉換為 CSV 下載網址
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        # 如果試算表還沒加欄位，程式自動補上
        if "注單編號" not in df.columns:
            df["注單編號"] = "舊資料"
        
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗：{e}")
    st.stop()

# --- 重要：初始化老師選擇，防止 NameError ---
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 2. UI 錄入表單 ---
with st.expander("📝 錄入新注單 (支援單場或串關)", expanded=False):
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
            
        if st.form_submit_button("🚀 確認提交整張注單"):
            s_id = f"SLIP-{int(time.time())}" 
            payload = {"teacher": f_t, "date": f_date.strftime("%Y-%m-%d"), "slipId": s_id, "matches": m_list}
            res = requests.post(GAS_URL, json=payload)
            if res.status_code == 200:
                st.success("✅ 存檔成功！")
                time.sleep(1)
                st.rerun()

st.divider()

# --- 3. 顯示切換按鈕 ---
cols = st.columns(len(all_teachers))
for i, t in enumerate(all_teachers):
    with cols[i]:
        if st.button(t, key=f"t_{t}", use_container_width=True, 
                     type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# --- 4. 數據統計邏輯 (防護加強版) ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # A. 單場統計
    t_m = len(df_display)
    w_m = len(df_display[df_display["結果"] == "正確"])
    rate_m = (w_m / t_m * 100) if t_m > 0 else 0
    
    # B. 注單(串關)統計
    # 確保注單編號存在且不為空
    valid_df = df_display.dropna(subset=["注單編號"])
    if not valid_df.empty:
        slip_results = valid_df.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
        t_s = len(slip_results)
        w_s = sum(slip_results)
        rate_s = (w_s / t_s * 100) if t_s > 0 else 0
    else:
        t_s, w_s, rate_s = 0, 0, 0

    m1, m2 = st.columns(2)
    m1.metric(f"🏀 {cur_t} 單場勝率", f"{rate_m:.1f}%", f"命中 {w_m} / 總 {t_m} 場")
    m2.metric(f"🎫 {cur_t} 注單勝率", f"{rate_s:.1f}%", f"過關 {int(w_s)} / 總 {t_s} 張")

    st.subheader(f"📍 {cur_t} 歷史明細")
    st.dataframe(df_display.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info(f"目前尚無 {cur_t} 的數據紀錄。")
