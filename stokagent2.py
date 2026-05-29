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

# =====================================================================
# 🎯 תיקון קריטי: הגדרת מפתח ה-API והסיכון בראש הדף (גלובלי)
# =====================================================================
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
    st.session_state.all_active_tickers = []
if "custom_dashboard_indices" not in st.session_state:
    st.session_state.custom_dashboard_indices = ["S&P 500", "Nasdaq 100", "תל אביב 35"]

# --- שעונים עולמיים ודאשבורד מדדים עליון ---
st.markdown("### 🌐 דאשבורד מאקרו וזמני מסחר עולמיים")

# חישוב זמנים לפי אזורי זמן בעולם
fmt = "%H:%M:%S"
time_il = datetime.now(pytz.timezone("Asia/Jerusalem")).strftime(fmt)
time_us = datetime.now(pytz.timezone("America/New_York")).strftime(fmt)
time_eu = datetime.now(pytz.timezone("Europe/London")).strftime(fmt)
time_jp = datetime.now(pytz.timezone("Asia/Tokyo")).strftime(fmt)

# הצגת השעונים ב-4 עמודות ויזואליות נקיות
clk1, clk2, clk3, clk4 = st.columns(4)
clk1.metric("🇮🇱 שעון ישראל", time_il)
clk2.metric("🇺🇸 שעון ניו יורק (EST)", time_us)
clk3.metric("🇪🇺 שעון לונדון (GMT)", time_eu)
clk4.metric("🇯🇵 שעון טוקיו (JST)", time_jp)

# מיפוי מדדים זמינים לבחירה
ALL_AVAILABLE_INDICES = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^IXIC",
    "Dow Jones": "^DJI",
    "תל אביב 35": "^TA35.TA",
    "תל אביב 125": "^TA125.TA",
    "Euro Stoxx 50": "^STOXX50E",
    "Nikkei 225": "^N225",
    "USD/ILS (דולר)": "ILS=X",
    "EUR/ILS (יורו)": "EURILS=X"
}

# אפשרות להתאמה אישית של הדאשבורד מתפריט הצד
st.sidebar.markdown("---")
selected_dashboard_metrics = st.sidebar.multiselect(
    "בחר מדדים ומטבעות להצגה קבועה עליונה:",
    list(ALL_AVAILABLE_INDICES.keys()),
    default=st.session_state.custom_dashboard_indices
)
st.session_state.custom_dashboard_indices = selected_dashboard_metrics

# פונקציה למשיכת נתוני הדאשבורד המותאם
def fetch_custom_dashboard(selected_metrics):
    dashboard = {}
    for name in selected_metrics:
        ticker = ALL_AVAILABLE_INDICES[name]
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                pct = ((current - prev) / prev) * 100
                dashboard[name] = (current, pct)
            elif not hist.empty:
                dashboard[name] = (hist['Close'].iloc[-1], 0.0)
            else:
                dashboard[name] = (None, None)
        except:
            dashboard[name] = (None, None)
    return dashboard

live_data = fetch_custom_dashboard(st.session_state.custom_dashboard_indices)

if live_data:
    cols = st.columns(len(live_data))
    for i, (name, data) in enumerate(live_data.items()):
        val, change = data
        if val is not None and change is not None:
            if "ILS" in name:
                cols[i].metric(label=name, value=f"{val:.3f} ש\"ח", delta=f"{change:.4f}")
            else:
                cols[i].metric(label=name, value=f"{val:,.1f}", delta=f"{change:.2f}%")
        else:
            cols[i].metric(label=name, value="N/A")

st.write("---")
# --- רכיב אוניברסלי מוגן: פונקציית הפקת גרף ונתונים חסינה הרמטית ---
def render_universal_stock_analysis(ticker_str, unique_key_prefix=""):
    """מנקה לחלוטין את הטיקר מכל תו שאינו אות באנגלית ומציגה גרף ומדדים בלחיצה יזומה."""
    if not ticker_str:
        return
    
    # ניקוי קשיח באמצעות Regex - משאיר רק אותיות נקיות
    clean_ticker = re.sub(r'[^a-zA-Z]', '', str(ticker_str)).strip().upper()
    
    if not clean_ticker:
        st.warning("לא זוהה סימול מנייה תקין באנגלית לצורך הפקת הגרף.")
        return
        
    st.markdown(f"##### 📈 טעינת נתוני שוק עבור הסימול הנקי: **{clean_ticker}**")
    
    if st.button(f"📊 לחץ להצגת גרף 6M ומדדים עבור {clean_ticker}", key=f"btn_chart_{clean_ticker}_{unique_key_prefix}"):
        with st.spinner(f"מושך נתוני מסחר היסטוריים עבור {clean_ticker}..."):
            try:
                stock = yf.Ticker(clean_ticker)
                hist = stock.history(period="6m")
                
                if hist.empty:
                    st.error(f"❌ לא ניתן היה למשוך היסטוריית מחירים עבור הסימול '{clean_ticker}'. ודא שהסימול פעיל בבורסה.")
                    return
                
                # 1. ציור הגרף
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
                
                # 2. אינדיקטורים מהירים
                current_price = hist['Close'].iloc[-1]
                price_6m_ago = hist['Close'].iloc if len(hist) > 0 else current_price
                return_6m = ((current_price - price_6m_ago) / price_6m_ago) * 100
                avg_volume = hist['Volume'].tail(10).mean()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("מחיר אחרון", f"${current_price:,.2f}")
                m2.metric("תשואה חצי שנתית (6M)", f"{return_6m:+.1f}%")
                m3.metric("מחזור מסחר ממוצע", f"{avg_volume:,.0f}")
                
            except Exception as e:
                st.error(f"שגיאה בתהליך התקשורת מול שרתי יאהו: {str(e)}")

# --- סורק פונדמנטלי מקומי לסקטורים ---
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
# רכיב א': רדאר אירועים גלובליים (הפקת טבלה נקייה + העמקה משנית)
# =====================================================================
st.header("🛰️ רדאר אירועים וטרנדים גלובליים (Macro Catalyst Radar)")
st.markdown("סריקה אקטיבית המפיקה טבלת מניות מומלצות קונקרטית, ללא דוחות או גרפים כבושים מראש.")

if st.button("🚀 הפעל רדאר לאיתור מניות פוטנציאליות", type="secondary"):
    if not api_key: 
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        with st.spinner("הסוכן מבצע מחקר מאקרו עולמי ומפיק ממצאים..."):
            prompt_catalyst_stable = """
            You are a global macro-economic asset scanner. Scan the live web using Google Search 
            to find major breaking economic, geopolitical, or subsidy events from the last few weeks.
            Based on these events, identify exactly 4 publicly traded stocks that have massive upcoming structural potential.
            
            Provide your comprehensive research analysis report in Hebrew first.
            
            Then, at the very end of your response, you MUST provide a strict tabular data section wrapped inside an explicit block named [DATA_START] and [DATA_END].
            Inside that section, each line must represent a stock, formatted EXACTLY like this:
            TICKER | CATALYST_SECTOR | REASON_SENTENCE | RISK_LEVEL
            
            Rules for the data section:
            - Provide exactly 4 stock rows.
            - Ticker must be a clean, raw unquoted symbol string (e.g., MP, INTC, NVDA, XOM). Do not add quotes, brackets or extra characters inside tickers.
            - Write CATALYST_SECTOR and REASON_SENTENCE strictly in Hebrew.
            - RISK_LEVEL should be either Low, Medium, or High.
            
            Example of the data section block:
            [DATA_START]
            INTC | טכנולוגיה ושבבים | מענקים ממשלתיים חדשים והרחבת ייצור מקומי. | Medium
            XOM | אנרגיה וגיאופוליטיקה | זינוק מחירי הנפט עקב מתחים במפרץ הפרסי. | Medium
            [DATA_END]
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
                except Exception as exc:
                    if "503" in str(exc) or "429" in str(exc):
                        wait_time = (attempt + 1) * 5
                        st.caption(f"⚠️ שרת גוגל עמוס זמנית. מבצע ניסיון חוזר {attempt + 2}/{max_retries}...")
                        time.sleep(wait_time)
                    else:
                        st.error(f"שגיאת API: {str(exc)}")
                        break

            if full_text:
                st.session_state.radar_full_text = full_text
                try:
                    if "[DATA_START]" in full_text and "[DATA_END]" in full_text:
                        data_part = full_text.split("[DATA_START]")[1].split("[DATA_END]")[0].strip()
                        lines = data_part.split("\n")
                        parsed_rows = []
                        
                        for line in lines:
                            if "|" in line:
                                parts = [p.strip() for p in line.split("|")]
                                if len(parts) >= 4:
                                    t_cleaned = re.sub(r'[^a-zA-Z]', '', str(parts[0])).strip().upper()
                                    if t_cleaned:
                                        parsed_rows.append({
                                            "מנייה": t_cleaned,
                                            "תחום/אירוע מאתר": parts[1],
                                            "פרטים ונימוק": parts[2],
                                            "רמת סיכון": parts[3]
                                        })
                        
                        if parsed_rows:
                            st.session_state.radar_stocks_df = pd.DataFrame(parsed_rows)
                        else:
                            st.error("לא ניתן היה לפענח את שורות הנתונים. נסה להריץ שוב.")
                    else:
                        st.error("מבנה הדוח התקבל ללא בלוק הנתונים הייעודי. אנא נסה שוב.")
                except Exception as parse_err:
                    st.error(f"שגיאה בעיבוד הטקסט: {str(parse_err)}")
            else:
                st.error("❌ השרת עמוס מדי כעת ולא הצליח להשלים את החיפוש.")
# הצגת ממצאי הרדאר במידה וקיימים בזיכרון
if st.session_state.radar_stocks_df is not None and not st.session_state.radar_stocks_df.empty:
    st.success("✅ אותרו המניות הבאות בעלות פוטנציאל מבני מתוך ניתוח המאקרו העולמי:")
    st.dataframe(st.session_state.radar_stocks_df, use_container_width=True, hide_index=True)
    
    with st.expander("🌐 לחץ כאן כדי לצפות בדוח מחקר המאקרו המלא שלפיו הופקו המסקנות"):
        st.markdown(st.session_state.radar_full_text.split("[DATA_START]")[0])
    
    tickers_list = st.session_state.radar_stocks_df["מנייה"].tolist()
    
    st.write("")
    st.markdown("##### 🔍 חקירת מנייה מהרדאר")
    radar_choice_input = st.text_input("הקלד את סימול המנייה שברצונך לחקור מהטבלה (למשל: XOM, MP, NVDA):", value=str(tickers_list[0]) if tickers_list else "XOM").strip().upper()
    
    render_universal_stock_analysis(radar_choice_input, unique_key_prefix="radar")
    
    col_r1, col_r2 = st.columns(2)
    if col_r1.button("🌐 הפק דוח אנליסט עמוק ספציפי (Bloomberg & TradingView)", type="primary"):
        with st.spinner(f"סוכן הרשת חוקר כעת לעומק את {radar_choice_input}..."):
            prompt_deep = f"Generate a full Alpha Convergence Report for {radar_choice_input} (Risk: {risk_profile}). Use Google Search tool to extract insights from site:bloomberg.com and site:tradingview.com. Respond strictly and entirely in Hebrew."
            try:
                client = genai.Client(api_key=api_key)
                deep_res = client.models.generate_content(
                    model='gemini-2.5-flash', contents=prompt_deep,
                    config=types.GenerateContentConfig(temperature=0.3, tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.markdown("---")
                st.markdown(deep_res.text)
            except Exception as e: st.error(f"שגיאה בהפקת הדוח: {str(e)}")
            
    if col_r2.button(f"📌 הוסף את {radar_choice_input} לרשימת המעקב האישית", key="add_radar_watch"):
        if radar_choice_input not in st.session_state.watchlist:
            st.session_state.watchlist.append(radar_choice_input)
            st.success(f"המנייה {radar_choice_input} נוספה בהצלחה למעקב!")

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
        if df_sector.empty: 
            st.error("שגיאה זמנית במשיכת נתוני המניות.")
        else:
            st.subheader(f"📊 ממצאי סינון וסריקה עבור ענף: {selected_sector}")
            st.dataframe(df_sector, use_container_width=True, hide_index=True)
            st.session_state.all_active_tickers = tickers

if st.session_state.all_active_tickers:
    st.write("")
    st.markdown("##### 🔍 חקירת מנייה מהסורק")
    chosen_ticker_input = st.text_input("הקלד את סימול המנייה שברצונך לחקור מהסורק (למשל: NVDA, TSM):", value=str(st.session_state.all_active_tickers[0])).strip().upper()
    
    render_universal_stock_analysis(chosen_ticker_input, unique_key_prefix="scanner")
    
    col_s1, col_s2 = st.columns(2)
    if col_s1.button("🌐 הפק דוח עמוק מבוסס רשת (סוכן מלא)", key="deep_sec"):
        with st.spinner(f"סוכן הרשת יוצא לחקור את {chosen_ticker_input}..."):
            prompt_deep = f"Generate a full Alpha Convergence Report for {chosen_ticker_input} (Risk: {risk_profile}). Use Google Search tool to extract insights from site:bloomberg.com, site:tradingview.com, and institutional money flow/13F filings. Respond strictly and entirely in Hebrew."
            try:
                client = genai.Client(api_key=api_key)
                deep_response = client.models.generate_content(
                    model='gemini-2.5-flash', contents=prompt_deep,
                    config=types.GenerateContentConfig(temperature=0.3, tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.markdown("---")
                st.markdown(deep_response.text)
            except Exception as e: st.error(f"שגיאה בהפקת הדוח המלא: {str(e)}")
            
    if col_s2.button(f"📌 הוסף את {chosen_ticker_input} למחברת מעקב ארוך טווח", key="add_scan_watch"):
        if chosen_ticker_input not in st.session_state.watchlist:
            st.session_state.watchlist.append(chosen_ticker_input)
            st.success(f"המנייה {chosen_ticker_input} נוספה למעקב אשרור ביצועים!")

# =====================================================================
# רכיב ג': מחברת מעקב ואשרור ביצועים ארוכי טווח
# =====================================================================
st.write("---")
st.header("📌 מחברת מעקב ואשרור ביצועים (Long-Term Track Record)")
st.markdown("מניות שסימנת לאורך השימוש במערכת כדי לעקוב אחריהן לאורך זמן ולאשרר את דיוק המנוע.")

if not st.session_state.watchlist:
    st.info("רשימת המעקב שלך ריקה כרגע. הוסף מניות מתוך הרדאר או הסורק כדי להתחיל לאשרר ביצועים.")
else:
    st.success(f"מעקב פעיל אחר {len(st.session_state.watchlist)} מניות שנבחרו על ידך:")
    
    watchlist_df = scan_sector_fundamentals(st.session_state.watchlist)
    st.dataframe(watchlist_df, use_container_width=True, hide_index=True)
    
    watchlist_choice_input = st.text_input("הקלד את סימול המנייה מרשימת המעקב לצפייה בגרף 6M עדכני:", value=str(st.session_state.watchlist[0])).strip().upper()
    
    render_universal_stock_analysis(watchlist_choice_input, unique_key_prefix="watchlist")
    
    if st.button("🗑️ נקה את כל רשימת המעקב"):
        st.session_state.watchlist = []
        st.rerun()
