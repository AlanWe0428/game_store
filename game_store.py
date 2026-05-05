import streamlit as st
import pandas as pd
import requests

st.title("🏆 賽事雲端統計看板")

# 1. 讀取資料 (使用 Secrets 裡的 SHEET_URL)
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    CSV_URL = SHEET_URL.replace("/edit?usp=sharing", "/export?format=csv")
    df = pd.read_csv(CSV_URL)
    # 自動偵測老師
    teachers = df["老師"].dropna().unique().tolist() if not df.empty else ["MLB"]
except:
    st.error("請檢查 Secrets 設定")
    st.stop()

# --- 2. UI 填單表單 ---
with st.expander("📝 直接錄入新賽事", expanded=False):
    with st.form("ui_form", clear_on_submit=True):
        f_t = st.text_input("老師姓名 (輸入新名字會自動新增按鈕)")
        f_date = st.date_input("日期")
        f_match = st.text_input("對戰組合")
        f_pred = st.text_input("預測內容")
        f_score = st.text_input("實際比分")
        f_res = st.radio("結果", ["✅", "❌"], horizontal=True)
        
        if st.form_submit_button("確認存檔"):
            # 這裡貼上您剛才在 Google Apps Script 得到的 URL
            # 建議也存放在 Secrets 裡比較安全
            GAS_URL = st.secrets["GAS_URL"] 
            
            payload = {
                "teacher": f_t,
                "date": f_date.strftime("%Y-%m-%d"),
                "match": f_match,
                "pred": f_pred,
                "score": f_score,
                "result": f_res
            }
            # 發送資料到 Google，這不會被 API 擋
            response = requests.post(GAS_URL, json=payload)
            if response.status_code == 200:
                st.success(f"成功！老師 {f_t} 的資料已同步。")
                st.rerun()
            else:
                st.error("傳送失敗，請檢查網路。")

# --- 3. 原有的看板顯示邏輯 ---
# ... (顯示按鈕與勝率表格)
