import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import time
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Alpha Core - מנוע מדורג", layout="wide")

st.title("🎯 Macro AI Alpha Core (v3 - מנוע מדורג)")
st.subheader("סוכן מחקר רב-שלבי המונע שגיאות עומס באמצעות איסוף ועיבוד הדרגתי")

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

def generate_sector_chart(tickers):
    try:
        fig, ax = plt.subplots(figsize=(10, 3.5))
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6m")
            if not hist.empty:
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
    except:
        return None

# פונקציית עזר להרצת קריאת מודל בודדת עם מנגנון הגנה מפני עומס
def run_agent_step(client, prompt, step_name):
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
            if ("503" in str(exc) or "429" in str(exc)) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 4
                time.sleep(wait_time)
            else:
                return f"שגיאה זמנית באיסוף נתונים עבור {step_name}. המערכת תמשיך לשלב הבא."
    return "לא התקבלו נתונים."

# --- הפעלת מנוע הסוכנים המדורג ---
st.write("---")
if st.button("🚀 הפעל סוכן מחקר מדורג", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        # יצירת קונטיינרים דינמיים להצגת התקדמות השלבים למשתמש
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # אתחול הלקוח
        client = genai.Client(api_key=api_key)
        
        # שלב 0: בניית תרשים טכני מהיר מה-API
        status_text.markdown("#### 📊 שלב 0: משיכת נתוני שוק ויזואליים...")
        tickers_to_chart = [target_ticker] if target_ticker else SECTOR_MAP[selected_sector]
        img_bytes = generate_sector_chart(tickers_to_chart)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
        progress_bar.progress(15)
        
        focus_scope = f"המנייה {target_ticker}" if target_ticker else f"הענף {selected_sector}"
        
        # -------------------------------------------------------------
        # שלב 1: איסוף חדשות בסיסיות ומצב הסקטור
        # -------------------------------------------------------------
        status_text.markdown("#### 📰 שלב 1: סריקת חדשות עולמיות ומצב השוק הנוכחי...")
        prompt_1 = f"Search Google for the latest premium financial news and recent market events regarding {focus_scope}. Provide a summary of the top 3 macro highlights. Respond in Hebrew."
        raw_news_data = run_agent_step(client, prompt_1, "חדשות ומאקרו")
        
        with st.expander("🔍 ממצאי שלב 1: חדשות ומצב שוק", expanded=True):
            st.markdown(raw_news_data)
        progress_bar.progress(40)
        
        # -------------------------------------------------------------
        # שלב 2: נתונים אלטרנטיביים (לוויין, שרשרת אספקה, לוגיסטיקה)
        # -------------------------------------------------------------
        status_text.markdown("#### 🛰️ שלב 2: סריקת אינדיקטורים אלטרנטיביים ושרשראות אספקה...")
        prompt_2 = f"Search Google for alternative data, satellite tracking reports, port congestions, shipping delays, or inventory levels relevant to {focus_scope}. Summarize critical anomalies. Respond in Hebrew."
        raw_alt_data = run_agent_step(client, prompt_2, "נתונים אלטרנטיביים")
        
        with st.expander("🔍 ממצאי שלב 2: מודיעין אלטרנטיבי ולוגיסטיקה", expanded=True):
            st.markdown(raw_alt_data)
        progress_bar.progress(65)
        
        # -------------------------------------------------------------
        # שלב 3: חדשנות, פטנטים ורגולציה
        # -------------------------------------------------------------
        status_text.markdown("#### 💡 שלב 3: בדיקת צנרת פטנטים, אישורים ושינויי רגולציה...")
        prompt_3 = f"Search Google for recent patent filings, R&D breakthroughs, subsidies, government grants, or critical regulatory updates regarding {focus_scope}. Respond in Hebrew."
        raw_tech_data = run_agent_step(client, prompt_3, "קניין רוחני ורגולציה")
        
        with st.expander("🔍 ממצאי שלב 3: קניין רוחני ורגולציה", expanded=True):
            st.markdown(raw_tech_data)
        progress_bar.progress(85)
        
        # -------------------------------------------------------------
        # שלב 4: סינתזה סופית והפקת דוח אלפא משולב
        # -------------------------------------------------------------
        status_text.markdown("#### 🧠 שלב 4: מנוע סינתזה - גיבוש דוח המודיעין המשולב...")
        
        prompt_final = f"""
        You are a senior investment manager. Review the following pieces of raw research gathered by our sub-agents for {focus_scope} (Risk Profile: {risk_profile}):
        
        [Market News Info]: {raw_news_data}
        [Alternative & Supply Chain Info]: {raw_alt_data}
        [Innovation & Patents Info]: {raw_tech_data}
        
        Compile a final, polished comprehensive Alpha Convergence Report.
        Include:
        1. Executive Summary (The real story behind the scenes).
        2. Alpha Convergence Score (0-100) with strict mathematical justification based on how well the news, tech, and alternative data align.
        3. Clear Buy/Sell/Hold strategic recommendations tailored to the {risk_profile} profile.
        
        Respond strictly and entirely in Hebrew.
        """
        
        # קריאה אחרונה ללא חיפוש (כי הנתונים כבר אצלנו), מה שמבטיח מהירות מקסימלית
        try:
            final_report = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_final,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            
            status_text.success("✅ המחקר המדורג הושלם בהצלחה!")
            progress_bar.progress(100)
            
            st.write("---")
            st.header("📋 דוח אבחנות מודיעין פיננסי משולב (סינתזה סופית)")
            st.markdown(final_report.text)
        except Exception as final_exc:
            st.error(f"מנוע הסינתזה נתקל בשגיאה: {str(final_exc)}")
