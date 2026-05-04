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
except Exception as e:
    st.error("請檢查 Secrets 中的 SHEET_URL 設定。")
    st.stop()

# --- 2. 老師管理邏輯 (側邊欄找回) ---
if 'teachers' not in st.session_state:
    # 優先從試算表抓取既有老師，若無則預設
    if not df.empty and "老師" in df.columns:
        st.session_state.teachers = df["老師"].unique().tolist()
    else:
        st.session_state.teachers = ["MLB", "分析師A"]

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

# 側邊欄管理
with st.sidebar:
    st.header("👨‍🏫 老師管理系統")
    
    # 新增老師
    new_t = st.text_input("輸入新老師姓名")
    if st.button("新增老師"):
        if new_t and new_t not in st.session_state.teachers:
            st.session_state.teachers.append(new_t)
            st.success(f"已新增: {new_t}")
            st.rerun()

    st.divider()
    
    # 刪除老師 (從列表移除)
    del_t = st.selectbox("選擇要移除的老師", st.session_state.teachers)
    if st.button("❌ 移除選中老師"):
        if len(st.session_state.teachers) > 1:
            st.session_state.teachers.remove(del_t)
            if st.session_state.current_teacher == del_t:
                st.session_state.current_teacher = st.session_state.teachers[0]
            st.rerun()
        else:
            st.error("至少需保留一名老師")

# --- 3. UI 佈局 (老師切換按鈕) ---
cols = st.columns(len(st.session_state.teachers) + 1)
with cols[0]:
    # 提供連結讓使用者去填單 (例如您做好的 Google 表單連結)
    if st.button("➕ 前往填單", type="primary"):
        st.info(f"請點擊連結填寫資料：{SHEET_URL}")

for i, t in enumerate(st.session_state.teachers):
    with cols[i+1]:
        is_active = st.session_state.current_teacher == t
        if st.button(t, type="primary" if is_active else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

st.divider()

# --- 4. 數據統計與顯示 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t] if not df.empty else pd.DataFrame()

if not df_display.empty:
    # 勝率計算邏輯
    total = len(df_display)
    # 確保欄位名稱正確，並計算勾選正確的數量
    wins = len(df_display[df_display["結果"].isin(["✅", "正確"])])
    win_rate = (wins / total * 100) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("總預測場數", f"{total} 場")
    c2.metric("準確命中", f"{wins} 場")
    c3.metric("目前勝率", f"{win_rate:.1f}%")

    st.subheader(f"📍 {cur_t} 的歷史記錄")
    st.table(df_display.sort_index(ascending=False))
else:
    st.info(f"目前尚無 {cur_t} 的資料。")
