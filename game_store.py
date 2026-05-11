import streamlit as st
import pandas as pd
import requests
import time

# 1. 頁面基本設定
st.set_page_config(page_title="Sports Dashboard", layout="wide")

# --- 隱藏 Manage app 與頂部工具列 CSS ---
st.markdown("""
    <style>
    header {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    footer {display: none !important;}
    .stAppDeployButton {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    .st-emotion-cache-zq5wms {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 賽事雲端統計看板")

# 2. 讀取資料並建立「記憶選單」
try:
    SHEET_URL = st.secrets["SHEET_URL"]
    GAS_URL = st.secrets["GAS_URL"]
    
    if "/edit" in SHEET_URL:
        CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
    else:
        CSV_URL = SHEET_URL
        
    df = pd.read_csv(CSV_URL)
    
    # --- 動態記憶邏輯：從歷史資料提取球隊與球員 ---
    team_options = [""]
    player_options = [""]
    
    if not df.empty:
        df = df.dropna(subset=["老師"])
        df["老師"] = df["老師"].astype(str)
        df["注單編號"] = df["注單編號"].fillna("無編號").astype(str)
        
        # 1. 自動記憶球隊
        all_matches = df["對戰組合"].dropna().astype(str).tolist()
        u_teams = set()
        for m in all_matches:
            if " vs " in m:
                u_teams.update([t.strip() for t in m.split(" vs ")])
            else:
                u_teams.add(m.strip())
        team_options += sorted(list(u_teams))
        
        # 2. 自動記憶球員 (抓取『特定球員』欄位)
        if "特定球員" in df.columns:
            u_players = set(df["特定球員"].dropna().astype(str).tolist())
            if "nan" in u_players: u_players.remove("nan")
            player_options += sorted([p for p in u_players if p.strip() != ""])
        
        # 3. 數值型態轉換
        df["下注總額"] = pd.to_numeric(df.get("下注總額", 0), errors='coerce').fillna(0)
        df["領回金額"] = pd.to_numeric(df.get("領回金額", 0), errors='coerce').fillna(0)
        
        all_teachers = sorted(df["老師"].unique().tolist())
    else:
        all_teachers = ["MLB"]
except Exception as e:
    st.error(f"❌ 讀取失敗，請確認 Secrets 或試算表欄位。")
    st.stop()

if 'current_teacher' not in st.session_state:
    st.session_state.current_teacher = all_teachers[0]

# --- 3. UI 錄入表單 (含球隊/球員/金額) ---
with st.expander("📝 錄入新注單 (支援自動記憶)", expanded=False):
    num_m = st.number_input("這張注單包含幾場比賽？", 1, 10, 1)
    
    with st.form("multi_match_form", clear_on_submit=True):
        c_t, c_d = st.columns(2)
        f_t = c_t.text_input("老師姓名", value=st.session_state.current_teacher)
        f_date = c_d.date_input("日期")
        
        c_cost, c_ret = st.columns(2)
        f_cost = c_cost.number_input("下注總額 (成本)", min_value=0, value=0)
        f_ret = c_ret.number_input("領回總額 (回收)", min_value=0, value=0)
        
        m_list = []
        for i in range(int(num_m)):
            st.markdown(f"--- **📍 賽事 {i+1}** ---")
            
            # 主客隊選擇
            st.write("對戰組合 (主隊 vs 客隊)")
            col_t1, col_vs, col_t2 = st.columns([4, 1, 4])
            with col_t1:
                t1_s = st.selectbox(f"選取主隊", options=team_options, key=f"t1s_{i}")
                t1_n = st.text_input(f"手輸新主隊", key=f"t1n_{i}")
                final_t1 = t1_n if t1_n else t1_s
            with col_vs:
                st.markdown("<h3 style='text-align:center; padding-top:25px;'>VS</h3>", unsafe_allow_html=True)
            with col_t2:
                t2_s = st.selectbox(f"選取客隊", options=team_options, key=f"t2s_{i}")
                t2_n = st.text_input(f"手輸新客隊", key=f"t2n_{i}")
                final_t2 = t2_n if t2_n else t2_s
            
            # 球員選擇
            st.write("特定球員 (選填)")
            c_p1, c_p2 = st.columns(2)
            p_s = c_p1.selectbox(f"從歷史選取球員", options=player_options, key=f"ps_{i}")
            p_n = c_p2.text_input(f"手輸新球員名字", key=f"pn_{i}")
            final_p = p_n if p_n else p_s

            # 預測內容與結果
            c1, c2, c3 = st.columns([4, 4, 2])
            p_v = c1.text_input("預測內容", key=f"p_{i}", placeholder="例: 得分>28.5")
            s_v = c2.text_input("實際數據", key=f"s_{i}", placeholder="例: 32")
            r_v = c3.selectbox("結果", ["正確", "錯誤"], key=f"r_{i}")
            
            m_list.append({
                "match": f"{final_t1} vs {final_t2}",
                "player": final_p,
                "pred": p_v, "score": s_v, "result": r_v
            })
        
        if st.form_submit_button("🚀 確認提交整張注單"):
            if not f_t or not final_t1 or not final_t2:
                st.error("請確保老師姓名與球隊已填寫")
            else:
                s_id = f"SLIP-{int(time.time())}"
                payload = {
                    "teacher": f_t, "date": f_date.strftime("%Y-%m-%d"), 
                    "slipId": s_id, "matches": m_list,
                    "cost": f_cost, "returnVal": f_ret
                }
                try:
                    res = requests.post(GAS_URL, json=payload, timeout=10)
                    if res.status_code == 200:
                        st.success("✅ 存檔成功！系統已更新記憶選單。")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 連線異常：{e}")

st.divider()

# --- 4. 老師切換按鈕 ---
btn_cols = st.columns(len(all_teachers))
for i, t in enumerate(all_teachers):
    with btn_cols[i]:
        if st.button(t, key=f"btn_{t}", use_container_width=True, 
                     type="primary" if st.session_state.current_teacher == t else "secondary"):
            st.session_state.current_teacher = t
            st.rerun()

# --- 5. 數據統計與收合顯示 ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # ROI 損益統計 (以注單編號分組，取第一筆金額)
    slip_money = df_display.groupby("注單編號").first()
    t_cost = slip_money["下注總額"].sum()
    t_ret = slip_money["領回金額"].sum()
    profit = t_ret - t_cost
    roi = (profit / t_cost * 100) if t_cost > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("單場勝率", f"{(len(df_display[df_display['結果']=='正確'])/len(df_display)*100):.1f}%")
    c2.metric("累積損益", f"${profit:,.0f}", f"投資額 ${t_cost:,.0f}")
    c3.metric("總投報率 ROI", f"{roi:.1f}%")

    st.subheader(f"📍 {cur_t} 歷史明細 (按注單收合)")
    unique_slips = [s for s in df_display["注單編號"].unique() if str(s) != "nan"][::-1]
    
    for sid in unique_slips:
        slip_data = df_display[df_display["注單編號"] == sid]
        if slip_data.empty: continue
        
        is_win = all(slip_data["結果"] == "正確")
        s_cost = slip_data["下注總額"].iloc[0]
        s_ret = slip_data["領回金額"].iloc[0]
        date_str = slip_data["日期"].iloc[0]
        
        status_icon = "💰" if s_ret > s_cost else ("❌" if s_ret < s_cost else "➖")
        
        with st.expander(f"{status} 日期：{slip_data['日期'].iloc[0]} | 成本：{s_cost} | 回收：{s_ret}"):
            # 這裡加入安全性檢查，確保欄位存在才顯示
            target_cols = ["對戰組合", "特定球員", "預測內容", "實際比分", "結果"]
            available_cols = [c for c in target_cols if c in slip_data.columns]
            
            if available_cols:
                st.table(slip_data[available_cols])
            else:
                st.write("此筆資料格式較舊，無法完整顯示表格。")
            
            # 刪除功能
            c_space, c_del = st.columns([5, 1])
            with c_del:
                with st.popover("🗑️ 刪除", use_container_width=True):
                    st.warning("確定刪除此注單？")
                    if st.button("確認", key=f"del_{sid}", type="primary"):
                        try:
                            requests.post(GAS_URL, json={"action": "delete", "slipId": sid}, timeout=10)
                            st.rerun()
                        except:
                            st.error("失敗")
else:
    st.info("尚無數據紀錄")
