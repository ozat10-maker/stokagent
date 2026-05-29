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

# הגדרת מפתח ה-API והסיכון בראש הדף
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
# --- רכיב אוניברסלי מוגן: משיכת גרף ישירה ומנוקת Regex לחלוטין ---
def render_universal_stock_analysis(ticker_str, unique_key_prefix=""):
    """מנקה לחלוטין את הקלט ומושכת נתוני מניה רק בלחיצה מפורשת."""
    if not ticker_str:
        return
    
    # השארת אותיות באנגלית בלבד (חיתוך עד 5 תווים למניעת שגיאות טקסט עודף)
    clean_ticker = re.sub(r'[^a-zA-Z]', '', str(ticker_str)).strip().upper()[:5]
    
    if not clean_ticker:
        st.warning("אנא הזן סימול מנייה תקין באנגלית לצורך בדיקה.")
        return
        
    st.markdown(f"##### 📈 אזור בדיקה ייעודי עבור הסימול המנוקה: **{clean_ticker}**")
    
    if st.button(f"📊 לחץ להצגת גרף 6M ומדדים עבור {clean_ticker}", key=f"btn_chart_{clean_ticker}_{unique_key_prefix}"):
        with st.spinner(f"פונה לשרתי הבורסה למשוך נתונים עבור {clean_ticker}..."):
            try:
                stock = yf.Ticker(clean_ticker)
                hist = stock.history(period="6m")
                
                if hist.empty:
                    st.error(f"❌ לא ניתן היה למשוך נתוני מחיר עבור '{clean_ticker}'. ודא שהסימול נכון (למשל: NVDA, XOM) ונסה שנית.")
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
                price_6m_ago = hist['Close'].iloc[0] if len(hist) > 0 else current_price
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
            clean_t = re.sub(r'[^a-zA-Z]', '', str(ticker)).strip().upper()[:5]
            stock = yf.Ticker(clean_t)
            hist = stock.history(period="1y")
            if hist.empty: continue
            current_price = hist['Close'].iloc[-1]
            price_6m_ago = hist['Close'].iloc[-126] if len(hist) >= 126 else hist['Close'].iloc[0]
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
# רכיב א': רדאר אירועים גלובליים (גרסת הדוח הישיר והחסין)
# =====================================================================
st.header("🛰️ רדאר אירועים וטרנדים גלובליים (Macro Catalyst Radar)")
st.markdown("סריקה אקטיבית המפיקה דוח אבחנות ומודיעין מאקרו לאיתור מניות פוטנציאליות ברחבי העולם.")

if st.button("🚀 הפעל רדאר לאיתור מניות פוטנציאליות", type="secondary"):
    if not api_key: st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        with st.spinner("הסוכן מבצע מחקר מאקרו עולמי ומגבש המלצות..."):
            prompt_catalyst_stable = """
            You are a global macro-economic asset scanner. Scan the live web using Google Search 
            to find major breaking economic, geopolitical, or subsidy events from the last few weeks.
            Based on these events, identify exactly 3-4 publicly traded stocks that have massive upcoming structural potential.
            
            Generate a comprehensive, beautifully formatted research analysis report in Hebrew.
            You must structure the report under these specific headers:
            
            ### 🌍 אירועי המאקרו והקטליזטורים המשמעותיים ביותר שנמצאו בשטח
            (Detail what happened globally - subsidies, trade constraints, energy spikes).
            
            ### 🎯 מניות בעלות פוטנציאל מבני מומלץ (Structural Picks)
            For each stock you recommend, explicitly state:
            1. The clean Ticker Symbol in English (e.g. XOM, NVDA, MP, INTC).
            2. Sector and brief reasoning on why it will capture the macro momentum.
            3. Risk Level (Low, Medium, High).
            
            ### ⚠️ סיכונים וצווארי בקבוק בשוק הגלובלי
            
            Respond strictly and entirely in Hebrew.
            """
            max_retries = 3
            full_text = ""
            client = genai.Client(api_key=api_key)
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash', contents=prompt_catalyst_stable,
                        config=types.GenerateContentConfig(temperature=0.3, tools=[types.Tool(google_search=types.GoogleSearch())])
                    )
                    full_text = response.text
                    break
                except:
                    time.sleep(4)

            if full_text:
                st.session_state.radar_full_text = full_text
            else:
                st.error("❌ השרת עמוס מדי כעת ולא הצליח להשלים את החיפוש. אנא נסה שנית בעוד חצי דקה.")
# הצגת דוח הרדאר הטקסטואלי החסין
if st.session_state.radar_full_text:
    st.success("📋 דוח מודיעין מאקרו ואיתור הזדמנויות גלובלי:")
    st.markdown(st.session_state.radar_full_text)
    
    # אזור משני לחקירה עצמאית ומאובטחת של מנייה מתוך הדוח
    st.write("---")
    st.markdown("#### 🔍 חקירה עצמאית של מנייה שאותרה בדוח")
    radar_input = st.text_input("הקלד ידנית את סימול המנייה שברצונך לחקור מהדוח (למשל: NVDA, XOM, MP):", "XOM", key="radar_txt_in").strip().upper()
    
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
