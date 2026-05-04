import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 標題
st.title("🏆 賽事雲端統計系統")

# 1. 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取資料 (從 Secrets 中設定的網址讀取)
df = conn.read(ttl="0s") # ttl=0s 表示不快取，每次都抓最新的

# 3. 老師名單管理 (這部分可以先寫死或從試算表讀取)
if 'teachers' not in st.session_state:
    st.session_state.teachers = ["MLB", "分析師A", "分析師B"]
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

# --- UI 佈局 (老師按鈕) ---
cols = st.columns(len(st.session_state.teachers) + 1)
with cols[0]:
    if st.button("➕ 新增資料"):
        st.session_state.show_form = True

for i, t in enumerate(st.session_state.teachers):
    with cols[i+1]:
        if st.button(t, type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t

# --- 顯示數據與計算勝率 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t] if not df.empty else pd.DataFrame()

if not df_display.empty:
    win_rate = (len(df_display[df_display["結果"] == "✅"]) / len(df_display)) * 100
    st.metric(f"{cur_t} 目前勝率", f"{win_rate:.1f}%")
    st.table(df_display)
else:
    st.info("尚無資料")

# --- 4. 表單輸入並寫回 Google Sheets ---
if st.session_state.get('show_form'):
    with st.form("input_form"):
        f_date = st.date_input("日期")
        f_match = st.text_input("對戰組合")
        f_pred = st.text_input("預測內容")
        f_score = st.text_input("實際比分")
        f_res = st.radio("結果", ["✅", "❌"], horizontal=True)
        
        if st.form_submit_button("確認存檔"):
            new_row = pd.DataFrame([{
                "老師": cur_t,
                "日期": f_date.strftime("%Y-%m-%d"),
                "對戰組合": f_match,
                "預測內容": f_pred,
                "實際比分": f_score,
                "結果": f_res
            }])
            # 結合舊資料與新資料
            updated_df = pd.concat([df, new_row], ignore_index=True)
            # 寫回 Google Sheets
            conn.update(data=updated_df)
            st.success("資料已成功同步至 Google Sheets！")
            st.session_state.show_form = False
            st.rerun()