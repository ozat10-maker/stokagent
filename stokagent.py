import yfinance as yf
import pandas as pd

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
            elif not hist.empty:
                dashboard[name] = (hist['Close'].iloc[-1], 0.0)
            else:
                dashboard[name] = (None, None)
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
            else:
                fx_rates[name] = (None, None)
        except:
            fx_rates[name] = (None, None)
    return fx_rates

def fetch_commodity_price(commodity_ticker):
    try:
        stock = yf.Ticker(commodity_ticker)
        hist = stock.history(period="2d")
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            pct_change = ((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100 if len(hist) >= 2 else 0.0
            return f"${current_price:,.2f} ({pct_change:+.1f}%)"
    except:
        pass
    return "N/A"

def scan_sector_fundamentals(tickers):
    scan_results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            if hist.empty: continue
            
            current_price = hist['Close'].iloc[-1]
            
            price_6m_ago = hist['Close'].iloc[-126] if len(hist) >= 126 else hist['Close'].iloc[0]
            return_6m = ((current_price - price_6m_ago) / price_6m_ago) * 100
            
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else hist['Close'].mean()
            dist_ma200 = ((current_price - ma200) / ma200) * 100
            
            avg_volume = hist['Volume'].tail(10).mean()
            
            scan_results.append({
                "מנייה": ticker,
                "מחיר נוכחי ($)": round(current_price, 2),
                "תשואה 6 חודשים": f"{return_6m:.1f}%",
                "מיקום מעל ממוצע 200": f"{dist_ma200:.1f}%",
                "מחזור מסחר ממוצע (10 ימים)": f"{avg_volume:,.0f}"
            })
        except:
            continue
    return pd.DataFrame(scan_results)
import streamlit as st
from google import genai
from google.genai import types

# ייבוא פונקציות מקובץ העזר
from utils import (
    fetch_live_market_dashboard,
    fetch_fx_rates,
    fetch_commodity_price,
    scan_sector_fundamentals
)

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Screener v9", layout="wide")
st.title("🎯 Macro AI Alpha Core - סורק מניות ומקורות אלטרנטיביים")

# --- הצגת לוח מחוונים עליון בזמן אמת ---
live_indices = fetch_live_market_dashboard()
live_fx = fetch_fx_rates()

all_metrics = {**live_indices, **live_fx}
idx_cols = st.columns(len(all_metrics))

for i, (name, data) in enumerate(all_metrics.items()):
    if data and data[0] is not None:
        val, change = data
        if "ILS" in name:
            idx_cols[i].metric(label=name, value=f"{val:.3f}", delta=f"{change:.4f}")
        else:
            idx_cols[i].metric(label=name, value=f"{val:,.1f}", delta=f"{change:.2f}%")
    else:
        idx_cols[i].metric(label=name, value="N/A")

st.write("---")

# הגדרת סקטורים, מניות, וסחורות עוגן מובילות
SECTOR_MAP = {
    "Technology & AI Semiconductors": {
        "tickers": ["NVDA", "TSM", "AMD", "ASML"],
        "commodity_name": "חוזה עתידי על נחושת (Copper Futures)",
        "commodity_ticker": "HG=F"
    },
    "Energy & Global Infrastructure": {
        "tickers": ["XOM", "CVX", "SHEL", "NEXTERA"],
        "commodity_name": "נפט גולמי מסוג Brent (Crude Oil)",
        "commodity_ticker": "BZ=F"
    },
    "Commodities & Global Shipping": {
        "tickers": ["VALE", "CAT", "ZIM", "BHP"],
        "commodity_name": "חוזה עתידי על זהב (Gold Futures)",
        "commodity_ticker": "GC=F"
    },
    "Biotech & Healthcare": {
        "tickers": ["LLY", "NVO", "PFE", "MRK"],
        "commodity_name": "מדד התנודתיות בשווקים (VIX Index)",
        "commodity_ticker": "^VIX"
    }
}

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("הזן מפתח API של Gemini:", type="password")
risk_profile = st.sidebar.selectbox("פרופיל סיכון יעד:", ["Conservative", "Moderate", "Aggressive"])

selected_sector = st.selectbox("בחר ענף שבו תרצה לאתר השקעות ופוטנציאל:", list(SECTOR_MAP.keys()))

# שליפת נתוני סחורת העוגן
current_sector_data = SECTOR_MAP[selected_sector]
commodity_price_str = fetch_commodity_price(current_sector_data["commodity_ticker"])

st.info(f"📊 **עוגן מאקרו סקטוריאלי:** {current_sector_data['commodity_name']} עומד כעת על: **{commodity_price_str}**")

if st.button("🔍 הפעל סורק ענפי מהיר", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        with st.spinner("מריץ סורק נתונים פונדמנטלי וטכני מקומי..."):
            tickers = current_sector_data["tickers"]
            df_sector = scan_sector_fundamentals(tickers)
            
            if df_sector.empty:
                st.error("שגיאה זמנית במשיכת נתוני המניות מ-Yahoo Finance.")
            else:
                st.subheader(f"📊 ממצאי סינון וסריקה עבור ענף: {selected_sector}")
                st.dataframe(df_sector, use_container_width=True, hide_index=True)
                
                st.write("")
                st.subheader("💡 אבחנת מנוע מהירה (איתור פוטנציאל)")
                
                prompt_quick = f"""
                You are a senior hedge fund screener. Look at this processed data table for the sector {selected_sector}:
                {df_sector.to_string()}
                Macro anchor pricing for this specific sector ({current_sector_data['commodity_name']}): {commodity_price_str}
                
                Based strictly on these momentum metrics and the macro anchor status, identify WHICH stock has the highest investment potential right now for a '{risk_profile}' profile.
                Provide a short, 3-sentence summary in Hebrew explaining why, and state a clear top pick.
                Respond strictly in Hebrew.
                """
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_quick)
                    st.info(response.text)
                    st.session_state.active_tickers = tickers
                except Exception as e:
                    st.error(f"שגיאה בהפקת האבחנה המהירה: {str(e)}")

if "active_tickers" in st.session_state:
    st.write("---")
    st.markdown("### 🚀 העמקה ומודיעין עמוק (לפי דרישה בלבד)")
    chosen_ticker = st.selectbox("בחר מנייה ספציפית מהסורק כדי להפיק עליה דוח מלא מהאינטרנט:", st.session_state.active_tickers)
    
    if st.button("🌐 הפק דוח מקיף ומלא (Bloomberg, TradingView & Institutional 13F)", type="secondary"):
        with st.spinner(f"סוכן הרשת יוצא כעת לסרוק מקורות מוסדיים וכלכליים על {chosen_ticker}..."):
            
            prompt_deep = f"""
            Generate a full, comprehensive Alpha Convergence Report for the stock {chosen_ticker} (Risk Profile: {risk_profile}).
            Use Google Search tool to prioritize and extract insights from:
            1. site:bloomberg.com (Institutional macro news, corporate shifts, and supply chain updates).
            2. site:tradingview.com (Technical chart patterns, community sentiment, and indicator consensus).
            3. Institutional Money Flow (Search SEC filings, 13F tracker data, or recent whale activity from Whalewisdom/InsiderSentiment to see if institutional hedge funds are accumulating or distributing {chosen_ticker}).
            
            Structure the report exactly as follows in Hebrew:
            
            ### 📋 תקציר מנהלים ומודיעין מהשטח (Bloomberg & TradingView)
            
            ### 🐋 תזרים כסף חכם ומוסדי (דיווחי SEC & 13F)
            
            ### 📊 מדד התלכדות תובנות (Alpha Convergence Score)
            Calculate a score from 0-100 based on:
            - 30% Weight: Technical trends.
            - 30% Weight: Fundamental health.
            - 40% Weight: Geopolitical & Institutional flows (13F accumulation).
            
            ### 🚀 המלצה אסטרטגית מנומקת
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
