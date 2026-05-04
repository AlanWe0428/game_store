import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 標題
st.title("🏆 賽事雲端統計系統")

# 1. 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取資料 (從 Secrets 中設定的網址讀取)
df = conn.read(ttl="0s")

# --- 3. 老師名單管理 (側邊欄功能找回) ---
if 'teachers' not in st.session_state:
    # 嘗試從比賽資料中抓取現有老師名單，若無則預設
    if not df.empty and "老師" in df.columns:
        existing_teachers = df["老師"].unique().tolist()
        st.session_state.teachers = existing_teachers if existing_teachers else ["MLB"]
    else:
        st.session_state.teachers = ["MLB"]

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

# 側邊欄：新增與刪除老師
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
    
    # 刪除老師 (從目前名單中移除)
    del_t = st.selectbox("選擇要隱藏的老師", st.session_state.teachers)
    if st.button("❌ 刪除老師"):
        if len(st.session_state.teachers) > 1:
            st.session_state.teachers.remove(del_t)
            if st.session_state.current_teacher == del_t:
                st.session_state.current_teacher = st.session_state.teachers[0]
            st.rerun()

# --- 4. UI 佈局 (老師切換按鈕) ---
cols = st.columns(len(st.session_state.teachers) + 1)
with cols[0]:
    if st.button("➕ 新增資料"):
        st.session_state.show_form = True

for i, t in enumerate(st.session_state.teachers):
    with cols[i+1]:
        # 標示目前選中的老師
        is_active = st.session_state.current_teacher == t
        if st.button(t, type="primary" if is_active else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

st.divider()

# --- 5. 顯示數據與計算勝率 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t] if not df.empty else pd.DataFrame()

if not df_display.empty:
    # 計算該老師勝率
    total = len(df_display)
    wins = len(df_display[df_display["結果"] == "✅"])
    win_rate = (wins / total) * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{cur_t} 總場數", f"{total} 場")
    c2.metric("命中數", f"{wins} 場")
    c3.metric("目前勝率", f"{win_rate:.1f}%")
    
    # 依照日期排序顯示
    st.table(df_display.sort_values(by="日期", ascending=False))
else:
    st.info(f"目前尚無 {cur_t} 的預測資料")

# --- 6. 表單輸入並寫回 Google Sheets ---
if st.session_state.get('show_form'):
    with st.expander("📝 錄入新賽事資料", expanded=True):
        with st.form("input_form"):
            # 自動帶入當前選中的老師
            f_t = st.selectbox("負責老師", st.session_state.teachers, 
                               index=st.session_state.teachers.index(cur_t))
            f_date = st.date_input("日期")
            f_match = st.text_input("對戰組合")
            f_pred = st.text_input("預測內容")
            f_score = st.text_input("實際比分")
            f_res = st.radio("結果", ["✅", "❌"], horizontal=True)
            
            if st.form_submit_button("確認同步至雲端"):
                new_row = pd.DataFrame([{
                    "老師": f_t,
                    "日期": f_date.strftime("%Y-%m-%d"),
                    "對戰組合": f_match,
                    "預測內容": f_pred,
                    "實際比分": f_score,
                    "結果": f_res
                }])
                # 更新試算表
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success("同步成功！")
                st.session_state.show_form = False
                st.rerun()
