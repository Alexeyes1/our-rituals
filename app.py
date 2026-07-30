import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
import altair as alt
import os
import time

# --- СОЗДАНИЕ ПАПКИ ДЛЯ ФОТО НА СЕРВЕРЕ ---
if not os.path.exists("capsule_photos"):
    os.makedirs("capsule_photos")

# --- ФУНКЦИИ ---
def send_telegram_message(text):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception:
        pass 

def get_streaks(records):
    if not records: return 0, 0
    df = pd.DataFrame(records)
    r_streak, s_streak = 0, 0
    sys_rituals = ['Ежедневный Дневник 🌸', 'Ежедневное Послание 💌', '📸 Фото на память']
    
    if 'Вместе ✨' in df.columns:
        df_rituals = df[(df['Вместе ✨'] == '✅') & (~df['Ритуал'].isin(sys_rituals))]
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

# --- НАСТРОЙКИ UI (ТОЛЬКО ТЕМНАЯ ТЕМА) ---
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

bg_color, text_color, input_bg = "#000000", "#ffffff", "#111111"

st.markdown(f"""
    <style>
    .stApp, .stApp > header {{ background-color: {bg_color} !important; }}
    h1, h2, h3, p, label, span, li, .stMetric label {{ color: {text_color} !important; font-family: 'Arial', sans-serif; }}
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {{
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
    [data-testid="stImage"] img {{ animation: breathe 4s ease-in-out infinite; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.4); }}
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
sys_rituals = ['Ежедневный Дневник 🌸', 'Ежедневное Послание 💌', '📸 Фото на память']

st.sidebar.title("⚙️ Настройки")
st.sidebar.write(f"Профиль: **{current_user}**")
if st.sidebar.button("Сменить профиль"): st.query_params.pop("user", None); st.rerun()

@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["json_key"])
    credentials = Credentials.from_service_account_info(key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(credentials)

try:
    client = init_connection()
    sheet = client.open("Наши ритуалы").sheet1 
    records = sheet.get_all_records()
except Exception as e:
    st.error(f"Ошибка базы данных: {e}")
    st.stop()

r_streak, s_streak = get_streaks(records)
today_date_obj = datetime.now().date()
today_str = today_date_obj.strftime("%Y-%m-%d")

# ================= Вкладки =================
tab1, tab2, tab3, tab4 = st.tabs(["📝 Ритуалы", "🌸 Дневник", "📸 Капсула", "📊 Стат."])

# ----------------- ВКЛАДКА 1: РИТУАЛЫ -----------------
with tab1:
    has_done_ritual_today = any(str(r.get('Дата')) == today_str and str(r.get('Ритуал')) not in sys_rituals and str(r.get(current_user)) == '✅' for r in records)
    pet_happy = any(str(r.get('Дата')) == today_str and str(r.get('Вместе ✨')) == '✅' and str(r.get('Ритуал')) not in sys_rituals for r in records)
    
    pet_stage = 2 if r_streak >= 14 else 1
    pet_mood = "happy" if pet_happy else "sad"
    
    col_t, col_img, col_m = st.columns([2, 1, 1])
    with col_t: st.title("✨ Ритуалы")
    with col_img: 
        try: st.image(f"stage{pet_stage}_{pet_mood}.png", use_container_width=True)
        except Exception: st.info("🐣")
    with col_m: st.metric("🔥 Серия", f"{r_streak} дн.")
    st.divider()

    # --- ЛОГИКА ЕЖЕДНЕВНОГО ПОСЛАНИЯ ---
    msg_match_idx, my_msg_today, partner_msg_today = None, "", ""
    for i, row in enumerate(records):
        if str(row.get('Дата')) == today_str and str(row.get('Ритуал')) == 'Ежедневное Послание 💌':
            msg_match_idx = i + 2
            my_col = 'Послание Лисички' if current_user == "Лисичка 🦊" else 'Послание Мишки'
            p_col = 'Послание Мишки' if current_user == "Лисичка 🦊" else 'Послание Лисички'
            my_msg_today = str(row.get(my_col, '')).strip()
            partner_msg_today = str(row.get(p_col, '')).strip()
            break

    if has_done_ritual_today:
        st.subheader("💌 Послание дня (1 раз в день)")
        if partner_msg_today:
            st.info(f"**От {partner}:**\n\n*{partner_msg_today}*")
        else:
            st.write(f"*{partner} пока не оставил(а) послание на сегодня.*")
        
        with st.form("daily_message_form"):
            new_msg = st.text_area("Ваше послание партнеру:", value=my_msg_today, placeholder="Теплые слова на сегодня...")
            if st.form_submit_button("Сохранить послание 💌"):
                if new_msg.strip() != my_msg_today:
                    if msg_match_idx:
                        col_idx = 6 if current_user == "Лисичка 🦊" else 7
                        sheet.update_cell(msg_match_idx, col_idx, new_msg.strip())
                    else:
                        f_msg = new_msg.strip() if current_user == "Лисичка 🦊" else ""
                        b_msg = new_msg.strip() if current_user == "Мишка 🐻" else ""
                        sheet.append_row([today_str, "Ежедневное Послание 💌", "❌", "❌", "❌", f_msg, b_msg, "", "", "", "", ""])
                    
                    send_telegram_message(f"💌 <b>{current_user}</b> оставил(а) тебе послание дня! Зайди почитать.")
                    st.success("✅ Послание успешно сохранено!")
                    time.sleep(1.5) # Пауза, чтобы увидеть уведомление
                    st.rerun()
                else:
                    st.warning("Текст послания не изменился.")
    else:
        st.info("🔒 Выполните хотя бы один ритуал ниже, чтобы увидеть послание партнера и оставить своё!")

    st.divider()

    # --- ОТМЕТКА РИТУАЛОВ ---
    base_rituals = ["🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога", "🎮 Совместные игры"]
    history_rituals = [str(r['Ритуал']) for r in records if r.get('Ритуал') and str(r.get('Ритуал')) not in sys_rituals]
    all_rituals = sorted(list(set(base_rituals + history_rituals)))

    st.subheader("📝 Отметить ритуал")
    with st.form("habit_form"):
        date_input = st.text_input("Дата", value=today_str)
        selected_ritual = st.selectbox("Что выполнили?", all_rituals)
        custom_ritual = st.text_input("ИЛИ новый ритуал:")
        
        if st.form_submit_button("Я выполнил(а)! Сохранить ✨"):
            final_ritual = custom_ritual.strip() if custom_ritual.strip() else selected_ritual
            match_idx, existing_fox, existing_bear = None, "❌", "❌"
            
            for i, row in enumerate(records):
                if str(row.get('Дата')) == date_input and str(row.get('Ритуал')) == final_ritual:
                    match_idx = i + 2
                    existing_fox = row.get('Лисичка 🦊', '❌')
                    existing_bear = row.get('Мишка 🐻', '❌')
                    break

            if match_idx:
                new_fox = "✅" if current_user == "Лисичка 🦊" else existing_fox
                new_bear = "✅" if current_user == "Мишка 🐻" else existing_bear
                new_together = "✅" if (new_fox == "✅" and new_bear == "✅") else "❌"
                
                sheet.update_cell(match_idx, 3, new_fox)
                sheet.update_cell(match_idx, 4, new_bear)
                sheet.update_cell(match_idx, 5, new_together)
                
                if new_together == "✅":
                    st.success(f"Ого! Галочка ВМЕСТЕ получена! 🎉")
                    st.balloons()
                    time.sleep(1.5)
                else:
                    st.success("Отлично! Данные обновлены. Ждем партнера ✨")
                    time.sleep(1.5)
            else:
                new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
                new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
                
                sheet.append_row([date_input, final_ritual, new_fox, new_bear, "❌", "", "", "", "", "", "", ""])
                st.success(f"Записано! Ждем партнера ✨")
                send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, твоя очередь! ✨")
                time.sleep(1.5)
            st.rerun()

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

    diary_date_obj = st.date_input("Выберите день для чтения или записи:", value=today_date_obj, max_value=today_date_obj)
    diary_date_str = diary_date_obj.strftime("%Y-%m-%d")
    is_today = (diary_date_obj == today_date_obj)

    match_diary_idx, my_diary_text, my_mood_emoji = None, "", "😁 Отличное"
    partner_diary_text, partner_mood_emoji = "", ""
    
    for i, row in enumerate(records):
        if str(row.get('Дата')) == diary_date_str and str(row.get('Ритуал')) == 'Ежедневный Дневник 🌸':
            match_diary_idx = i + 2
            m_my_col, d_my_col = ('Настроение Лисички', 'Дневник Лисички') if current_user == "Лисичка 🦊" else ('Настроение Мишки', 'Дневник Мишки')
            m_p_col, d_p_col = ('Настроение Мишки', 'Дневник Мишки') if current_user == "Лисичка 🦊" else ('Настроение Лисички', 'Дневник Лисички')
            
            my_mood_emoji = str(row.get(m_my_col, '😁 Отличное')) or "😁 Отличное"
            my_diary_text = str(row.get(d_my_col, ''))
            
            partner_mood_emoji = str(row.get(m_p_col, ''))
            partner_diary_text = str(row.get(d_p_col, ''))
            break

    if partner_diary_text and my_diary_text:
        st.markdown(f"📌 **Статус за {diary_date_str}:** 🟢 *Заполнен обоими!*")
    elif partner_diary_text or my_diary_text:
        st.markdown(f"📌 **Статус за {diary_date_str}:** 🟡 *Заполнен частично*")
    else:
        st.markdown(f"📌 **Статус за {diary_date_str}:** ⚪️ *Еще не заполнен*")
    st.divider()

    if not is_today:
        st.info("📜 **Архивная запись (Только чтение)**: Прошлые дни нельзя редактировать.")
        if partner_diary_text:
            st.markdown(f"**Запись {partner} ({partner_mood_emoji}):**\n\n*{partner_diary_text}*")
        else:
            st.write(f"*{partner} не заполнял(а) дневник в этот день.*")
            
        st.divider()
        if my_diary_text:
            st.markdown(f"**Ваша запись ({my_mood_emoji}):**\n\n*{my_diary_text}*")
        else:
            st.write("*Вы не заполняли дневник в этот день.*")
    else:
        if partner_diary_text and my_diary_text:
            st.info(f"**Запись {partner} ({partner_mood_emoji}):**\n\n*{partner_diary_text}*")
            st.divider()
            st.success(f"**Ваша запись за сегодня ({my_mood_emoji}):**\n\n*{my_diary_text}*")
        elif partner_diary_text and not my_diary_text:
            st.warning(f"🤫 {partner} уже заполнил(а) дневник сегодня! Напишите свою запись ниже, чтобы прочитать её.")

        st.write("Ваша запись за сегодня (можно редактировать до конца дня):")
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
                    if not my_diary_text: send_telegram_message(f"🌸 <b>{current_user}</b> заполнил(а) дневник за сегодня! Зайди почитать.")
                    
                    if match_diary_idx:
                        sheet.update_cell(match_diary_idx, my_m_idx, mood_emoji)
                        sheet.update_cell(match_diary_idx, my_d_idx, diary_text.strip())
                    else:
                        new_row = [today_str, "Ежедневный Дневник 🌸", "❌", "❌", "❌", "", ""]
                        add_cols = [mood_emoji, diary_text.strip(), "", "", ""] if current_user == "Лисичка 🦊" else ["", "", mood_emoji, diary_text.strip(), ""]
                        sheet.append_row(new_row + add_cols)
                    
                    st.success("✅ Дневник успешно сохранен!")
                    time.sleep(1.5)
                    st.rerun()

# ----------------- ВКЛАДКА 3: КАПСУЛА -----------------
with tab3:
    st.title("📸 Капсула времени")
    st.write("Фотографии сохраняются прямо на вашем личном сервере (VPS)!")
    
    uploaded_file = st.file_uploader("Добавить фото к сегодняшнему дню", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        if st.button("💾 Сохранить надежно"):
            with st.spinner("Сохраняем на сервере..."):
                file_ext = uploaded_file.name.split('.')[-1]
                safe_filename = f"{today_str}_{datetime.now().strftime('%H%M%S')}.{file_ext}"
                local_filepath = os.path.join("capsule_photos", safe_filename)
                
                with open(local_filepath, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                match_idx = None
                for i, row in enumerate(records):
                    if str(row.get('Дата')) == today_str and str(row.get('Ритуал')) not in sys_rituals:
                        match_idx = i + 2
                        break
                if match_idx: sheet.update_cell(match_idx, 12, local_filepath)
                else: sheet.append_row([today_str, "📸 Фото на память", "✅", "✅", "✅", "", "", "", "", "", "", local_filepath])
                
                st.success("✅ Фотография успешно сохранена на вашем сервере!")
                st.balloons()
                time.sleep(2)
                st.rerun()

    st.divider()
    has_photos = False
    for row in reversed(records):
        photo_url = str(row.get('Фото', ''))
        if photo_url:
            has_photos = True
            st.write(f"**{row.get('Дата', '')}** — {row.get('Ритуал', '')}")
            try:
                st.image(photo_url, use_container_width=True)
            except Exception:
                st.error("Фото не найдено на сервере.")
            st.markdown("<br>", unsafe_allow_html=True)
            
    if not has_photos: st.info("Ваша капсула пока пуста.")

# ----------------- ВКЛАДКА 4: СТАТИСТИКА -----------------
with tab4:
    st.subheader("📖 История ритуалов")
    if records:
        df_hist = pd.DataFrame(records).iloc[::-1]
        cols_to_show = ['Дата', 'Ритуал', 'Лисичка 🦊', 'Мишка 🐻', 'Вместе ✨']
        df_display = df_hist[[c for c in cols_to_show if c in df_hist.columns]]
        df_display = df_display[~df_display['Ритуал'].isin(sys_rituals)]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    st.divider()
    
    if records:
        df_stats = pd.DataFrame(records)
        df_stats['Дата'] = pd.to_datetime(df_stats['Дата'])
        df_joint = df_stats[(df_stats['Вместе ✨'] == '✅') & (~df_stats['Ритуал'].isin(sys_rituals))]
        
        if not df_joint.empty:
            st.subheader("🏆 Любимые ритуалы")
            ritual_counts = df_joint['Ритуал'].value_counts().reset_index()
            ritual_counts.columns = ['Ритуал', 'Дней']
            
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
