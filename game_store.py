import streamlit as st
import pandas as pd

# 標題
st.title("🏆 賽事雲端統計系統")

# 1. 讀取資料 (從 Secrets 取得 URL)
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    # 轉換為 CSV 匯出連結以進行讀取 (免金鑰)
    CSV_URL = SHEET_URL.replace("/edit?usp=sharing", "/export?format=csv")
    df = pd.read_csv(CSV_URL)
    
    # --- 自動化優化：清除髒資料並確保型別正確 ---
    if not df.empty:
        # 過濾掉「老師」欄位為空的行，並轉為字串
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
except Exception as e:
    st.error("請檢查 Secrets 中的 SHEET_URL 設定。")
    st.stop()

# --- 2. 老師管理邏輯 (自動偵測新老師) ---
# 自動從資料表抓取所有不重複的老師名字
if not df.empty and "老師" in df.columns:
    detected_teachers = sorted(df["老師"].unique().tolist())
    # 將偵測到的老師與 Session State 同步
    st.session_state.teachers = detected_teachers if detected_teachers else ["MLB"]
else:
    if 'teachers' not in st.session_state:
        st.session_state.teachers = ["MLB"]

# 確保當前選中的老師在名單內
if 'current_teacher' not in st.session_state or st.session_state.current_teacher not in st.session_state.teachers:
    st.session_state.current_teacher = st.session_state.teachers[0]

# 側邊欄保留手動微調功能
with st.sidebar:
    st.header("👨‍🏫 老師管理系統")
    st.info("系統會自動偵測試算表中的新老師。您也可以在此手動管理暫時名單。")
    
    new_t = st.text_input("手動預增老師")
    if st.button("手動新增"):
        if new_t and new_t not in st.session_state.teachers:
            st.session_state.teachers.append(new_t)
            st.rerun()

    st.divider()
    
    del_t = st.selectbox("移除顯示", st.session_state.teachers)
    if st.button("❌ 移除"):
        if len(st.session_state.teachers) > 1:
            st.session_state.teachers.remove(del_t)
            st.rerun()

# --- 3. UI 佈局 ---
cols = st.columns(len(st.session_state.teachers) + 1)
with cols[0]:
    # 這裡可以改成您的 Google 表單連結
    if st.button("➕ 前往填單", type="primary"):
        st.info("💡 提示：若填入新老師姓名，提交後重新整理此頁面即可看到新按鈕。")
        st.markdown(f"[👉 點我開啟填單系統 (支援多筆輸入)]({SHEET_URL})")

for i, t in enumerate(st.session_state.teachers):
    with cols[i+1]:
        is_active = st.session_state.current_teacher == t
        if st.button(t, key=f"btn_{t}", type="primary" if is_active else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

st.divider()

# --- 4. 數據統計與顯示 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t] if not df.empty else pd.DataFrame()

if not df_display.empty:
    total = len(df_display)
    # 支援多種正確格式
    wins = len(df_display[df_display["結果"].isin(["✅", "正確", "TRUE", True])])
    win_rate = (wins / total * 100) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("總預測場數", f"{total} 場")
    c2.metric("準確命中", f"{wins} 場")
    c3.metric("目前勝率", f"{win_rate:.1f}%")

    st.subheader(f"📍 {cur_t} 的歷史記錄")
    st.table(df_display.sort_index(ascending=False))
else:
    st.info(f"目前尚無 {cur_t} 的資料。若剛填寫請稍候並重新整理。")
