import streamlit as st
import pandas as pd
import requests

# 標題
st.title("🏆 賽事雲端統計看板")

# 1. 讀取資料 (使用 Secrets 變數)
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    # 轉換 CSV 讀取連結
    CSV_URL = SHEET_URL.replace("/edit?usp=sharing", "/export?format=csv")
    # 這裡加入一個參數確保每次都讀到最新的資料
    df = pd.read_csv(CSV_URL)
    
    # 清理資料：過濾掉空行，確保「老師」欄位是字串
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        # 自動偵測所有不重複的老師名字
        st.session_state.teachers = sorted(df["老師"].unique().tolist())
    else:
        if 'teachers' not in st.session_state:
            st.session_state.teachers = ["MLB"]

except Exception as e:
    st.error(f"❌ 讀取失敗，請確認 Secrets 設定。詳細訊息: {e}")
    st.stop()

# 確保當前選中的老師有效
if 'current_teacher' not in st.session_state or st.session_state.current_teacher not in st.session_state.teachers:
    st.session_state.current_teacher = st.session_state.teachers[0]

# --- 2. UI 填單表單 ---
with st.expander("📝 直接錄入新賽事", expanded=False):
    with st.form("ui_form", clear_on_submit=True):
        st.write("💡 填寫完畢按『確認存檔』後，網頁會自動重新整理更新數據。")
        f_t = st.text_input("老師姓名 (輸入新名字會自動新增按鈕)")
        f_date = st.date_input("日期")
        f_match = st.text_input("對戰組合")
        f_pred = st.text_input("預測內容")
        f_score = st.text_input("實際比分")
        f_res = st.radio("結果", ["正確", "錯誤", "✅", "❌"], horizontal=True)
        
        if st.form_submit_button("確認存檔"):
            if not f_t:
                st.warning("請填寫老師姓名")
            else:
                payload = {
                    "teacher": f_t,
                    "date": f_date.strftime("%Y-%m-%d"),
                    "match": f_match,
                    "pred": f_pred,
                    "score": f_score,
                    "result": f_res
                }
                # 發送資料到 Google Apps Script 寫入
                response = requests.post(GAS_URL, json=payload)
                if response.status_code == 200:
                    st.success(f"成功！資料已同步至雲端。")
                    st.rerun()
                else:
                    st.error("傳送失敗，請確認 GAS 部署為『任何人』。")

st.divider()

# --- 3. 看板顯示邏輯 ---
# 顯示老師切換按鈕
cols = st.columns(len(st.session_state.teachers))
for i, t in enumerate(st.session_state.teachers):
    with cols[i]:
        is_active = st.session_state.current_teacher == t
        if st.button(t, key=f"btn_{t}", type="primary" if is_active else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# 統計數據計算
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t] if not df.empty else pd.DataFrame()

if not df_display.empty:
    total = len(df_display)
    # 計算命中數：包含試算表中的 "正確" 或 "✅"
    wins = len(df_display[df_display["結果"].isin(["✅", "正確"])])
    win_rate = (wins / total * 100) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{cur_t} 總場數", f"{total} 場")
    c2.metric("命中數", f"{wins} 場")
    c3.metric("目前勝率", f"{win_rate:.1f}%")

    st.subheader(f"📍 {cur_t} 的歷史記錄")
    # 將資料反轉顯示，最新的在最上面
    st.table(df_display.iloc[::-1])
else:
    st.info(f"目前尚無 {cur_t} 的資料。")
