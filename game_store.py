import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="賽事雲端看板", layout="wide")
st.title("🏆 賽事雲端統計看板")

# 1. 讀取資料
try:
    # 這裡建議使用 Secrets 裡的網址，最能避免 404 錯誤
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
        # 預防性檢查：如果試算表還沒手動加欄位，程式自動補上避免崩潰
        if "注單編號" not in df.columns:
            df["注單編號"] = "舊資料"
        
        st.session_state.teachers = sorted(df["老師"].unique().tolist())
    else:
        st.session_state.teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗：{e}")
    st.info("提示：請確認試算表已開啟『知道連結的任何人皆可檢視』權限。")
    st.stop()

# 初始化老師選取
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

# --- 2. UI 錄入表單 (支援多場/串關) ---
with st.expander("📝 錄入新注單 (支援單場或串關)", expanded=False):
    with st.form("multi_form", clear_on_submit=True):
        f_t = st.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = st.date_input("日期")
        num_m = st.number_input("這張單有幾場比賽？(串關請增加場數)", 1, 10, 1)
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"--- **賽事 {i+1}** ---")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            m_val = c1.text_input("對戰組合", key=f"m_{i}", placeholder="例如：湖人 vs 勇士")
            p_val = c2.text_input("預測內容", key=f"p_{i}", placeholder="例如：大分 220.5")
            s_val = c3.text_input("實際比分", key=f"s_{i}", placeholder="例如：110:115")
            r_val = c4.selectbox("結果", ["正確", "錯誤"], key=f"r_{i}")
            m_list.append({"match": m_val, "pred": p_val, "score": s_val, "result": r_val})
            
        if st.form_submit_button("🚀 確認提交整張注單"):
            # 自動生成唯一注單編號
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
                    st.success("✅ 存檔成功！資料已寫入試算表。")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 傳送失敗，請檢查 GAS 部署權限。")
            except:
                st.error("❌ 連線至 Google 失敗。")

st.divider()

# --- 3. 顯示老師切換按鈕 ---
cols = st.columns(len(st.session_state.teachers))
for i, t in enumerate(st.session_state.teachers):
    with cols[i]:
        if st.button(t, key=f"t_{t}", use_container_width=True, 
                     type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# --- 4. 數據統計邏輯 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # A. 單場統計 (每一列獨立算)
    t_m = len(df_display)
    w_m = len(df_display[df_display["結果"] == "正確"])
    
    # B. 注單(串關)統計
    # 邏輯：按注單編號分組，只要組內有任何一個「錯誤」，該注單就算輸
    slip_results = df_display.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
    t_s = len(slip_results)
    w_s = sum(slip_results)

    # 顯示指標卡
    m1, m2 = st.columns(2)
    m1.metric(f"🏀 {cur_t} 單場勝率", f"{(w_m/t_m*100):.1f}%", f"命中 {w_m} / 總 {t_m} 場")
    m2.metric(f"🎫 {cur_t} 注單勝率", f"{(w_s/t_s*100):.1f}%", f"過關 {int(w_s)} / 總 {t_s} 張")

    st.subheader(f"📍 {cur_t} 歷史明細 (最新的在最前)")
    # 反轉顯示資料
    st.dataframe(df_display.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info(f"目前尚無 {cur_t} 的數據紀錄。")
