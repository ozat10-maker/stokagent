import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import time
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Alpha Core - מנוע איתור מניות", layout="wide")

st.title("🎯 Macro AI Alpha Core")
st.subheader("מערכת סוכנים אוטומטית לסריקת ענפים ואיתור השקעות (Powered by Gemini 2.5 Flash)")

# תפריט צד: הגדרות מפתח ופרופיל מנהל השקעות
st.sidebar.header("⚙️ הגדרות מערכת וסיכון")

# ניהול מפתח API של Gemini
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("מפתח API נטען אוטומטית ✅")
else:
    api_key = st.sidebar.text_input("הזן מפתח API של Gemini:", type="password")

# בחירת פרופיל סיכון
risk_profile = st.sidebar.selectbox("פרופיל סיכון יעד:", ["Conservative", "Moderate", "Aggressive"])

# הגדרת ענפים ומניות מובילות כברירת מחדל לאוטומציה
SECTOR_MAP = {
    "Technology & AI Semiconductors": ["NVDA", "TSM", "AMD", "ASML"],
    "Energy & Global Infrastructure": ["XOM", "CVX", "SHEL", "NextEra"],
    "Commodities & Global Shipping": ["VALE", "CAT", "ZIM", "BHP"],
    "Biotech & Healthcare": ["LLY", "NVO", "PFE", "MRK"]
}

# 1. שלב חובה: בחירת ענף
selected_sector = st.selectbox(
    "1. בחר ענף/סקטור לסריקה מקיפה:", 
    list(SECTOR_MAP.keys())
)

# 2. שלב אופציונלי: התעמקות במנייה ספציפית
st.write("---")
st.markdown("### 🔍 התעמקות במנייה ספציפית (אופציונלי)")
use_specific_stock = st.checkbox("אני רוצה לבחור מנייה ספציפית לניתוח בתוך הענף")

target_ticker = None
if use_specific_stock:
    ticker_options = SECTOR_MAP[selected_sector]
    selected_ticker = st.selectbox(f"בחר מנייה מתוך ענף {selected_sector}:", ticker_options)
    custom_ticker = st.text_input("או הזן סימול מנייה אחרת ידנית (למשל: AAPL, MSFT):").upper().strip()
    target_ticker = custom_ticker if custom_ticker else selected_ticker

# פונקציית עזר ליצירת גרף טכני אוטומטי לענף/מנייה
def generate_sector_chart(tickers):
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6m")
            if not hist.empty:
                # נרמול המחיר ל-100 כדי להשוות אחוזים
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

# --- הפעלת מנוע הסוכנים האוטומטי עם מנגנון הגנה מפני עומס ---
st.write("---")
if st.button("🚀 הפעל סוכן מחקר אוטומטי", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד על מנת להפעיל את הסוכן.")
    else:
        with st.spinner(f"הסוכן יוצא לרשת, מחפש חדשות ומנתח נתונים עבור סקטור {selected_sector}..."):
            try:
                # אתחול הלקוח של Gemini
                client = genai.Client(api_key=api_key)
                
                # 1. יצירת גרף ויזואלי עצמאי של נתוני השוק בשבילו
                tickers_to_chart = [target_ticker] if target_ticker else SECTOR_MAP[selected_sector]
                img_bytes = generate_sector_chart(tickers_to_chart)
                
                # 2. הכנת חלקי התוכן
                contents = []
                if img_bytes:
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                    st.subheader("📊 ביצועי שוק נוכחיים (נוצר אוטומטית על ידי המערכת)")
                    st.image(img_bytes, use_container_width=True)
                
                # 3. בניית הנחיית הסוכן
                focus_scope = f"המנייה הספציפית: {target_ticker}" if target_ticker else f"כלל הענף והחברות המובילות בו: {', '.join(SECTOR_MAP[selected_sector])}"
                
                prompt_text = f"""
                You are an autonomous AI macro-research analyst. Your goal is to identify investment opportunities in the sector: '{selected_sector}'.
                Focus Scope: {focus_scope}
                Target Risk Profile: {risk_profile}
                
                Perform the following autonomous research using Google Search to gather alternative and recent data from premium global finance and news sources:
                
                1. **Global & Regional News:** Search for uncensored regional news, export bans, or logistical challenges related to this sector.
                2. **Alternative Insights & Satellite/Supply Chain Indicators:** Look for recent reports about port congestions, factory inventory gluts, aircraft movement trends, or satellite-tracked oil/commodity storages relevant to this industry.
                3. **Patent & Innovation Pipeline:** Scan recent news for breaking patents, regulatory updates (FDA approvals, chips act funding, etc.).
                4. **Chart Interpretation:** If an image is attached, review the trends shown.
                
                Synthesize all findings and provide:
                - Top Market Insights (What is happening right now behind the scenes).
                - An Alpha Convergence Score (0-100) assessing the alignment of technical, fundamental, and geopolitical indicators.
                - Actionable recommendations for an investment manager.
                
                Respond strictly and entirely in Hebrew.
                """
                contents.append(prompt_text)
                
                # 4. מנגנון Retry להתמודדות עם שגיאות עומס (503 / 429)
                max_retries = 3
                response = None
                
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=contents,
                            config=types.GenerateContentConfig(
                                temperature=0.3,
                                tools=[types.Tool(google_search=types.GoogleSearch())]
                            )
                        )
                        break  # הצלחנו! יוצאים מהלולאה
                    except Exception as exc:
                        if ("503" in str(exc) or "429" in str(exc)) and attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            st.caption(f"⚠️ השרת עמוס זמנית (503). מבצע ניסיון חוזר {attempt + 2}/{max_retries} בעוד {wait_time} שניות...")
                            time.sleep(wait_time)
                        else:
                            raise exc
                
                # הצגת דוח המודיעין הפיננסי האוחזר
                if response:
                    st.write("---")
                    st.header("📋 דוח מודיעין פיננסי עצמאי ומבוסס חיפוש רשת")
                    st.markdown(response.text)
                    
                    # הצגת מקורות המידע מהרשת
                    if response.candidates and response.candidates.grounding_metadata:
                        metadata = response.candidates.grounding_metadata
                        if metadata.grounding_chunks:
                            with st.expander("🔗 צפה במקורות ואתרי החדשות מהם הסוכן שאב מידע:"):
                                for chunk in metadata.grounding_chunks:
                                    if chunk.web:
                                        st.write(f"- [{chunk.web.title}]({chunk.web.uri})")
                                        
            except Exception as e:
                st.error(f"❌ שגיאה בהפעלת סוכן המחקר: {str(e)}\n\nהמלצה: נסה ללחוץ שוב על כפתור ההפעלה בעוד מספר רגעים.")
