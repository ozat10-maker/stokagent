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
                        # אם זו שגיאת עומס ונותרו ניסיונות, נמתין ונסה שוב
                        if ("503" in str(exc) or "429" in str(exc)) and attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5  # המתנה הולכת וגדלה (5, 10 שניות)
                            st.caption(f"⚠️ השרת עמוס זמנית (503). מבצע ניסיון חוזר {attempt + 2}/{max_retries} בעוד {wait_time} שניות...")
                            time.sleep(wait_time)
                        else:
                            raise exc  # אם זו שגיאה אחרת או שנגמרו הניסיונות, זרוק את השגיאה החוצה
                
                # הצגת דוח המודיעין הפיננסי האוטומטי
                if response:
                    st.write("---")
                    st.header("📋 דוח מודיעין פיננסי עצמאי ומבוסס חיפוש רשת")
                    st.markdown(response.text)
                    
                    # הצגת מקורות המידע מהרשת
                    if response.candidates and response.candidates[0].grounding_metadata:
                        metadata = response.candidates[0].grounding_metadata
                        if metadata.grounding_chunks:
                            with st.expander("🔗 צפה במקורות ואתרי החדשות מהם הסוכן שאב מידע:"):
                                for chunk in metadata.grounding_chunks:
                                    if chunk.web:
                                        st.write(f"- [{chunk.web.title}]({chunk.web.uri})")
                                        
            except Exception as e:
                st.error(f"❌ שגיאה בהפעלת סוכן המחקר: {str(e)}\n\nהמלצה: נסה ללחוץ שוב על כפתור ההפעלה בעוד מספר רגעים.")
