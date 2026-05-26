import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import io
import time
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Alpha Core - מנוע איתור מניות", layout="wide")

# אתחול משתני State גלובליים
if "current_view" not in st.session_state:
    st.session_state.current_view = "dashboard"
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

# תפריט צד: הגדרות מפתח ופרופיל מנהל השקעות
st.sidebar.header("⚙️ הגדרות מערכת וסיכון")

# ניהול מפתח API של Gemini
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("מפתח API נטען אוטומטית ✅")
else:
    api_key = st.sidebar.text_input("הזן מפתח API של Gemini Pro:", type="password")

# הגדרת פרופיל סיכון ותחומי עניין
risk_profile = st.sidebar.selectbox("פרופיל סיכון יעד:", ["Conservative", "Moderate", "Aggressive"])
selected_sector = st.sidebar.selectbox(
    "תחום עניין לסריקה וחקר:", 
    ["Semiconductors & AI Hardware", "Energy & Global Infrastructure", "Commodities & Shipping", "Biotech & Healthcare"]
)

# עזרי עקיפת צנזורה ותרגום
report_lang = st.sidebar.radio("שפת הפקת האבחנות:", ["עברית (Hebrew)", "אנגלית (English)"])

# --- פונקציות ליבה עצמאיות למשיכת נתונים ובניית גרפים ---

def generate_and_analyze_technical_chart(ticker_str):
    """משיכת נתוני מחיר, בניית גרף טכני עצמאי והמרתו לביטים עבור ה-AI"""
    try:
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        # חישוב אינדיקטורים טכניים עצמאיים
        hist['MA50'] = hist['Close'].rolling(window=50).mean()
        hist['MA200'] = hist['Close'].rolling(window=200).mean()
        
        # יצירת תרשים עצמאי באמצעות Matplotlib (במערך זיכרון ללא שמירה בדיסק)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(hist.index, hist['Close'], label='Price', color='black')
        ax.plot(hist.index, hist['MA50'], label='MA 50', color='blue', linestyle='--')
        ax.plot(hist.index, hist['MA200'], label='MA 200', color='red', linestyle='-')
        ax.set_title(f"{ticker_str} Technical Trends & Moving Averages")
        ax.legend()
        ax.grid(True)
        
        # שמירת הגרף בזיכרון כקובץ PNG (על מנת להזין אותו ישירות ל-Gemini Vision)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        image_bytes = buf.getvalue()
        plt.close(fig)
        
        return image_bytes, hist
    except:
        return None, None

def fetch_financial_reports_data(ticker_str):
    """משיכת נתוני דוחות כספיים אחרונים (פונדמנטלי)"""
    try:
        stock = yf.Ticker(ticker_str)
        # משיכת דוחות רווח והפסד רבעוניים
        quarterly_financials = stock.quarterly_financials
        # מידע כללי
        info = stock.info
        return quarterly_financials, info
    except:
        return None, None

# --- המסך הראשי של המערכת ---
st.title("🎯 Macro AI Alpha Core")
st.subheader("מערכת מולטי-מודאלית מבוססת Gemini Pro לאיתור השקעות אלטרנטיביות")

# מנוע החיפוש הראשי באפליקציה
col_input, col_action = st.columns([4, 1])
target_ticker = col_input.text_input("הזן סימול מניית מטרה לבדיקת התלכדות תובנות (למשל: NVDA, XOM, TSMC):", "NVDA").upper().strip()

if col_action.button("הפעל מנוע אבחון מקיף", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד")
    else:
        with st.spinner("המנוע מפעיל רדארים וסורק מקורות מידע אלטרנטיביים..."):
            
            # 1. משיכת נתונים ובניית גרפים עצמאית
            img_bytes, price_hist = generate_and_analyze_technical_chart(target_ticker)
            financials, stock_info = fetch_financial_reports_data(target_ticker)
            
            if price_hist is not None:
                # מדמה העלאת קבצים אלטרנטיביים לצורך ה-MVP (במציאות המשתמש יעלה או נמשוך מ-API)
                st.session_state.analysis_results = {
                    "ticker": target_ticker,
                    "img_bytes": img_bytes,
                    "financials": financials.to_string() if financials is not None else "No financial statements data",
                    "info": stock_info
                }
            else:
                st.error("לא ניתן היה למשוך נתוני שוק עבור סימול זה.")

# הצגת תוצאות הניתוח וממשק הכלים האלטרנטיביים
if st.session_state.analysis_results:
    res = st.session_state.analysis_results
    st.write("---")
    st.header(f"🔍 ממצאים ואבחנות עבור מניית {res['ticker']}")
    
    # הצגת הגרף שהמערכת יצרה עצמאית
    st.subheader("📊 גרף מגמה טכני (נוצר עצמאית על ידי המנוע)")
    st.image(res['img_bytes'], use_container_width=True)
    
    # -------------------------------------------------------------
    # ממשק קלט לנתונים אלטרנטיביים (לוויין, מגזינים, פטנטים)
    # -------------------------------------------------------------
    st.write("---")
    st.subheader("🛰️ הזנת נתונים אלטרנטיביים ומולטי-מודאליים (רובד ויזואלי וגיאופוליטי)")
    
    col_v1, col_v2 = st.columns(2)
    uploaded_satellite = col_v1.file_saver = col_v1.file_uploader("העלה תמונת לוויין / תשתיות (נמלים, מיכלי נפט, חניונים):", type=["png", "jpg", "jpeg"])
    uploaded_magazine = col_v2.file_uploader("העלה צילום גרף/ניתוח ממגזין כלכלי (Bloomberg, Economist):", type=["png", "jpg", "jpeg"])
    
    geopolitical_news = st.text_area("הזן כותרות או טקסט חדשותי ממדינות מקומיות (עקיפת צנזורה):", 
                                     value="דיווחים מקומיים בתקשורת הזרה על מגבלות ייצוא חדשות ומתיחות בנמלי המסחר המרכזיים.")
    
    if st.button("🚀 הרץ ניתוח Gemini Pro משולב (ציון התלכדות תובנות)", type="primary"):
        with st.spinner("מנוע Gemini 2.5 Pro מנתח קבצי תמונה, דוחות כספיים וחדשות במקביל..."):
            try:
                # הגדרת לקוח ג'נאי
                client = genai.Client(api_key=api_key)
                
                # בניית התוכן המולטי-מודאלי למודל
                contents = []
                
                # 1. הוספת הגרף הטכני שהמערכת יצרה עצמאית
                contents.append(types.Part.from_bytes(data=res['img_bytes'], mime_type="image/png"))
                
                # 2. הוספת תמונת הלוויין במידה והועלתה
                if uploaded_satellite:
                    contents.append(types.Part.from_bytes(data=uploaded_satellite.getvalue(), mime_type="image/png"))
                
                # 3. הוספת גרף המגזין במידה והועלה
                if uploaded_magazine:
                    contents.append(types.Part.from_bytes(data=uploaded_magazine.getvalue(), mime_type="image/png"))
                
                # 4. בניית פרומפט ההנחיה המתוחכם (כולל כל 5 האספקטים וההוספות החדשות)
                lang_rule = "Respond ONLY in Hebrew." if report_lang == "עברית (Hebrew)" else "Respond ONLY in English."
                
                prompt_text = f"""
                You are a senior investment manager and multi-disciplinary macro analyst.
                Analyze the following data points for the stock {res['ticker']} and generate an Alpha Convergence Report:
                
                1. **Technical Graph (Attached Image 1):** Analyze the trends and moving averages generated by the engine.
                2. **Fundamental & Financial Reports:** Examine these recent quarterly figures:\n{res['financials']}\nAnalyze short/long term behavior.
                3. **Alternative Satellite Imagery (If attached):** Look for supply chain anomalies, oil levels, or port activity.
                4. **Financial Media Chart (If attached):** Interpret hidden chart insights from premium magazines.
                5. **Geopolitical Radar:** Evaluate the following raw text for hidden censorship or macro risks:\n{geopolitical_news}
                
                **Incorporate Advanced Metrics:**
                - **Patent Pipeline Tracker:** Assess how future innovations might impact this stock's moat based on the sector ({selected_sector}).
                - **Alternative Sentiment:** Cross-reference with macro sentiment.
                - **Insight Convergence Score:** Provide a final mathematical/justified score (0-100) indicating how aligned all 5 indicators are for an investment.
                
                {lang_rule}
                """
                contents.append(prompt_text)
                
                # הפעלת מודל הפרו החזק
                response = client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                
                # הצגת דוח האנליסט המורחב
                st.write("---")
                st.subheader("📋 דוח אבחנות מודיעין פיננסי משולב")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"שגיאה בהפעלת מנוע הניתוח של Gemini Pro: {str(e)}")
