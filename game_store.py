import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 標題
st.title("🏆 賽事雲端統計系統")

# 1. 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取資料 (強制不快取)
df = conn.read(ttl="0s")

# 確保 df 即使為空也有正確的欄位名
columns = ["老師", "日期", "對戰組合", "預測內容", "實際比分", "結果"]
if df.empty:
    df = pd.DataFrame(columns=columns)

# --- 3. 老師名單與管理 ---
if 'teachers' not in st.session_state:
    existing_teachers = df["老師"].unique().tolist() if not df.empty else []
    st.session_state.teachers = list(set(["MLB"] + [t for t in existing_teachers if str(t) != 'nan']))

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

with st.sidebar:
    st.header("👨‍🏫 老師管理")
    new_t = st.text_input("新增老師姓名")
    if st.button("確認新增"):
        if new_t and new_t not in st.session_state.teachers:
            st.session_state.teachers.append(new_t)
            st.rerun()
    st.divider()
    del_t = st.selectbox("移除顯示", st.session_state.teachers)
    if st.button("❌ 移除"):
        if len(st.session_state.teachers) > 1:
            st.session_state.teachers.remove(del_t)
            st.session_state.current_teacher = st.session_state.teachers[0]
            st.rerun()

# --- 4. 按鈕佈局 ---
cols = st.columns(len(st.session_state.teachers) + 1)
with cols[0]:
    if st.button("➕ 資料輸入", type="primary"):
        st.session_state.show_form = True

for i, t in enumerate(st.session_state.teachers):
    with cols[i+1]:
        if st.button(t, type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

st.divider()

# --- 5. 顯示數據與計算勝率 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t]

if not df_display.empty:
    total = len(df_display)
    wins = len(df_display[df_display["結果"].str.contains("✅", na=False)])
    win_rate = (wins / total) * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總場數", f"{total}")
    c2.metric("命中數", f"{wins}")
    c3.metric("勝率", f"{win_rate:.1f}%")
    st.table(df_display.sort_index(ascending=False))
else:
    st.info(f"尚無 {cur_t} 的資料")

# --- 6. 強健的寫入邏輯 ---
if st.session_state.get('show_form'):
    with st.expander("📝 錄入新資料", expanded=True):
        with st.form("input_form", clear_on_submit=True):
            f_t = st.selectbox("負責老師", st.session_state.teachers, index=st.session_state.teachers.index(cur_t))
            f_date = st.date_input("日期")
            f_match = st.text_input("對戰組合")
            f_pred = st.text_input("預測內容")
            f_score = st.text_input("實際比分")
            f_res = st.radio("結果", ["✅", "❌"], horizontal=True)
            
            if st.form_submit_button("確認存檔"):
                # 準備新的一列
                new_row = pd.DataFrame([{
                    "老師": f_t,
                    "日期": f_date.strftime("%Y-%m-%d"),
                    "對戰組合": f_match,
                    "預測內容": f_pred,
                    "實際比分": f_score,
                    "結果": f_res
                }])
                
                # 合併資料並過濾掉全空列
                updated_df = pd.concat([df, new_row], ignore_index=True).dropna(how='all')
                
                try:
                    # 使用 conn.update 並明確指定讀取回來的 df 結構
                    conn.update(data=updated_df)
                    st.cache_data.clear() # 清除所有快取
                    st.session_state.show_form = False
                    st.success("同步成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"寫入發生錯誤。請確認您的 Secrets 網址包含 /edit。 錯誤訊息: {e}")
