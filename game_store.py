import streamlit as st
import pandas as pd
import requests
import time

# 1. 頁面基本設定
st.set_page_config(page_title="Sports Dashboard", layout="wide")

# --- 隱藏右下角 Manage app 的 CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* 隱藏右下角管理按鈕 */
    .stAppToolbar {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
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
    
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        if "注單編號" not in df.columns:
            df["注單編號"] = "N/A"
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗，請確認權限。")
    st.stop()

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 ---
with st.expander("📝 錄入新注單 (支援單場或串關)", expanded=False):
    num_m = st.number_input("這張注單包含幾場比賽？", min_value=1, max_value=10, value=1)
    with st.form("multi_match_form", clear_on_submit=True):
        f_t = st.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = st.date_input("日期")
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"**賽事 {i+1}**")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            m_v = c1.text_input("對戰組合", key=f"match_{i}")
            p_v = c2.text_input("預測內容", key=f"pred_{i}")
            s_v = c3.text_input("實際比分", key=f"score_{i}")
            r_v = c4.selectbox("結果", ["正確", "錯誤"], key=f"res_{i}")
            m_list.append({"match": m_v, "pred": p_v, "score": s_v, "result": r_v})
        
        if st.form_submit_button("🚀 確認提交整張注單"):
            s_id = f"SLIP-{int(time.time())}"
            payload = {"teacher": f_t, "date": f_date.strftime("%Y-%m-%d"), "slipId": s_id, "matches": m_list}
            try:
                res = requests.post(GAS_URL, json=payload, timeout=10)
                if res.status_code == 200:
                    st.success("✅ 存檔成功！")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 連線異常：{str(e)}")

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
    # 勝率計算
    t_m = len(df_display)
    w_m = len(df_display[df_display["結果"] == "正確"])
    
    valid_df = df_display.dropna(subset=["注單編號"])
    slip_res = valid_df.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
    t_s = len(slip_res)
    w_s = sum(slip_res)

    c1, c2 = st.columns(2)
    c1.metric("單場勝率", f"{(w_m/t_m*100):.1f}%", f"{w_m}/{t_m} 場")
    c2.metric("注單勝率 (串關)", f"{(w_s/t_s*100 if t_s > 0 else 0):.1f}%", f"{int(w_s)}/{t_s} 張")

    st.subheader(f"📍 {cur_t} 歷史明細 (按注單收合)")
    
    # --- 關鍵：按注單編號分組並收合 ---
    # 取得所有注單編號並反轉（最新的在上面）
    unique_slips = df_display["注單編號"].unique()[::-1]
    
    for sid in unique_slips:
        slip_data = df_display[df_display["注單編號"] == sid]
        # 判定這張單整體的結果
        is_win = all(slip_data["結果"] == "正確")
        date_str = slip_data["日期"].iloc[0]
        status_icon = "✅" if is_win else "❌"
        
        # Expander 標題顯示日期、編號與結果
        with st.expander(f"{status_icon} 日期：{date_str} | 注單：{sid} ({len(slip_data)} 場)"):
            st.table(slip_data[["對戰組合", "預測內容", "實際比分", "結果"]])
else:
    st.info("尚無數據紀錄")
