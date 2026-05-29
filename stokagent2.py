import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import time
import re
from datetime import datetime
import pytz
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת
st.set_page_config(page_title="Macro AI Terminal", layout="wide")

st.sidebar.header("⚙️ הגדרות מערכת וסיכון")

if "GEMINI_API_KEY" in st.secrets: 
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("מפתח API נטען אוטומטית ✅")
else: 
    api_key = st.sidebar.text_input("הזן מפתח API של Gemini:", type="password", key="global_api_key")

risk_profile = st.sidebar.selectbox("פרופיל סיכון יעד:", ["Conservative", "Moderate", "Aggressive"])

# --- אתחול משתני State גלובליים לשמירת נתונים ---
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "radar_stocks_df" not in st.session_state:
    st.session_state.radar_stocks_df = None
if "radar_full_text" not in st.session_state:
    st.session_state.radar_full_text = ""
if "all_active_tickers" not in st.session_state:
    st.session_state.all_active_tickers = ["NVDA", "TSM", "AMD", "ASML"]

# --- שעונים עולמיים ויזואליים בלבד לחסכון ב-Rate Limit ---
st.markdown("### 🌐 זמני מסחר עולמיים")

fmt = "%H:%M:%S"
time_il = datetime.now(pytz.timezone("Asia/Jerusalem")).strftime(fmt)
time_us = datetime.now(pytz.timezone("America/New_York")).strftime(fmt)
time_eu = datetime.now(pytz.timezone("Europe/London")).strftime(fmt)
time_jp = datetime.now(pytz.timezone("Asia/Tokyo")).strftime(fmt)

clk1, clk2, clk3, clk4 = st.columns(4)
clk1.metric("🇮🇱 שעון ישראל", time_il)
clk2.metric("🇺🇸 שעון ניו יורק (EST)", time_us)
clk3.metric("🇪🇺 שעון לונדון (GMT)", time_eu)
clk4.metric("🇯🇵 שעון טוקיו (JST)", time_jp)

st.write("---")
# --- רכיב אוניברסלי מוגן: משיכת גרף ישירה ומנוקת לחלוטין ---
def render_universal_stock_analysis(ticker_str, unique_key_prefix=""):
    """מנקה לחלוטין את הקלט ומושכת נתוני מניה רק בלחיצה מפורשת."""
    if not ticker_str:
        return
    
    # השארת אותיות באנגלית בלבד - חסין לחלוטין מרווחים או תווים בעברית
    clean_ticker = re.sub(r'[^a-zA-Z]', '', str(ticker_str)).strip().upper()
    
    if not clean_ticker:
        st.warning("אנא הזן סימול מנייה תקין באנגלית לצורך בדיקה.")
        return
        
    st.markdown(f"##### 📈 אזור בדיקה ייעודי עבור הסימול: **{clean_ticker}**")
    
    if st.button(f"📊 לחץ להצגת גרף 6M ומדדים עבור {clean_ticker}", key=f"btn_chart_{clean_ticker}_{unique_key_prefix}"):
        with st.spinner(f"פונה לשרתי הבורסה למשוך נתונים עבור {clean_ticker}..."):
            try:
                stock = yf.Ticker(clean_ticker)
                hist = stock.history(period="6m")
                
                if hist.empty:
                    st.error(f"❌ לא ניתן היה למשוך נתוני מחיר עבור '{clean_ticker}'. ודא שהסימול נכון (למשל: NVDA, XOM) ושרשת ה-API של Yahoo פנויה.")
                    return
                
                # ציור גרף
                fig, ax = plt.subplots(figsize=(10, 3.0))
                ax.plot(hist.index, hist['Close'], color="#1E3A8A", linewidth=2)
                ax.set_title(f"{clean_ticker} - 6 Month Trend Line")
                ax.grid(True, linestyle="--", alpha=0.5)
                ax.set_ylabel("Price ($)")
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)
                st.image(buf.getvalue(), use_container_width=True)
                plt.close(fig)
                
                # מדדים יבשים
                current_price = hist['Close'].iloc[-1]
                price_6m_ago = hist['Close'].iloc if len(hist) > 0 else current_price
                return_6m = ((current_price - price_6m_ago) / price_6m_ago) * 100
                avg_volume = hist['Volume'].tail(10).mean()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("מחיר אחרון", f"${current_price:,.2f}")
                m2.metric("תשואה 6 חודשים", f"{return_6m:+.1f}%")
                m3.metric("מחזור מסחר ממוצע", f"{avg_volume:,.0f}")
                
            except Exception as e:
                st.error(f"שגיאת תקשורת מול Yahoo Finance: {str(e)}")

def scan_sector_fundamentals(tickers):
    scan_results = []
    for ticker in tickers:
        try:
            clean_t = re.sub(r'[^a-zA-Z]', '', str(ticker)).strip().upper()
            stock = yf.Ticker(clean_t)
            hist = stock.history(period="1y")
            if hist.empty: continue
            current_price = hist['Close'].iloc[-1]
            price_6m_ago = hist['Close'].iloc[-126] if len(hist) >= 126 else hist['Close'].iloc
            return_6m = ((current_price - price_6m_ago) / price_6m_ago) * 100
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else hist['Close'].mean()
            dist_ma200 = ((current_price - ma200) / ma200) * 100
            avg_volume = hist['Volume'].tail(10).mean()
            
            scan_results.append({
                "מנייה": clean_t, "מחיר נוכחי ($)": round(current_price, 2),
                "תשואה 6 חודשים": f"{return_6m:.1f}%", "מיקום מעל ממוצע 200": f"{dist_ma200:.1f}%",
                "מחזור מסחר ממוצע (10 ימים)": f"{avg_volume:,.0f}"
            })
        except: continue
    return pd.DataFrame(scan_results)

# =====================================================================
# רכיב א': רדאר אירועים גלובליים
# =====================================================================
st.header("🛰️ רדאר אירועים וטרנדים גלובליים (Macro Catalyst Radar)")
st.markdown("סריקה אקטיבית המפיקה טבלת מניות מומלצות קונקרטית מתוך חדשות העולם.")

if st.button("🚀 הפעל רדאר לאיתור מניות פוטנציאליות", type="secondary"):
    if not api_key: st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        with st.spinner("הסוכן מבצע מחקר מאקרו עולמי ומסנן ממצאים..."):
            prompt_catalyst_stable = """
            You are a global macro-economic asset scanner. Scan the live web using Google Search 
            to find major breaking economic, geopolitical, or subsidy events from the last few weeks.
            Based on these events, identify exactly 4 publicly traded stocks that have massive upcoming structural potential.
            
            Provide your comprehensive research analysis report in Hebrew first.
            
            Then, at the very end of your response, you MUST list the 4 stocks line by line, formatted EXACTLY like this (use the pipe symbol):
            TICKER | CATALYST_SECTOR | REASON_SENTENCE | RISK_LEVEL
            
            Rules:
            - Provide exactly 4 rows, NO MORE. Do not add numbers like 1., 2., 3. or asterisks **.
            - Ticker must be a clean string symbol (e.g., MP, INTC, NVDA, XOM). Do not add any text, brackets or quotes to the ticker part.
            - Write CATALYST_SECTOR and REASON_SENTENCE strictly in Hebrew.
            - RISK_LEVEL should be either Low, Medium, or High.
            """
            max_retries = 3
            full_text = ""
            client = genai.Client(api_key=api_key)
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash', contents=prompt_catalyst_stable,
                        config=types.GenerateContentConfig(temperature=0.2, tools=[types.Tool(google_search=types.GoogleSearch())])
                    )
                    full_text = response.text
                    break
                except:
                    time.sleep(4)

            if full_text:
                st.session_state.radar_full_text = full_text
                try:
                    lines = full_text.strip().split("\n")
                    parsed_rows = []
                    
                    for line in lines:
                        if "|" in line and "TICKER" not in line and "-------" not in line:
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 4:
                                # 🎯 חילוץ חסין טעויות: ניקוי הטיקר ישירות מאינדקס 0 ללא המרת כל המערך
                                t_raw = str(parts[0]).strip()
                                t_cleaned = re.sub(r'[^a-zA-Z]', '', t_raw).upper()
                                
                                # מניעת כניסת כותרות או שורות פגומות לטבלה
                                if t_cleaned and len(t_cleaned) <= 5:
                                    parsed_rows.append({
                                        "מנייה": t_cleaned,
                                        "תחום/אירוע מאתר": parts[1],
                                        "פרטים ונימוק": parts[2],
                                        "רמת סיכון": parts[3]
                                    })
                                    
                    if parsed_rows:
                        st.session_state.radar_stocks_df = pd.DataFrame(parsed_rows)
                    else:
                        st.error("הסוכן הפיק את המידע אך מבנה השורות דורש הרצה חוזרת. אנא לחץ שוב על כפתור ההפעלה.")
                except Exception as e: 
                    st.error(f"שגיאה בעיבוד בלוק המניות: {str(e)}")
if st.session_state.radar_stocks_df is not None and not st.session_state.radar_stocks_df.empty:
    st.success("✅ אותרו המניות הבאות בעלות פוטנציאל מבני מתוך ניתוח המאקרו העולמי:")
    st.dataframe(st.session_state.radar_stocks_df, use_container_width=True, hide_index=True)
    
    with st.expander("🌐 לחץ כאן כדי לצפות בדוח מחקר המאקרו המלא שלפיו הופקו המסקנות"):
        st.markdown(st.session_state.radar_full_text)
    
    st.write("")
    st.markdown("#### 🔍 חקירה עצמאית ומאובטחת של מנייה מהרדאר")
    radar_input = st.text_input("הקלד ידנית את סימול המנייה שברצונך לחקור מהטבלה (למשל: NVDA, XOM, INTC):", "NVDA", key="radar_txt_in").strip().upper()
    
    render_universal_stock_analysis(radar_input, unique_key_prefix="radar_panel")
    
    col_r1, col_r2 = st.columns(2)
    if col_r1.button("🌐 הפק דוח אנליסט עמוק ספציפי (Bloomberg & TradingView)", type="primary"):
        with st.spinner(f"סוכן הרשת חוקר כעת לעומק את {radar_input}..."):
            prompt_deep = f"Generate a full Alpha Convergence Report for {radar_input} (Risk: {risk_profile}). Use Google Search tool to extract insights from site:bloomberg.com and site:tradingview.com. Respond strictly and entirely in Hebrew."
            try:
                client = genai.Client(api_key=api_key)
                deep_res = client.models.generate_content(
                    model='gemini-2.5-flash', contents=prompt_deep,
                    config=types.GenerateContentConfig(temperature=0.3, tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.markdown("---")
                st.markdown(deep_res.text)
            except Exception as e: st.error(f"שגיאה בהפקת הדוח: {str(e)}")
            
    if col_r2.button(f"📌 הוסף את {radar_input} לרשימת המעקב האישית", key="add_radar_watch"):
        if radar_input not in st.session_state.watchlist:
            st.session_state.watchlist.append(radar_input)
            st.success(f"המנייה {radar_input} נוספה בהצלחה למעקב!")

st.write("---")

# =====================================================================
# רכיב ב': סורק מניות ענפי (Bottom-Up Model)
# =====================================================================
st.header("🔍 סורק מניות ומקורות אלטרנטיביים")
SECTOR_MAP = {
    "Technology & AI Semiconductors": ["NVDA", "TSM", "AMD", "ASML"],
    "Energy & Global Infrastructure": ["XOM", "CVX", "SHEL", "NEXTERA"],
    "Commodities & Global Shipping": ["VALE", "CAT", "ZIM", "BHP"],
    "Biotech & Healthcare": ["LLY", "NVO", "PFE", "MRK"]
}

selected_sector = st.selectbox("בחר ענף שבו תרצה לאתר השקעות ופוטנציאל:", list(SECTOR_MAP.keys()))
tickers = SECTOR_MAP[selected_sector]

if st.button("🔍 הפעל סורק ענפי מהיר", type="primary"):
    with st.spinner("מריץ סורק נתונים פונדמנטלי וטכני מקומי..."):
        df_sector = scan_sector_fundamentals(tickers)
        if df_sector.empty: st.error("שגיאה במשיכת נתוני המניות.")
        else:
            st.subheader(f"📊 ממצאי סינון וסריקה עבור ענף: {selected_sector}")
            st.dataframe(df_sector, use_container_width=True, hide_index=True)
            st.session_state.all_active_tickers = tickers

if st.session_state.all_active_tickers:
    st.write("")
    st.markdown("#### 🔍 חקירה עצמאית של מנייה מהסורק")
    scanner_input = st.text_input("הקלד ידנית את סימול המנייה שברצונך לחקור מהסורק (למשל: NVDA, TSM):", "NVDA", key="scanner_txt_in").strip().upper()
    
    render_universal_stock_analysis(scanner_input, unique_key_prefix="scanner_panel")
    
    col_s1, col_s2 = st.columns(2)
    if col_s1.button("🌐 הפק דוח עמוק מבוסס רשת (סוכן מלא)", key="deep_sec"):
        with st.spinner(f"סוכן הרשת יוצא לחקור את {scanner_input}..."):
            prompt_deep = f"Generate a full Alpha Convergence Report for {scanner_input} (Risk: {risk_profile}). Use Google Search tool to extract insights from site:bloomberg.com, site:tradingview.com, and institutional money flow/13F filings. Respond strictly and entirely in Hebrew."
            try:
                client = genai.Client(api_key=api_key)
                deep_response = client.models.generate_content(
                    model='gemini-2.5-flash', contents=prompt_deep,
                    config=types.GenerateContentConfig(temperature=0.3, tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.markdown("---")
                st.markdown(deep_response.text)
            except Exception as e: st.error(f"שגיאה בהפקת הדוח המלא: {str(e)}")
            
    if col_s2.button(f"📌 הוסף את {scanner_input} למחברת מעקב ארוך טווח", key="add_scan_watch"):
        if scanner_input not in st.session_state.watchlist:
            st.session_state.watchlist.append(scanner_input)
            st.success(f"המנייה {scanner_input} נוספה למעקב!")

# =====================================================================
# רכיב ג': מחברת מעקב ואשרור ביצועים ארוכי טווח
# =====================================================================
st.write("---")
st.header("📌 מחברת מעקב ואשרור ביצועים (Long-Term Track Record)")

if not st.session_state.watchlist:
    st.info("רשימת המעקב שלך ריקה כרגע.")
else:
    st.success(f"מעקב פעיל אחר {len(st.session_state.watchlist)} מניות שנבחרו על ידך:")
    
    try:
        watchlist_df = scan_sector_fundamentals(st.session_state.watchlist)
        st.dataframe(watchlist_df, use_container_width=True, hide_index=True)
    except:
        st.caption("⚠️ שרתי יאהו עמוסים זמנית. ניתן לבדוק גרף מניה בודדת למטה.")
    
    st.write("")
    watchlist_input = st.text_input("הקלד את סימול המנייה מרשימת המעקב לצפייה בגרף:", "NVDA", key="track_txt_in").strip().upper()
    render_universal_stock_analysis(watchlist_input, unique_key_prefix="track_panel")
    
    if st.button("🗑️ נקה את כל רשימת המעקב"):
        st.session_state.watchlist = []
        st.rerun()
