import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import time
from google import genai
from google.genai import types

# הגדרת תצורת דף רחב למערכת האנליסטים
st.set_page_config(page_title="Macro AI Alpha Core - מנוע חסכוני", layout="wide")

st.title("🎯 Macro AI Alpha Core (v6 - מנוע אחוד וחסכוני)")
st.subheader("מנוע מחקר מותאם למסלול החינמי - צריכת קריאה בודדת (1 Call) לחיסכון במכסה היומית")

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

# --- הפעלת מנוע הסוכנים המאוחד ---
st.write("---")
if st.button("🚀 הפעל מחקר שוק מאוחד (צורך קריאה בודדת)", type="primary"):
    if not api_key:
        st.warning("אנא הזן מפתח API בתפריט הצד.")
    else:
        # הצגת הגרף (מתבצע מקומית בשרת של Streamlit ולא צורך מכסת API)
        st.markdown("#### 📊 שלב 0: הפקת נתוני שוק ויזואליים...")
        tickers_to_chart = target_ticker if target_ticker else SECTOR_MAP[selected_sector]
        img_bytes = generate_market_chart(tickers_to_chart)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
            
        focus_scope = f"המנייה {target_ticker}" if target_ticker else f"הענף {selected_sector}"
        
        # בניית פרומפט מאוחד שמבצע הכל בפעימה אחת
        prompt_unified = f"""
        You are an expert investment manager and macro researcher. 
        Your task is to generate a comprehensive Alpha Convergence Report for {focus_scope} based on a target risk profile of '{risk_profile}'.
        
        Using Google Search, explore the web and compile data across these three specific categories:
        1. **Global Market News:** Summary of recent major geopolitical developments, trade constraints, or macro highlights impacting this asset class.
        2. **Alternative Data & Logistics:** Look for tracking reports regarding shipping bottlenecks, production gluts, or factory/port activity anomalies.
        3. **Innovation & Patents:** Search for recent patent filings, regulatory approvals, or technological breakthroughs.
        
        Synthesize all of these findings into a polished, definitive investment report in Hebrew.
        The report must include:
        - **ממצאים מרכזיים מהשטח (מודיעין פיננסי משולב):** A deep synthesis of the news, alternative metrics, and tech breakthroughs.
        - **מדד התלכדות תובנות (Alpha Convergence Score):** A numerical score from 0-100 with strict logical justification.
        - **המלצה אסטרטגית מנומקת:** Clear buy/sell/hold tactical guidance tailored specifically to a {risk_profile} investment strategy.
        
        Respond strictly and entirely in Hebrew.
        """
        
        with st.spinner("🧠 סוכן המאקרו המאוחד מבצע חיפוש רשת ומגבש את הדוח הסופי (זה עשוי לקחת כ-15-20 שניות)..."):
            try:
                client = genai.Client(api_key=api_key)
                
                # ביצוע קריאה בודדת ומאובטחת
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_unified,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                
                st.write("---")
                st.success("✅ המחקר הושלם בהצלחה תוך שימוש בקריאה בודדת!")
                st.header("📋 דוח אבחנות מודיעין פיננסי משולב")
                st.markdown(response.text)
                
                # הצגת מקורות המידע בהם הסוכן ביקר
                if response.candidates and response.candidates.grounding_metadata:
                    metadata = response.candidates.grounding_metadata
                    if metadata.grounding_chunks:
                        with st.expander("🔗 צפה במקורות ואתרי החדשות מהם הסוכן שאב מידע:"):
                            for chunk in metadata.grounding_chunks:
                                if chunk.web:
                                    st.write(f"- [{chunk.web.title}]({chunk.web.uri})")
                                    
            except Exception as e:
                if "429" in str(e):
                    st.error("❌ חרגת ממכסת הבקשות היומית הזמנית של גוגל למסלול החינמי. גוגל תאפס ותפתח לך את החשבון מחדש אוטומטית בהמשך היום. הקוד הנוכחי שהעלינו כעת ימנע את הישנות המקרה ברגע שהחסימה תשתחרר!")
                else:
                    st.error(f"❌ שגיאה בהפעלת מנוע המחקר: {str(e)}")
