import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request as GAuthRequest
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
import altair as alt

FOLDER_ID = "1a275gJbbClAMz-ZY-so1BuMVbQDW6-cA"

# --- ФУНКЦИИ ---
def send_telegram_message(text):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception:
        pass 

def upload_to_drive(file_bytes, filename, credentials):
    if not credentials.valid:
        credentials.refresh(GAuthRequest())
    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    headers = {"Authorization": "Bearer " + credentials.token}
    metadata = {"name": filename, "parents": [FOLDER_ID]}
    files = {
        'metadata': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
        'file': (filename, file_bytes, 'image/jpeg')
    }
    r = requests.post(url, headers=headers, files=files)
    if r.status_code == 200:
        file_id = r.json().get('id')
        requests.post(f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions", 
            headers={"Authorization": "Bearer " + credentials.token, "Content-Type": "application/json"},
            json={"role": "reader", "type": "anyone"})
        return f"https://drive.google.com/uc?id={file_id}", None
    return None, r.text # Возвращаем точную ошибку для дебага

def get_streaks(records):
    if not records: return 0, 0
    df = pd.DataFrame(records)
    r_streak, s_streak = 0, 0
    
    if 'Вместе ✨' in df.columns:
        df_rituals = df[(df['Вместе ✨'] == '✅') & (df['Ритуал'] != 'Ежедневный Дневник 🌸')]
        if not df_rituals.empty:
            df_rituals['Дата'] = pd.to_datetime(df_rituals['Дата']).dt.date
            dates = sorted(df_rituals['Дата'].unique(), reverse=True)
            today = datetime.now().date()
            if dates[0] == today or dates[0] == (today - timedelta(days=1)):
                r_streak = 1; curr = dates[0]
                for d in dates[1:]:
                    if d == curr - timedelta(days=1): r_streak += 1; curr = d
                    else: break
                    
    if 'Дневник Лисички' in df.columns and 'Дневник Мишки' in df.columns:
        df_diary = df[(df['Ритуал'] == 'Ежедневный Дневник 🌸') & (df['Дневник Лисички'] != '') & (df['Дневник Мишки'] != '')]
        if not df_diary.empty:
            df_diary['Дата'] = pd.to_datetime(df_diary['Дата']).dt.date
            dates_s = sorted(df_diary['Дата'].unique(), reverse=True)
            today = datetime.now().date()
            if dates_s[0] == today or dates_s[0] == (today - timedelta(days=1)):
                s_streak = 1; curr_s = dates_s[0]
                for d in dates_s[1:]:
                    if d == curr_s - timedelta(days=1): s_streak += 1; curr_s = d
                    else: break
    return r_streak, s_streak

# --- НАСТРОЙКИ UI ---
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

if "theme" not in st.query_params: st.query_params["theme"] = "dark" 
st.sidebar.title("⚙️ Настройки")
theme_choice = st.sidebar.radio("Оформление:", ["Темная тема 🌙", "Светлая тема ☀️"], index=0 if st.query_params["theme"] == "dark" else 1)

bg_color, text_color, input_bg = ("#000000", "#ffffff", "#111111") if theme_choice == "Темная тема 🌙" else ("#ffffff", "#000000", "#f9f9f9")
st.query_params["theme"] = "dark" if theme_choice == "Темная тема 🌙" else "light"

st.markdown(f"""
    <style>
    .stApp, .stApp > header {{ background-color: {bg_color} !important; }}
    h1, h2, h3, p, label, span, li, .stMetric label {{ color: {text_color} !important; font-family: 'Arial', sans-serif; }}
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {{
        background-color: {input_bg} !important; color: {text_color} !important; border: 1px solid {text_color} !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{ color: {text_color} !important; opacity: 0.5 !important; }}
    div[data-baseweb="popover"] > div, ul[role="listbox"] {{ background-color: {input_bg} !important; }}
    li[role="option"]:hover {{ background-color: {text_color} !important; color: {bg_color} !important; }}
    div[data-testid="stFormSubmitButton"] button {{ background-color: {text_color} !important; border: 2px solid {text_color} !important; }}
    div[data-testid="stFormSubmitButton"] button p {{ color: {bg_color} !important; font-weight: bold !important; }}
    div[data-testid="stFormSubmitButton"] button:hover {{ opacity: 0.8; }}
    svg {{ fill: {text_color} !important; }}
    .stTabs [data-baseweb="tab-list"] button {{ color: {text_color} !important; font-size: 1rem !important; padding: 10px 10px !important; }}
    [data-testid="stDataFrame"] {{ background-color: {input_bg} !important; border-radius: 8px; }}
    
    @keyframes breathe {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} 100% {{ transform: scale(1); }} }}
    [data-testid="stImage"] img {{ animation: breathe 4s ease-in-out infinite; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.2); }}
    </style>
""", unsafe_allow_html=True)

# --- АВТОРИЗАЦИЯ И БД ---
if "user" not in st.query_params:
    st.title("Привет! Кто ты? 👋")
    col1, col2 = st.columns(2)
    if col1.button("Я Лисичка 🦊", use_container_width=True): st.query_params["user"] = "fox"; st.rerun()
    if col2.button("Я Мишка 🐻", use_container_width=True): st.query_params["user"] = "bear"; st.rerun()
    st.stop()

current_user = "Лисичка 🦊" if st.query_params["user"] == "fox" else "Мишка 🐻"
partner = "Мишка 🐻" if st.query_params["user"] == "fox" else "Лисичка 🦊"

st.sidebar.write(f"Профиль: **{current_user}**")
if st.sidebar.button("Сменить профиль"): st.query_params.pop("user", None); st.rerun()

@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["json_key"])
    credentials = Credentials.from_service_account_info(key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return credentials, gspread.authorize(credentials)

try:
    g_creds, client = init_connection()
    sheet = client.open("Наши ритуалы").sheet1 
    records = sheet.get_all_records()
except Exception as e:
    st.error(f"Ошибка базы данных: {e}")
    st.stop()

r_streak, s_streak = get_streaks(records)
today_str = datetime.now().strftime("%Y-%m-%d")

# ================= Вкладки =================
tab1, tab2, tab3, tab4 = st.tabs(["📝 Ритуалы", "🌸 Дневник", "📸 Капсула", "📊 Стат."])

# ----------------- ВКЛАДКА 1: РИТУАЛЫ -----------------
with tab1:
    pet_happy = any(str(r.get('Дата')) == today_str and str(r.get('Вместе ✨')) == '✅' and str(r.get('Ритуал')) != 'Ежедневный Дневник 🌸' for r in records)
    pet_stage = 2 if r_streak >= 14 else 1
    pet_mood = "happy" if pet_happy else "sad"
    
    col_t, col_img, col_m = st.columns([2, 1, 1])
    with col_t: st.title("✨ Ритуалы")
    with col_img: 
        try: st.image(f"stage{pet_stage}_{pet_mood}.png", use_container_width=True)
        except Exception: st.info("🐣")
    with col_m: st.metric("🔥 Серия", f"{r_streak} дн.")
    st.divider()

    base_rituals = ["🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога", "🎮 Совместные игры"]
    history_rituals = [str(r['Ритуал']) for r in records if r.get('Ритуал') and r.get('Ритуал') != 'Ежедневный Дневник 🌸']
    all_rituals = sorted(list(set(base_rituals + history_rituals)))

    with st.form("habit_form"):
        date_input = st.text_input("Дата", value=today_str)
        selected_ritual = st.selectbox("Что выполнили?", all_rituals)
        custom_ritual = st.text_input("ИЛИ новый ритуал:")
        
        # Проверяем, есть ли уже послание за сегодня для выбранного ритуала
        existing_my_msg = ""
        current_final_ritual = custom_ritual.strip() if custom_ritual.strip() else selected_ritual
        for row in records:
            if str(row.get('Дата')) == date_input and str(row.get('Ритуал')) == current_final_ritual:
                my_col = 'Послание Лисички' if current_user == "Лисичка 🦊" else 'Послание Мишки'
                existing_my_msg = str(row.get(my_col, '')).strip()
                break

        secret_message = st.text_area("💌 Тайное послание партнеру (необязательно):", value=existing_my_msg, placeholder="Партнер увидит, когда тоже выполнит этот ритуал...")
        
        if st.form_submit_button("Я выполнил(а)! Сохранить ✨"):
            final_ritual = custom_ritual.strip() if custom_ritual.strip() else selected_ritual
            match_idx, existing_fox, existing_bear, partner_msg = None, "❌", "❌", ""
            
            for i, row in enumerate(records):
                if str(row.get('Дата', '')) == date_input and str(row.get('Ритуал', '')) == final_ritual:
                    match_idx = i + 2 
                    existing_fox = row.get('Лисичка 🦊', '❌')
                    existing_bear = row.get('Мишка 🐻', '❌')
                    msg_col = 'Послание Мишки' if partner == "Мишка 🐻" else 'Послание Лисички'
                    partner_msg = str(row.get(msg_col, '')).strip()
                    break
            
            # Отправка уведомления, если послание обновилось/добавилось
            if secret_message.strip() and secret_message.strip() != existing_my_msg:
                send_telegram_message(f"💌 <b>{current_user}</b> оставил(а) тебе тайное послание за <b>{final_ritual}</b>! Отметь ритуал, чтобы прочитать.")

            if match_idx:
                new_fox = "✅" if current_user == "Лисичка 🦊" else existing_fox
                new_bear = "✅" if current_user == "Мишка 🐻" else existing_bear
                new_together = "✅" if (new_fox == "✅" and new_bear == "✅") else "❌"
                
                sheet.update_cell(match_idx, 3, new_fox)
                sheet.update_cell(match_idx, 4, new_bear)
                sheet.update_cell(match_idx, 5, new_together)
                my_col_idx = 6 if current_user == "Лисичка 🦊" else 7
                sheet.update_cell(match_idx, my_col_idx, secret_message.strip())
                
                if new_together == "✅":
                    st.balloons()
                    st.success(f"Ого! Галочка ВМЕСТЕ получена! 🎉")
                    if partner_msg:
                        st.info(f"💌 **Послание от {partner}:**\n\n*{partner_msg}*")
                else:
                    st.success("Отлично! Данные обновлены. Ждем партнера ✨")
            else:
                new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
                new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
                f_msg = secret_message.strip() if current_user == "Лисичка 🦊" else ""
                b_msg = secret_message.strip() if current_user == "Мишка 🐻" else ""
                
                new_row = [date_input, final_ritual, new_fox, new_bear, "❌", f_msg, b_msg, "", "", "", "", ""]
                sheet.append_row(new_row)
                st.success(f"Записано! Ждем партнера ✨")
                send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, твоя очередь! ✨")


# ----------------- ВКЛАДКА 2: ДНЕВНИК -----------------
with tab2:
    sakura_happy = any(str(r.get('Дата')) == today_str and str(r.get('Ритуал')) == 'Ежедневный Дневник 🌸' and str(r.get('Дневник Лисички')) != "" and str(r.get('Дневник Мишки')) != "" for r in records)
    sakura_stage = 2 if s_streak >= 14 else 1
    sakura_mood = "happy" if sakura_happy else "sad"
    
    col_t2, col_img2, col_m2 = st.columns([2, 1, 1])
    with col_t2: st.title("🌸 Дневник")
    with col_img2: 
        try: st.image(f"sakura{sakura_stage}_{sakura_mood}.png", use_container_width=True)
        except Exception: st.info("🌸")
    with col_m2: st.metric("🌸 Серия", f"{s_streak} дн.")
    st.divider()

    # Ищем, заполнял ли я/партнер дневник сегодня
    match_diary_idx, my_diary_text, my_mood_emoji = None, "", "😁 Отличное"
    partner_diary_text, partner_mood_emoji = "", ""
    
    for i, row in enumerate(records):
        if str(row.get('Дата')) == today_str and str(row.get('Ритуал')) == 'Ежедневный Дневник 🌸':
            match_diary_idx = i + 2
            m_my_col, d_my_col = ('Настроение Лисички', 'Дневник Лисички') if current_user == "Лисичка 🦊" else ('Настроение Мишки', 'Дневник Мишки')
            m_p_col, d_p_col = ('Настроение Мишки', 'Дневник Мишки') if current_user == "Лисичка 🦊" else ('Настроение Лисички', 'Дневник Лисички')
            
            my_mood_emoji = str(row.get(m_my_col, '😁 Отличное'))
            if not my_mood_emoji: my_mood_emoji = "😁 Отличное"
            my_diary_text = str(row.get(d_my_col, ''))
            
            partner_mood_emoji = str(row.get(m_p_col, ''))
            partner_diary_text = str(row.get(d_p_col, ''))
            break

    # Логика отображения дневника партнера
    if partner_diary_text and my_diary_text:
        st.info(f"**Запись {partner} ({partner_mood_emoji}):**\n\n*{partner_diary_text}*")
    elif partner_diary_text and not my_diary_text:
        st.warning(f"🤫 {partner} уже заполнил(а) дневник сегодня! Напишите свою запись, чтобы увидеть её.")

    st.write("Ваша запись за сегодня (можно редактировать):")
    with st.form("diary_form"):
        mood_opts = ["😁 Отличное", "😌 Спокойное", "😐 Нормальное", "😔 Грустное", "😡 Злое"]
        idx_mood = mood_opts.index(my_mood_emoji) if my_mood_emoji in mood_opts else 0
        
        mood_emoji = st.selectbox("Ваше настроение:", mood_opts, index=idx_mood)
        diary_text = st.text_area("Что интересного случилось сегодня?", value=my_diary_text, height=100)
        
        if st.form_submit_button("🌸 Сохранить запись"):
            if not diary_text.strip():
                st.warning("Напишите хотя бы пару слов!")
            else:
                my_m_idx, my_d_idx = (8, 9) if current_user == "Лисичка 🦊" else (10, 11)
                
                # Отправляем уведомление, только если это первая запись за день
                if not my_diary_text:
                    send_telegram_message(f"🌸 <b>{current_user}</b> заполнил(а) дневник за сегодня! Зайди почитать и полей сакуру.")

                if match_diary_idx:
                    sheet.update_cell(match_diary_idx, my_m_idx, mood_emoji)
                    sheet.update_cell(match_diary_idx, my_d_idx, diary_text.strip())
                    st.success("Дневник обновлен!")
                    st.rerun() # Мгновенно перезагружаем страницу, чтобы показать запись партнера
                else:
                    new_row = [today_str, "Ежедневный Дневник 🌸", "❌", "❌", "❌", "", ""]
                    add_cols = [mood_emoji, diary_text.strip(), "", "", ""] if current_user == "Лисичка 🦊" else ["", "", mood_emoji, diary_text.strip(), ""]
                    sheet.append_row(new_row + add_cols)
                    st.success("Дневник сохранен! Ждем, когда партнер напишет свой.")
                    st.rerun()

# ----------------- ВКЛАДКА 3: КАПСУЛА -----------------
with tab3:
    st.title("📸 Капсула времени")
    st.write("Загружайте сюда лучшие моменты.")
    
    uploaded_file = st.file_uploader("Добавить фото к сегодняшнему дню", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        if st.button("💾 Сохранить в облако"):
            with st.spinner("Отправляем в Google Drive..."):
                file_url, err = upload_to_drive(uploaded_file.getvalue(), f"{today_str}_{uploaded_file.name}", g_creds)
                if file_url:
                    match_idx = None
                    for i, row in enumerate(records):
                        if str(row.get('Дата')) == today_str and str(row.get('Ритуал')) != 'Ежедневный Дневник 🌸':
                            match_idx = i + 2
                            break
                    if match_idx: sheet.update_cell(match_idx, 12, file_url)
                    else: sheet.append_row([today_str, "📸 Фото на память", "✅", "✅", "✅", "", "", "", "", "", "", file_url])
                    st.success("Фотография успешно сохранена!")
                    st.balloons()
                else:
                    st.error(f"Ошибка загрузки. Проверьте, включен ли Google Drive API. Лог: {err}")

    st.divider()
    st.subheader("🖼 Наша Галерея")
    has_photos = False
    for row in reversed(records):
        photo_url = str(row.get('Фото', ''))
        if photo_url and photo_url.startswith("http"):
            has_photos = True
            st.write(f"**{row.get('Дата', '')}** — {row.get('Ритуал', '')}")
            st.image(photo_url, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
    if not has_photos: st.info("Ваша капсула пока пуста.")

# ----------------- ВКЛАДКА 4: СТАТИСТИКА -----------------
with tab4:
    # ИСПРАВЛЕНИЕ: таблица истории адаптирована под мобилки (без индексов, широкая)
    st.subheader("📖 История ритуалов")
    if records:
        df_hist = pd.DataFrame(records).iloc[::-1]
        # Оставляем только нужные колонки для мобильного
        cols_to_show = ['Дата', 'Ритуал', 'Лисичка 🦊', 'Мишка 🐻', 'Вместе ✨']
        df_display = df_hist[[c for c in cols_to_show if c in df_hist.columns]]
        # Скрываем дневники из этой таблицы
        df_display = df_display[df_display['Ритуал'] != 'Ежедневный Дневник 🌸']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    st.divider()
    
    if records:
        df_stats = pd.DataFrame(records)
        df_stats['Дата'] = pd.to_datetime(df_stats['Дата'])
        df_joint = df_stats[(df_stats['Вместе ✨'] == '✅') & (df_stats['Ритуал'] != 'Ежедневный Дневник 🌸')]
        
        if not df_joint.empty:
            st.subheader("🏆 Любимые ритуалы")
            ritual_counts = df_joint['Ритуал'].value_counts().reset_index()
            ritual_counts.columns = ['Ритуал', 'Дней']
            
            # ИСПРАВЛЕНИЕ: Точные целые шаги на Y-оси
            max_days = int(ritual_counts['Дней'].max())
            tick_vals = list(range(max_days + 1))
            
            bar_chart = alt.Chart(ritual_counts).mark_bar(color='#9370DB', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X('Ритуал:N', title='', sort='-y', axis=alt.Axis(labelAngle=0)), 
                y=alt.Y('Дней:Q', title='Дней выполнено', axis=alt.Axis(values=tick_vals, format='d')), 
                tooltip=['Ритуал', 'Дней']
            ).properties(height=350)
            st.altair_chart(bar_chart, use_container_width=True)

            st.divider()
            st.subheader("🔥 Тепловая карта ритуалов")
            heatmap_data = df_joint.groupby('Дата').size().reset_index(name='Количество')
            heat_chart = alt.Chart(heatmap_data).mark_rect(cornerRadius=3).encode(
                x=alt.X('date(Дата):O', title='День'),
                y=alt.Y('month(Дата):N', title='Месяц'),
                color=alt.Color('Количество:Q', scale=alt.Scale(scheme='purples'), legend=None),
                tooltip=[alt.Tooltip('Дата:T', title='Дата', format='%Y-%m-%d'), alt.Tooltip('Количество:Q', title='Ритуалов')]
            ).properties(height=200)
            st.altair_chart(heat_chart, use_container_width=True)
