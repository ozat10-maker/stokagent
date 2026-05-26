import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import time
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Alpha Core - מנוע חסין חסימות", layout="wide")

st.title("🎯 Macro AI Alpha Core (v5 - מנוע מנוהל קצב)")
st.subheader("מערכת סוכנים מנוהלת קצב (Rate-Controlled) למניעת חסימות 429 במסלול החינמי")

# תפריט צד: הגדרות מפתח ופרופיל מנהל השקעות
st.sidebar.header("⚙️ הגדרות מערכת וסיכון")

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("מפתח API נטען אוטומטית ✅")
else:
    api_key = st.sidebar.text_input("הזן מפתח API של Gemini:", type="password")

risk_profile = st.sidebar.selectbox("פרופיל סיכון יעד:", ["Conservative", "Moderate", "Aggressive"])

# הגדרת ענפים ומניות מובילות
SECTOR_MAP = {
    "Technology & AI Semiconductors": ["NVDA", "TSM", "AMD", "ASML"],
    "Energy & Global Infrastructure": ["XOM", "CVX", "SHEL", "NextEra"],
    "Commodities & Global Shipping": ["VALE", "CAT", "ZIM", "BHP"],
    "Biotech & Healthcare": ["LLY", "NVO", "PFE", "MRK"]
}

selected_sector = st.selectbox("1. בחר ענף/סקטור לסריקה מקיפה:", list(SECTOR_MAP.keys()))

st.write("---")
st.markdown("### 🔍 התעמקות במנייה ספציפית (אופציונלי)")
use_specific_stock = st.checkbox("אני רוצה לבחור מנייה ספציפית לניתוח בתוך הענף")

target_ticker = None
if use_specific_stock:
    ticker_options = SECTOR_MAP[selected_sector]
    selected_ticker = st.selectbox(f"בחר מנייה מתוך ענף {selected_sector}:", ticker_options)
    custom_ticker = st.text_input("או הזן סימול מנייה אחרת ידנית:").upper().strip()
    target_ticker = custom_ticker if custom_ticker else selected_ticker

def generate_market_chart(tickers):
    try:
        fig, ax = plt.subplots(figsize=(10, 3.5))
        if isinstance(tickers, str):
            tickers = [tickers]
            
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6m")
            if not hist.empty:
                if len(tickers) == 1:
                    ax.plot(hist.index, hist['Close'], label=f"{ticker} Price ($)", color="blue")
                    ax.set_title(f"{ticker} Historical Trend (Last 6 Months)")
                    ax.set_ylabel("Price ($)")
                else:
                    normalized_price = (hist['Close'] / hist['Close'].iloc[0]) * 100
                    ax.plot(hist.index, normalized_price, label=ticker)
                    ax.set_title("Sector Peer Comparison (Last 6 Months Normalized to 100)")
                    ax.set_ylabel("Normalized Performance (%)")
                    
        ax.legend()
        ax.grid(True)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_bytes = buf.getvalue()
        plt.close(fig)
        return img_bytes
    except Exception as e:
        return None

# פונקציה להפעלת סוכן יחיד עם ניהול קצב קפדני
def run_stable_agent(client, prompt, agent_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        except Exception as exc:
            if "429" in str(exc) or "503" in str(exc):
                # אם נחסמנו, נמתין זמן ארוך יותר ונסה שוב
                wait = (attempt + 1) * 10
                time.sleep(wait)
            else:
                return f"סוכן {agent_name} נתקל בשגיאה: {str(exc)}"
    return f"סוכן {agent_name} לא הצליח לקבל מענה בשל מגבלות קצב של ה-API החינמי."

# --- הפעלת מנוע הסוכנים המנוהל ---
st.write("---")
if st.button("🚀 הפעל רשת סוכנים מנוהלת קצב", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        # הצגת הגרף
        st.markdown("#### 📊 שלב 0: הפקת נתוני שוק ויזואליים...")
        tickers_to_chart = target_ticker if target_ticker else SECTOR_MAP[selected_sector]
        img_bytes = generate_market_chart(tickers_to_chart)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
            
        focus_scope = f"המנייה {target_ticker}" if target_ticker else f"הענף {selected_sector}"
        client = genai.Client(api_key=api_key)
        
        # שלב 1: סוכן חדשות
        with st.spinner("📰 סוכן חדשות ומאקרו אוסף נתונים מהרשת..."):
            p1 = f"Search Google for the latest premium financial news and recent market events regarding {focus_scope}. Provide a summary of the top 3 macro highlights. Respond in Hebrew."
            res_news = run_stable_agent(client, p1, "חדשות ומאקרו")
            
        # ⏱️ השהיה קריטית למניעת חסימת קצב בקשות (Rate Limit)
        st.caption("⏱️ מנוע ניהול הקצב ממתין 6 שניות כדי למנוע חסימת API רשת...")
        time.sleep(6)
        
        # שלב 2: סוכן מודיעין אלטרנטיבי
        with st.spinner("🛰️ סוכן מודיעין אלטרנטיבי סורק נתוני לוגיסטיקה ולוויין..."):
            p2 = f"Search Google for alternative data, satellite tracking reports, port congestions, shipping delays, or factory inventory levels relevant to {focus_scope}. Summarize critical anomalies. Respond in Hebrew."
            res_alt = run_stable_agent(client, p2, "מודיעין אלטרנטיבי")
            
        # ⏱️ השהיה קריטית נוספת
        st.caption("⏱️ מנוע ניהול הקצב ממתין 6 שניות נוספות...")
        time.sleep(6)
        
        # שלב 3: סוכן קניין רוחני
        with st.spinner("💡 סוכן קניין ורגולציה סורק פטנטים ואישורים..."):
            p3 = f"Search Google for recent patent filings, R&D breakthroughs, subsidies, government grants, or critical regulatory updates regarding {focus_scope}. Respond in Hebrew."
            res_tech = run_stable_agent(client, p3, "קניין ורגולציה")

        # הצגת הממצאים במבנה של 3 עמודות
        st.write("---")
        st.success("✅ כל סוכני השטח סיימו את איסוף המידע המבוקר!")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown("### 📰 סוכן חדשות ומאקרו")
                st.write(res_news)
        with col2:
            with st.container(border=True):
                st.markdown("### 🛰️ סוכן מודיעין אלטרנטיבי")
                st.write(res_alt)
        with col3:
            with st.container(border=True):
                st.markdown("### 💡 סוכן קניין ורגולציה")
                st.write(res_tech)
                
        # ⏱️ השהיה אחרונה לפני הסינתזה
        st.caption("⏱️ ממתינים 6 שניות אחרונות לפני הרצת מנוע הסינתזה...")
        time.sleep(6)
        
        # -------------------------------------------------------------
        # שלב סינתזה סופית
        # -------------------------------------------------------------
        with st.spinner("🧠 מנוע סינתזה מגבש כעת את דוח ה-Alpha המשולב..."):
            prompt_final = f"""
            You are a senior investment manager. Review the following pieces of raw research gathered by our sub-agents for {focus_scope} (Risk Profile: {risk_profile}):
            
            [Market News Info]: {res_news}
            [Alternative & Supply Chain Info]: {res_alt}
            [Innovation & Patents Info]: {res_tech}
            
            Compile a final, polished comprehensive Alpha Convergence Report.
            Include:
            1. Executive Summary (The real story behind the scenes).
            2. Alpha Convergence Score (0-100) with strict mathematical justification based on how well the inputs align.
            3. Clear Buy/Sell/Hold strategic recommendations tailored to the {risk_profile} profile.
            
            Respond strictly and entirely in Hebrew.
            """
            
            try:
                final_report = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_final,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                st.write("---")
                st.header("📋 דוח אבחנות מודיעין פיננסי משולב (סינתזה סופית)")
                st.markdown(final_report.text)
            except Exception as final_exc:
                st.error(f"⚠️ מנוע הסינתזה נחסם זמנית על ידי ה-API החינמי: {str(final_exc)}\n\nהמלצה: המתן חצי דקה ולחץ שוב על כפתור ההפעלה.")
