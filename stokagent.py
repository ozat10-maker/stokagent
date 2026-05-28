import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io

def fetch_live_market_dashboard():
    indices = {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "תל אביב 35": "^TA35.TA"}
    dashboard = {}
    for name, ticker in indices.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                pct_change = ((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                dashboard[name] = (current_price, pct_change)
            else:
                dashboard[name] = (hist['Close'].iloc[-1], 0.0)
        except:
            dashboard[name] = (None, None)
    return dashboard

def fetch_fx_rates():
    fx_tickers = {"USD/ILS (דולר)": "ILS=X", "EUR/ILS (יורו)": "EURILS=X"}
    fx_rates = {}
    for name, ticker in fx_tickers.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if not hist.empty:
                current_rate = hist['Close'].iloc[-1]
                if current_rate < 1.0: current_rate = 1 / current_rate
                change = current_rate - (hist['Close'].iloc[-2] if len(hist) >= 2 else current_rate)
                fx_rates[name] = (current_rate, change)
        except:
            fx_rates[name] = (None, None)
    return fx_rates

def scan_sector_fundamentals(tickers):
    """סורק ומחשב מדדים יבשים לכל מניות הענף לצורך השוואה מהירה"""
    scan_results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            # חישוב מרחק מהממוצע הנע 200 ימי מסחר (אינדיקטור טכני)
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else hist['Close'].mean()
            current_price = hist['Close'].iloc[-1]
            dist_ma200 = ((current_price - ma200) / ma200) * 100
            
            scan_results.append({
                "מנייה": ticker,
                "מחיר נוכחי ($)": round(current_price, 2),
                "מכפיל רווח P/E": info.get("trailingPE", "N/A"),
                "מרווח תפעולי": f"{info.get('operatingMargins', 0) * 100:.1f}%" if info.get('operatingMargins') else "N/A",
                "יחס חוב/הון": info.get("debtToEquity", "N/A"),
                "מרחק מ-MA200": f"{dist_ma200:.1f}%"
            })
        except:
            continue
    return pd.DataFrame(scan_results)
import streamlit as st
from google import genai
from google.genai import types
from utils import fetch_live_market_dashboard, fetch_fx_rates, scan_sector_fundamentals

st.set_page_config(page_title="Macro AI Screener", layout="wide")
st.title("🎯 Macro AI Alpha Core - סורק מניות חכם")

# 🌐 דאשבורד מאקרו ומט"ח עליון (מהיר וחינמי)
live_indices = fetch_live_market_dashboard()
live_fx = fetch_fx_rates()
idx_cols = st.columns(len(live_indices) + len(live_fx))

for i, (name, data) in enumerate(live_indices.items()):
    if data[0]: idx_cols[i].metric(label=name, value=f"{data[0]:,.1f}", delta=f"{data[1]:.1f}%")
for i, (name, data) in enumerate(live_fx.items()):
    if data[0]: idx_cols[len(live_indices) + i].metric(label=name, value=f"{data[0]:.3f}", delta=f"{data[1]:.3f}")

st.write("---")

# הגדרות סקטורים
SECTOR_MAP = {
    "Technology & AI Semiconductors": ["NVDA", "TSM", "AMD", "ASML"],
    "Energy & Global Infrastructure": ["XOM", "CVX", "SHEL", "NextEra"],
    "Commodities & Global Shipping": ["VALE", "CAT", "ZIM", "BHP"],
    "Biotech & Healthcare": ["LLY", "NVO", "PFE", "MRK"]
}

# תפריט צד למפתח API
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("הזן מפתח API של Gemini:", type="password")
risk_profile = st.sidebar.selectbox("פרופיל סיכון יעד:", ["Conservative", "Moderate", "Aggressive"])

# 1. בחירת ענף להשקעה
selected_sector = st.selectbox("בחר ענף שבו תרצה לאתר השקעות ופוטנציאל:", list(SECTOR_MAP.keys()))

if st.button("🔍 הפעל סורק ענפי מהיר", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        with st.spinner("מריץ סורק נתונים פונדמנטלי וטכני מקומי..."):
            tickers = SECTOR_MAP[selected_sector]
            df_sector = scan_sector_fundamentals(tickers)
            
            st.subheader(f"📊 ממצאי סינון וסריקה עבור ענף: {selected_sector}")
            st.dataframe(df_sector, use_container_width=True, hide_index=True)
            
            # קריאת AI מהירה ותמציתית בלבד (ללא חיפוש אינטרנט שמכביד על האפליקציה)
            st.write("")
            st.subheader("💡 אבחנת מנוע מהירה (איתור פוטנציאל)")
            
            prompt_quick = f"""
            You are a stock screener assistant. Look at this processed data table for the sector {selected_sector}:
            {df_sector.to_string()}
            Based strictly on these metrics (P/E, Margins, Debt, MA200 distance) and risk profile '{risk_profile}', identify WHICH stock has the highest investment potential right now.
            Provide a short, 3-sentence summary in Hebrew explaining why, and state a clear top pick.
            Respond strictly in Hebrew.
            """
            
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_quick)
                st.info(response.text)
                # שמירה ב-Session State כדי לאפשר העמקה
                st.session_state.active_tickers = tickers
            except Exception as e:
                st.error(f"שגיאה בהפקת האבחנה המהירה: {str(e)}")

# 2. חלק אופציונלי: הפקת דוח מלא לפי דרישה בלבד
if "active_tickers" in st.session_state:
    st.write("---")
    st.markdown("### 🚀 העמקה ומודיעין עמוק (לפי דרישה בלבד)")
    chosen_ticker = st.selectbox("בחר מנייה ספציפית מהסורק כדי להפיק עליה דוח מלא מהאינטרנט:", st.session_state.active_tickers)
    
    if st.button("🌐 הפק דוח מקיף ומלא (Bloomberg & TradingView)", type="secondary"):
        with st.spinner(f"סוכן הרשת יוצא כעת ל-Bloomberg ו-TradingView לחקור את {chosen_ticker}..."):
            prompt_deep = f"""
            Generate a full, comprehensive Alpha Convergence Report for the stock {chosen_ticker} (Risk: {risk_profile}).
            Use Google Search tool to prioritize insights from site:bloomberg.com and site:tradingview.com.
            Cover: Executive Macro summary, Technical consensus from TradingView, and Geopolitical supply chain indicators from Bloomberg.
            Provide a final Alpha Convergence Score (0-100).
            Respond strictly and entirely in Hebrew.
            """
            try:
                client = genai.Client(api_key=api_key)
                deep_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_deep,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                st.write("---")
                st.markdown(deep_response.text)
            except Exception as e:
                st.error(f"שגיאה בהפקת הדוח המלא: {str(e)}")
