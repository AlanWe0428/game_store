# --- 4. 數據統計邏輯 (防呆加強版) ---
cur_t = st.session_state.current_teacher
df_display = df[df["老師"] == cur_t].copy()

if not df_display.empty:
    # A. 單場統計
    t_m = len(df_display)
    w_m = len(df_display[df_display["結果"] == "正確"])
    # 加入防呆判斷
    win_rate_m = (w_m / t_m * 100) if t_m > 0 else 0
    
    # B. 注單(串關)統計
    # 這裡加入 dropna 確保不會因為空欄位導致計算出錯
    valid_df = df_display.dropna(subset=["注單編號"])
    if not valid_df.empty:
        slip_results = valid_df.groupby("注單編號")["結果"].apply(lambda x: all(x == "正確"))
        t_s = len(slip_results)
        w_s = sum(slip_results)
        # 加入防呆判斷
        win_rate_s = (w_s / t_s * 100) if t_s > 0 else 0
    else:
        t_s, w_s, win_rate_s = 0, 0, 0

    # 顯示指標卡
    m1, m2 = st.columns(2)
    m1.metric(f"🏀 {cur_t} 單場勝率", f"{win_rate_m:.1f}%", f"命中 {w_m} / 總 {t_m} 場")
    m2.metric(f"🎫 {cur_t} 注單勝率", f"{win_rate_s:.1f}%", f"過關 {int(w_s)} / 總 {t_s} 張")

    st.subheader(f"📍 {cur_t} 歷史明細 (最新的在最前)")
    st.table(df_display.iloc[::-1])
else:
    st.info(f"目前尚無 {cur_t} 的數據紀錄，請先透過上方表單錄入賽事。")
