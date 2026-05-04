import streamlit as st
import pandas as pd
import os

# 設定檔案名稱
DATA_FILE = "match_records.xlsx"
TEACHER_FILE = "teachers.csv"  # 儲存老師名單

# --- 1. 資料處理函式 ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    return pd.DataFrame(columns=["老師", "日期", "對戰組合", "預測內容", "實際比分", "結果"])

def load_teachers():
    if os.path.exists(TEACHER_FILE):
        return pd.read_csv(TEACHER_FILE)['name'].tolist()
    return ["MLB"] # 預設初始老師

def save_teachers(teacher_list):
    pd.DataFrame({'name': teacher_list}).to_csv(TEACHER_FILE, index=False)

# --- 2. 初始化 Session State ---
if 'matches' not in st.session_state:
    st.session_state.matches = load_data()
if 'teachers' not in st.session_state:
    st.session_state.teachers = load_teachers()
if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = st.session_state.teachers[0]

# --- 3. 側邊欄：老師管理 (新增/刪除) ---
with st.sidebar:
    st.header("👨‍🏫 老師管理系統")
    
    # 新增老師
    new_t = st.text_input("輸入新老師姓名")
    if st.button("新增老師"):
        if new_t and new_t not in st.session_state.teachers:
            st.session_state.teachers.append(new_t)
            save_teachers(st.session_state.teachers)
            st.success(f"已新增: {new_t}")
            st.rerun()

    st.divider()
    
    # 刪除老師
    del_t = st.selectbox("選擇要刪除的老師", st.session_state.teachers)
    if st.button("❌ 刪除選中老師"):
        if len(st.session_state.teachers) > 1:
            st.session_state.teachers.remove(del_t)
            save_teachers(st.session_state.teachers)
            # 如果刪除的是當前選中的，切換回第一個
            if st.session_state.current_teacher == del_t:
                st.session_state.current_teacher = st.session_state.teachers[0]
            st.warning(f"已刪除: {del_t}")
            st.rerun()
        else:
            st.error("至少需保留一名老師")

# --- 4. 主頁面 UI ---
st.title("🏆 賽事預測統計看板")

# 動態產生老師按鈕 (對應 image_994094.png 的上方佈局)
# 使用 columns 讓按鈕橫向排列
cols = st.columns(len(st.session_state.teachers) + 1)
with cols[0]:
    if st.button("➕ 資料輸入", type="primary"):
        st.session_state.show_form = True

for i, t in enumerate(st.session_state.teachers):
    with cols[i+1]:
        # 當前選中的老師按鈕顏色不同
        btn_type = "primary" if st.session_state.current_teacher == t else "secondary"
        if st.button(t, key=f"btn_{t}"):
            st.session_state.current_teacher = t
            st.rerun()

st.divider()

# --- 5. 數據列表與勝率計算 ---
cur_t = st.session_state.current_teacher
df_display = st.session_state.matches[st.session_state.matches["老師"] == cur_t]

# 計算勝率
total_count = len(df_display)
win_count = len(df_display[df_display["結果"] == "✅"])
win_rate = (win_count / total_count * 100) if total_count > 0 else 0

# 顯示統計資訊
c1, c2, c3 = st.columns(3)
c1.metric("預測場數", f"{total_count} 場")
c2.metric("命中場數", f"{win_count} 場")
c3.metric("目前勝率", f"{win_rate:.1f}%")

st.subheader(f"📍 {cur_t} 的歷史預測記錄")

if df_display.empty:
    st.info("尚無記錄，請點擊左上方按鈕輸入資料。")
else:
    # 呈現樣式優化 (類似圖片清單)
    for _, row in df_display.sort_index(ascending=False).iterrows():
        with st.container():
            r1, r2, r3, r4, r5 = st.columns([1, 2, 1, 1, 0.5])
            r1.write(row["日期"])
            r2.markdown(f"**{row['對戰組合']}**")
            r3.write(row["預測內容"])
            r4.info(row["實際比分"])
            r5.write("✅" if row["結果"] == "✅" else "❌")
            st.divider()

# --- 6. 彈出輸入表單 ---
if st.session_state.get('show_form'):
    with st.expander("📝 錄入新賽事資料", expanded=True):
        with st.form("input_form"):
            f_t = st.selectbox("負責老師", st.session_state.teachers, 
                               index=st.session_state.teachers.index(cur_t))
            f_date = st.date_input("日期")
            f_match = st.text_input("對戰組合 (例: 勇士 vs 湖人)")
            f_pred = st.text_input("預測項目 (例: 湖人勝 / 大分)")
            f_score = st.text_input("最終比分 (例: 110:115)")
            f_res = st.radio("結果判斷", ["正確 ✅", "錯誤 ❌"], horizontal=True)
            
            if st.form_submit_button("確認存檔"):
                new_row = {
                    "老師": f_t,
                    "日期": f_date.strftime("%Y-%m-%d"),
                    "對戰組合": f_match,
                    "預測內容": f_pred,
                    "實際比分": f_score,
                    "結果": "✅" if "正確" in f_res else "❌"
                }
                st.session_state.matches = pd.concat([st.session_state.matches, pd.DataFrame([new_row])], ignore_index=True)
                st.session_state.matches.to_excel(DATA_FILE, index=False)
                st.session_state.show_form = False
                st.success("資料已寫入 Excel 並更新！")
                st.rerun()