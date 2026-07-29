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

# --- ФУНКЦИИ ИНТЕГРАЦИИ ---
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
    file_id = r.json().get('id')
    
    if file_id:
        requests.post(f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions", 
            headers={"Authorization": "Bearer " + credentials.token, "Content-Type": "application/json"},
            json={"role": "reader", "type": "anyone"})
        return f"https://drive.google.com/uc?id={file_id}"
    return None

def get_streaks(records):
    if not records: return 0, 0
    df = pd.DataFrame(records)
    
    # Стрик Ритуалов
    ritual_streak = 0
    if 'Вместе ✨' in df.columns:
        df_rituals = df[(df['Вместе ✨'] == '✅') & (df['Ритуал'] != 'Ежедневный Дневник 🌸')]
        if not df_rituals.empty:
            df_rituals['Дата'] = pd.to_datetime(df_rituals['Дата']).dt.date
            dates = sorted(df_rituals['Дата'].unique(), reverse=True)
            today = datetime.now().date()
            if dates[0] == today or dates[0] == (today - timedelta(days=1)):
                ritual_streak = 1
                curr = dates[0]
                for d in dates[1:]:
                    if d == curr - timedelta(days=1):
                        ritual_streak += 1; curr = d
                    else: break
                    
    # Стрик Дневников (Сакуры) - только когда оба заполнили!
    sakura_streak = 0
    if 'Дневник Лисички' in df.columns and 'Дневник Мишки' in df.columns:
        df_diary = df[(df['Ритуал'] == 'Ежедневный Дневник 🌸') & (df['Дневник Лисички'] != '') & (df['Дневник Мишки'] != '')]
        if not df_diary.empty:
            df_diary['Дата'] = pd.to_datetime(df_diary['Дата']).dt.date
            dates_s = sorted(df_diary['Дата'].unique(), reverse=True)
            today = datetime.now().date()
            if dates_s[0] == today or dates_s[0] == (today - timedelta(days=1)):
                sakura_streak = 1
                curr_s = dates_s[0]
                for d in dates_s[1:]:
                    if d == curr_s - timedelta(days=1):
                        sakura_streak += 1; curr_s = d
                    else: break
    return ritual_streak, sakura_streak

# --- НАСТРОЙКА СТРАНИЦЫ И ТЕМЫ ---
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
    .stTabs [data-baseweb="tab-list"] button {{ color: {text_color} !important; font-size: 1.1rem !important; padding: 10px 15px !important; }}
    
    @keyframes breathe {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} 100% {{ transform: scale(1); }} }}
    [data-testid="stImage"] img {{ animation: breathe 4s ease-in-out infinite; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.2); }}
    </style>
""", unsafe_allow_html=True)

# --- АВТОРИЗАЦИЯ И БАЗА ---
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

# ================= ГЛАВНОЕ МЕНЮ (4 ВКЛАДКИ) =================
tab1, tab2, tab3, tab4 = st.tabs(["📝 Ритуалы", "🌸 Дневник", "📸 Капсула", "📊 Статистика"])

# ----------------- ВКЛАДКА 1: РИТУАЛЫ И ПИТОМЕЦ -----------------
with tab1:
    # Питомец счастлив ТОЛЬКО если есть хотя бы 1 ритуал сегодня ВМЕСТЕ
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
        secret_message = st.text_area("💌 Тайное послание партнеру (необязательно):", placeholder="Партнер увидит, когда тоже выполнит этот ритуал...")
        
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
            
            if match_idx:
                new_fox = "✅" if current_user == "Лисичка 🦊" else existing_fox
                new_bear = "✅" if current_user == "Мишка 🐻" else existing_bear
                new_together = "✅" if (new_fox == "✅" and new_bear == "✅") else "❌"
                
                sheet.update_cell(match_idx, 3, new_fox)
                sheet.update_cell(match_idx, 4, new_bear)
                sheet.update_cell(match_idx, 5, new_together)
                my_col_idx = 6 if current_user == "Лисичка 🦊" else 7
                if secret_message.strip(): sheet.update_cell(match_idx, my_col_idx, secret_message.strip())
                
                if new_together == "✅":
                    st.balloons()
                    st.success(f"Ого! Галочка ВМЕСТЕ получена! 🎉")
                    if partner_msg:
                        st.info(f"💌 **Послание от {partner}:**\n\n*{partner_msg}*")
                        send_telegram_message(f"💌 <b>Тайное послание прочитано!</b> {current_user} увидел(а) твою записку.")
                else:
                    st.success("Отлично! Ждем партнера ✨")
            else:
                new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
                new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
                f_msg = secret_message.strip() if current_user == "Лисичка 🦊" else ""
                b_msg = secret_message.strip() if current_user == "Мишка 🐻" else ""
                
                # Дополняем пустыми строками для 12 колонок!
                new_row = [date_input, final_ritual, new_fox, new_bear, "❌", f_msg, b_msg, "", "", "", "", ""]
                sheet.append_row(new_row)
                st.success(f"Записано! Ждем партнера ✨")
                send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, твоя очередь! ✨")


# ----------------- ВКЛАДКА 2: ДНЕВНИК И САКУРА -----------------
with tab2:
    # Сакура счастлива ТОЛЬКО если оба дневника заполнены сегодня
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

    st.write("Как прошел ваш день? Заполните дневник, чтобы полить Сакуру.")
    with st.form("diary_form"):
        mood_emoji = st.selectbox("Ваше настроение:", ["😁 Отличное", "😌 Спокойное", "😐 Нормальное", "😔 Грустное", "😡 Злое"])
        diary_text = st.text_area("Что интересного случилось сегодня?", height=100)
        
        if st.form_submit_button("🌸 Сохранить запись"):
            if not diary_text.strip():
                st.warning("Напишите хотя бы пару слов!")
            else:
                match_idx, partner_diary, partner_mood = None, "", ""
                for i, row in enumerate(records):
                    if str(row.get('Дата')) == today_str and str(row.get('Ритуал')) == 'Ежедневный Дневник 🌸':
                        match_idx = i + 2
                        m_col, d_col = ('Настроение Мишки', 'Дневник Мишки') if partner == "Мишка 🐻" else ('Настроение Лисички', 'Дневник Лисички')
                        partner_mood, partner_diary = str(row.get(m_col, '')), str(row.get(d_col, ''))
                        break
                
                my_m_idx, my_d_idx = (8, 9) if current_user == "Лисичка 🦊" else (10, 11)
                
                if match_idx:
                    sheet.update_cell(match_idx, my_m_idx, mood_emoji)
                    sheet.update_cell(match_idx, my_d_idx, diary_text.strip())
                    st.success("Дневник обновлен!")
                    if partner_diary:
                        st.info(f"**Запись {partner} ({partner_mood}):**\n\n*{partner_diary}*")
                else:
                    new_row = [today_str, "Ежедневный Дневник 🌸", "❌", "❌", "❌", "", ""]
                    # Добавляем настроение и текст в правильные колонки
                    add_cols = [mood_emoji, diary_text.strip(), "", "", ""] if current_user == "Лисичка 🦊" else ["", "", mood_emoji, diary_text.strip(), ""]
                    sheet.append_row(new_row + add_cols)
                    st.success("Дневник сохранен! Ждем, когда партнер напишет свой.")
                    send_telegram_message(f"🌸 <b>{current_user}</b> заполнил(а) дневник за сегодня! Зайди почитать и полей сакуру.")


# ----------------- ВКЛАДКА 3: КАПСУЛА ВРЕМЕНИ -----------------
with tab3:
    st.title("📸 Капсула времени")
    st.write("Загружайте сюда лучшие моменты. Они навсегда останутся в вашей истории!")
    
    uploaded_file = st.file_uploader("Добавить фото к сегодняшнему дню", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        if st.button("💾 Сохранить в облако"):
            with st.spinner("Отправляем в Google Drive..."):
                file_url = upload_to_drive(uploaded_file.getvalue(), f"{today_str}_{uploaded_file.name}", g_creds)
                if file_url:
                    # Ищем любую сегодняшнюю запись, чтобы прикрепить фото. Если нет - создаем пустую
                    match_idx = None
                    for i, row in enumerate(records):
                        if str(row.get('Дата')) == today_str and str(row.get('Ритуал')) != 'Ежедневный Дневник 🌸':
                            match_idx = i + 2
                            break
                    if match_idx:
                        sheet.update_cell(match_idx, 12, file_url)
                    else:
                        sheet.append_row([today_str, "📸 Фото на память", "✅", "✅", "✅", "", "", "", "", "", "", file_url])
                    st.success("Фотография успешно сохранена в вашей капсуле!")
                    st.balloons()
                else:
                    st.error("Не удалось загрузить фото. Проверьте права папки в Google Drive.")

    st.divider()
    st.subheader("🖼 Наша Галерея")
    has_photos = False
    # Перебираем историю с конца, чтобы новые фото были сверху
    for row in reversed(records):
        photo_url = str(row.get('Фото', ''))
        if photo_url and photo_url.startswith("http"):
            has_photos = True
            date = row.get('Дата', 'Неизвестно')
            event = row.get('Ритуал', 'Фотография')
            st.write(f"**{date}** — {event}")
            st.image(photo_url, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
    if not has_photos:
        st.info("Ваша капсула пока пуста. Загрузите ваше первое совместное фото!")


# ----------------- ВКЛАДКА 4: СТАТИСТИКА -----------------
with tab4:
    if records:
        df_stats = pd.DataFrame(records)
        df_stats['Дата'] = pd.to_datetime(df_stats['Дата'])
        df_joint = df_stats[(df_stats['Вместе ✨'] == '✅') & (df_stats['Ритуал'] != 'Ежедневный Дневник 🌸')]
        
        if not df_joint.empty:
            st.subheader("🏆 Любимые ритуалы")
            ritual_counts = df_joint['Ритуал'].value_counts().reset_index()
            ritual_counts.columns = ['Ритуал', 'Дней']
            bar_chart = alt.Chart(ritual_counts).mark_bar(color='#9370DB', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X('Ритуал:N', title='', sort='-y', axis=alt.Axis(labelAngle=0)), 
                y=alt.Y('Дней:Q', title='Дней выполнено', axis=alt.Axis(tickMinStep=1, format='d')), 
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
        else:
            st.info("Выполните хотя бы один совместный ритуал, чтобы увидеть аналитику!")
