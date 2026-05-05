import streamlit as st
import pandas as pd
import requests
import time

# 1. 頁面基本設定
st.set_page_config(page_title="賽事雲端看板", layout="wide")
st.title("🏆 賽事雲端統計看板")

# 2. 從 Secrets 讀取資料
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
        # 清理資料：確保老師欄位存在且無空值
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        # 防呆：確保注單編號欄位存在
        if "注單編號" not in df.columns:
            df["注單編號"] = "舊資料"
        
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗，請確認 Secrets 或試算表共用權限。")
    st.info(f"詳細錯誤訊息: {e}")
    st.stop()

# 初始化 Session State (確保選取的老師不會因重新整理而消失)
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 (解決場數顯示問題) ---
with st.expander("📝 錄入新注單 (支援單場或串關)", expanded=False):
    # 【關鍵】將場數選擇放在 Form 外面，這樣數字改變時下方輸入框才會即時長出來
    num_m = st.number_input("這張注單包含幾場比賽？", min_value=1, max_value=10, value=1)
    
    with st.form("multi_match_form", clear_on_submit=True):
        st.write(f"💡 請填寫以下 {int(num_m)} 場賽事細節：")
        f_t = st.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = st.date_input("日期")
        
        m_list = []
        # 根據上面的 num_m 動態產生輸入欄位
        for i in range(int(num_m)):
            st.markdown(f"**📍 賽事 {i+1}**")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            m_val = c1.text_input("對戰組合", key=f"match_{i}", placeholder="例：湖人 vs 勇士")
            p_val = c2.text_input("預測內容", key=f"pred_{i}", placeholder="例：大分 220.5")
            s_val = c3.text_input("實際比分", key=f"score_{i}", placeholder="例：110:105")
            r_val = c4.selectbox("結果", ["正確", "錯誤"], key=f"res_{i}")
            m_list.append({"match": m_val, "pred": p_val, "score": s_val, "result": r_val})
        
        submit_btn = st.form_submit_button("🚀 確認提交整張注單")
        
        if submit_btn:
            if not f_t:
                st.error("請輸入老師姓名！")
            else:
                # 產生唯一的注單編號
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
                        st.success("✅ 資料已成功同步至雲端試算表！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 傳送失敗，請檢查 GAS 部署設定。")
                except:
                    st.error("❌ 無法連線至 Google 服務。")

st.divider()

# --- 4. 老師切換按鈕 ---
st.write("### 👨‍🏫 選擇老師查看統計")
btn_cols = st.columns(len(all_teachers))
for i, t in enumerate(all_teachers):
    with btn_cols[i]:
        is_active = (st.session_state.current_teacher == t)
        if st.button(t, key=f"btn_{t}", use_container_width=True, 
                     type="primary" if is_active else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# --- 5. 數據統計與顯示 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # A. 單場勝率計算
    total_m = len(df_display)
    wins_m = len(df_display[df_display["結果"] == "正確"])
    rate_m = (wins_m / total_m * 100) if total_m > 0 else 0
    
    # B. 注單(串關)勝率計算
    # 邏輯：同一個注單編號下，必須「全部正確」才算過關
    valid_df = df_display.dropna(subset=["注單編號"])
    if not valid_df.empty:
        # groupby 判斷每組編號是否全部為正確
        slip_results = valid_df.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
        total_s = len(slip_results)
        wins_s = sum(slip_results)
        rate_s = (wins_s / total_s * 100) if total_s > 0 else 0
    else:
        total_s, wins_s, rate_s = 0, 0, 0

    # 顯示指標卡
    m1, m2 = st.columns(2)
    m1.metric(f"🏀 {cur_t} 單場勝率", f"{rate_m:.1f}%", f"命中 {wins_m} / 總 {total_m} 場")
    m2.metric(f"🎫 {cur_t} 注單勝率 (串關)", f"{rate_s:.1f}%", f"過關 {int(wins_s)}
