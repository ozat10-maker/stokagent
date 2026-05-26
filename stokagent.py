import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import time
import concurrent.futures  # ספרייה להפעלת סוכנים במקביל
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Alpha Core - מנוע מקבילי", layout="wide")

st.title("🎯 Macro AI Alpha Core (v4 - מנוע סוכנים מקבילי)")
st.subheader("סוכני מחקר עצמאיים הפועלים במקביל (Parallel Execution) למהירות שיא ומניעת עומס")

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

# תיקון פונקציית הגרף - תמיכה מלאה במנייה בודדת או ענף שלם
def generate_market_chart(tickers):
    try:
        fig, ax = plt.subplots(figsize=(10, 3.5))
        
        # אם הועבר מחרוזת בודדת, נהפוך אותה לרשימה
        if isinstance(tickers, str):
            tickers = [tickers]
            
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6m")
            if not hist.empty:
                if len(tickers) == 1:
                    # מנייה בודדת: נציג מחיר סגירה אמיתי בדולרים
                    ax.plot(hist.index, hist['Close'], label=f"{ticker} Price ($)", color="blue")
                    ax.set_title(f"{ticker} Historical Trend (Last 6 Months)")
                    ax.set_ylabel("Price ($)")
                else:
                    # מספר מניות: נרמול ל-100 לצורך השוואה אחוזית
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
        st.sidebar.error(f"שגיאה בהפקת גרף: {str(e)}")
        return None

# פונקציה שכל סוכן מריץ באופן עצמאי ומבודד במקביל
def execute_single_agent_task(api_key, prompt, step_name):
    try:
        client = genai.Client(api_key=api_key)
        
        # מנגנון ניסיונות קצר לכל סוכן למניעת נפילת רשת
        for attempt in range(2):
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
            except:
                time.sleep(3)
        return f"סוכן {step_name} חווה עומס זמני ברשת ולא הצליח למשוך מידע."
    except Exception as e:
        return f"שגיאה בסוכן {step_name}: {str(e)}"

# --- הפעלת מנוע הסוכנים המקבילי ---
st.write("---")
if st.button("🚀 הפעל רשת סוכנים במקביל", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        # הצגת הגרף המתוקן מיד בתחילת הריצה
        st.markdown("#### 📊 שלב 0: הפקת נתוני שוק ויזואליים...")
        tickers_to_chart = target_ticker if target_ticker else SECTOR_MAP[selected_sector]
        img_bytes = generate_market_chart(tickers_to_chart)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
            
        focus_scope = f"המנייה {target_ticker}" if target_ticker else f"הענף {selected_sector}"
        
        # הגדרת משימות המחקר עבור שלושת הסוכנים
        prompts_dict = {
            "חדשות ומאקרו": f"Search Google for the latest premium financial news and recent market events regarding {focus_scope}. Provide a summary of the top 3 macro highlights. Respond in Hebrew.",
            "מודיעין אלטרנטיבי": f"Search Google for alternative data, satellite tracking reports, port congestions, shipping delays, or factory inventory levels relevant to {focus_scope}. Summarize critical anomalies. Respond in Hebrew.",
            "קניין רוחני ורגולציה": f"Search Google for recent patent filings, R&D breakthroughs, subsidies, government grants, or critical regulatory updates regarding {focus_scope}. Respond in Hebrew."
        }
        
        # הדלקת ספינר התקדמות
        with st.spinner("⚡ משלח סוכני מחקר עצמאיים למשימות מקביליות ברשת..."):
            
            # הפעלת ThreadPoolExecutor להרצה בו-זמנית
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # שליחת המשימות במקביל לכל הסוכנים
                future_to_agent = {
                    executor.submit(execute_single_agent_task, api_key, prompt, name): name 
                    for name, prompt in prompts_dict.items()
                }
                
                # איסוף התוצאות מהסוכנים ברגע שהם מסיימים
                results = {}
                for future in concurrent.futures.as_completed(future_to_agent):
                    agent_name = future_to_agent[future]
                    try:
                        results[agent_name] = future.result()
                    except Exception as exc:
                        results[agent_name] = f"הסוכן נכשל: {str(exc)}"
                        
        # הצגת ממצאי הסוכנים שפעלו במקביל בתוך תיבות קריאה נפרדות
        st.success("✅ כל סוכני השטח חזרו עם ממצאים!")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown("### 📰 סוכן חדשות ומאקרו")
                st.write(results.get("חדשות ומאקרו"))
        with col2:
            with st.container(border=True):
                st.markdown("### 🛰️ סוכן מודיעין אלטרנטיבי")
                st.write(results.get("מודיעין אלטרנטיבי"))
        with col3:
            with st.container(border=True):
                st.markdown("### 💡 סוכן קניין ורגולציה")
                st.write(results.get("קניין רוחני ורגולציה"))
                
        # -------------------------------------------------------------
        # שלב סינתזה סופית (הרצה מהירה ללא אינטרנט)
        # -------------------------------------------------------------
        with st.spinner("🧠 מנוע סינתזה מגבש כעת את דוח ה-Alpha המשולב..."):
            prompt_final = f"""
            You are a senior investment manager. Review the following pieces of raw research gathered by our parallel sub-agents for {focus_scope} (Risk Profile: {risk_profile}):
            
            [Market News Info]: {results.get('חדשות ומאקרו')}
            [Alternative & Supply Chain Info]: {results.get('מודיעין אלטרנטיבי')}
            [Innovation & Patents Info]: {results.get('קניין רוחני ורגולציה')}
            
            Compile a final, polished comprehensive Alpha Convergence Report.
            Include:
            1. Executive Summary (The real story behind the scenes).
            2. Alpha Convergence Score (0-100) with strict mathematical justification based on how well the inputs align.
            3. Clear Buy/Sell/Hold strategic recommendations tailored to the {risk_profile} profile.
            
            Respond strictly and entirely in Hebrew.
            """
            
            try:
                client = genai.Client(api_key=api_key)
                final_report = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_final,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                
                st.write("---")
                st.header("📋 דוח אבחנות מודיעין פיננסי משולב (סינתזה סופית)")
                st.markdown(final_report.text)
            except Exception as final_exc:
                st.error(f"מנוע הסינתזה נתקל בשגיאה: {str(final_exc)}")
