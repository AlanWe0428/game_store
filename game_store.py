import streamlit as st
import pandas as pd
import requests
import time

# 1. 頁面基本設定
st.set_page_config(page_title="Sports Dashboard", layout="wide")
st.title("🏆 賽事雲端統計看板")

# 2. 從 Secrets 讀取資料與路徑轉換
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    # 自動轉換為 CSV 下載連結
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        # 資料清理
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        # 確保注單編號欄位存在
        if "注單編號" not in df.columns:
            df["注單編號"] = "N/A"
        
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"讀取失敗，請檢查 Secrets 設定與試算表共用權限。")
    st.info(f"錯誤訊息: {e}")
    st.stop()

# 初始化老師選取狀態
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 (場數選擇放在 Form 外) ---
with st.expander("📝 錄入新注單 (支援單場或串關)", expanded=False):
    num_m = st.number_input("這張注單包含幾場比賽？", min_value=1, max_value=10, value=1)
    
    with st.form("multi_match_form", clear_on_submit=True):
        st.write(f"請填寫以下 {int(num_m)} 場賽事內容：")
        f_t = st.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = st.date_input("日期")
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"**賽事 {i+1}**")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            m_v = c1.text_input("對戰組合", key=f"match_in_{i}", placeholder="例：湖人 vs 勇士")
            p_v = c2.text_input("預測內容", key=f"pred_in_{i}", placeholder="例：大分 220.5")
            s_v = c3.text_input("實際比分", key=f"score_in_{i}", placeholder="例：110:105")
            r_v = c4.selectbox("結果", ["正確", "錯誤"], key=f"res_in_{i}")
            m_list.append({"match": m_v, "pred": p_v, "score": s_v, "result": r_v})
        
        if st.form_submit_button("🚀 確認提交整張注單"):
            if not f_t:
                st.error("請輸入老師姓名")
            else:
                # 產生唯一注單編號
                s_id = f"SLIP-{int(time.time())}"
                payload = {
                    "teacher": f_t,
                    "date": f_date.strftime("%Y-%m-%d"),
                    "slipId": s_id,
                    "matches": m_list
                }
                try:
                    res = requests.post(GAS_URL, json=payload)
                    if res.status_code == 200:
                        st.success("存檔成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("傳送失敗，請檢查 GAS 部署。")
                except:
                    st.error("無法連線至 Google 服務。")

st.divider()

# --- 4. 老師切換按鈕 ---
btn_cols = st.columns(len(all_teachers))
for i, t in enumerate(all_teachers):
    with btn_cols[i]:
        if st.button(t, key=f"btn_sel_{t}", use_container_width=True, 
                     type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# --- 5. 數據統計與顯示 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # A. 單場統計
    total_m = len(df_display)
    wins_m = len(df_display[df_display["結果"] == "正確"])
    rate_m = (wins_m / total_m * 100) if total_m > 0 else 0
    
    # B. 注單(串關)統計
    valid_df = df_display.dropna(subset=["注單編號"])
    if not valid_df.empty:
        # 核心邏輯：同編號必須全部正確
        slip_res = valid_df.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
        total_s = len(slip_res)
        wins_s = sum(slip_res)
        rate_s = (wins_s / total_s * 100) if total_s > 0 else 0
    else:
        total_s, wins_s, rate_s = 0, 0, 0

    # 顯示指標卡
    m1, m2 = st.columns(2)
    m1.metric("單場勝率", f"{rate_m:.1f}%", f"命中 {wins_m} / 總 {total_m} 場")
    m2.metric("注單勝率 (串關)", f"{rate_s:.1f}%", f"過關 {int(wins_s)} / 總 {total_s} 張")

    st.subheader(f"📍 {cur_t} 歷史明細")
    st.dataframe(df_display.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info(f"目前尚無 {cur_t} 的數據紀錄。")
