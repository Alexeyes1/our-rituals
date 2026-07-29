import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
import altair as alt

# --- ФУНКЦИЯ ДЛЯ ТЕЛЕГРАМА ---
def send_telegram_message(text):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except Exception:
        pass # Игнорируем ошибки, чтобы приложение не ломалось

# --- ФУНКЦИЯ ПОДСЧЕТА СТРИКА (СЕРИИ) ---
def get_streak(records):
    if not records: return 0
    df = pd.DataFrame(records)
    df_together = df[df['Вместе ✨'] == '✅']
    if df_together.empty: return 0
    
    df_together['Дата'] = pd.to_datetime(df_together['Дата']).dt.date
    dates = sorted(df_together['Дата'].unique(), reverse=True)
    
    today = datetime.now().date()
    # Если последняя отметка была не сегодня и не вчера, серия прервалась
    if dates[0] != today and dates[0] != (today - timedelta(days=1)):
        return 0
        
    streak = 1
    curr = dates[0]
    for d in dates[1:]:
        if d == curr - timedelta(days=1):
            streak += 1
            curr = d
        else:
            break
    return streak


# 1. Настройка страницы
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

# --- 2. СТРОГИЙ ЧБ ДИЗАЙН ---
if "theme" not in st.query_params:
    st.query_params["theme"] = "dark" 

st.sidebar.title("⚙️ Настройки")
theme_choice = st.sidebar.radio(
    "Оформление:", 
    ["Темная тема 🌙", "Светлая тема ☀️"], 
    index=0 if st.query_params["theme"] == "dark" else 1
)

if theme_choice == "Темная тема 🌙":
    st.query_params["theme"] = "dark"
    bg_color = "#000000"
    text_color = "#ffffff"
    input_bg = "#111111"
else:
    st.query_params["theme"] = "light"
    bg_color = "#ffffff"
    text_color = "#000000"
    input_bg = "#f9f9f9"

st.markdown(f"""
    <style>
    .stApp, .stApp > header {{ background-color: {bg_color} !important; }}
    h1, h2, h3, p, label, span, li, .stMetric label {{ color: {text_color} !important; font-family: 'Arial', sans-serif; }}
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        background-color: {input_bg} !important; color: {text_color} !important; border: 1px solid {text_color} !important;
    }}
    .stTextInput input::placeholder {{ color: {text_color} !important; opacity: 0.5 !important; }}
    div[data-baseweb="popover"] > div, ul[role="listbox"] {{ background-color: {input_bg} !important; }}
    li[role="option"]:hover {{ background-color: {text_color} !important; color: {bg_color} !important; }}
    div[data-testid="stFormSubmitButton"] button {{ background-color: {text_color} !important; border: 2px solid {text_color} !important; }}
    div[data-testid="stFormSubmitButton"] button p {{ color: {bg_color} !important; font-weight: bold !important; }}
    div[data-testid="stFormSubmitButton"] button:hover {{ opacity: 0.8; }}
    svg {{ fill: {text_color} !important; }}
    .stTabs [data-baseweb="tab-list"] button {{ color: {text_color} !important; }}
    </style>
""", unsafe_allow_html=True)


# --- 3. ПРОФИЛИ ---
if "user" not in st.query_params:
    st.title("Привет! Кто ты? 👋")
    col1, col2 = st.columns(2)
    if col1.button("Я Лисичка 🦊", use_container_width=True):
        st.query_params["user"] = "fox"
        st.rerun()
    if col2.button("Я Мишка 🐻", use_container_width=True):
        st.query_params["user"] = "bear"
        st.rerun()
    st.stop()

user_code = st.query_params["user"]
current_user = "Лисичка 🦊" if user_code == "fox" else "Мишка 🐻"
partner = "Мишка 🐻" if user_code == "fox" else "Лисичка 🦊"

st.sidebar.write(f"Профиль: **{current_user}**")
if st.sidebar.button("Сменить профиль"):
    st.query_params.pop("user", None)
    st.rerun()


# --- 4. ПОДКЛЮЧЕНИЕ К БАЗЕ И ДАННЫЕ ---
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["json_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(credentials)

try:
    client = init_connection()
    sheet = client.open("Наши ритуалы").sheet1 
    records = sheet.get_all_records()
except Exception as e:
    st.error(f"Ошибка базы данных: {e}")
    st.stop()

current_streak = get_streak(records)

# --- ВЕРХНЯЯ ЧАСТЬ ЭКРАНА ---
col_title, col_streak = st.columns([3, 1])
with col_title:
    st.title("✨ Наши Ритуалы")
with col_streak:
    # Красивый вывод серии дней подряд
    st.metric(label="Дней подряд", value=f"🔥 {current_streak}")
st.divider()

# Разделяем на 2 вкладки: Трекер и Статистика
tab1, tab2 = st.tabs(["📝 Трекер", "📊 Статистика"])

# ================= Вкладка 1: ТРЕКЕР =================
with tab1:
    base_rituals = ["🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога", "🎮 Совместные игры"]
    history_rituals = [str(row['Ритуал']) for row in records if row.get('Ритуал')]
    all_rituals = list(set(base_rituals + history_rituals))
    all_rituals.sort()

    with st.form("habit_form"):
        today = datetime.now().strftime("%Y-%m-%d")
        date_input = st.text_input("Дата", value=today)
        selected_ritual = st.selectbox("Что выполнили?", all_rituals)
        custom_ritual = st.text_input("ИЛИ впишите новый ритуал:", placeholder="Например: Посмотрели фильм 🍿")
        submitted = st.form_submit_button("Я выполнил(а)! Сохранить ✨")
        
        if submitted:
            raw_ritual = custom_ritual.strip()
            if raw_ritual:
                parts = raw_ritual.split()
                if len(parts) > 1 and ord(parts[-1][0]) > 10000:
                    emoji = parts.pop()
                    final_ritual = f"{emoji} {' '.join(parts)}"
                else:
                    final_ritual = raw_ritual
            else:
                final_ritual = selected_ritual
                
            match_idx = None
            existing_fox = "❌"
            existing_bear = "❌"
            
            for i, row in enumerate(records):
                if str(row.get('Дата', '')) == date_input and str(row.get('Ритуал', '')) == final_ritual:
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
                    st.balloons()
                    
                    # ПРОВЕРЯЕМ НОВЫЙ СТРИК И НАГРАДЫ
                    new_records = sheet.get_all_records()
                    new_streak = get_streak(new_records)
                    
                    # Если кратно 7 дням (7, 14, 21...)
                    if new_streak > 0 and new_streak % 7 == 0:
                        # Чередуем: 1 неделя - Лисичка, 2 - Мишка, 3 - Лисичка и тд.
                        chooser = "Лисичка 🦊" if (new_streak // 7) % 2 != 0 else "Мишка 🐻"
                        reward_msg = f"🏆 <b>Ура, вы разблокировали награду!</b>\nНепрерывное занятие {new_streak} дней!\n\nНа этих выходных награду выбирает: <b>{chooser}</b>!"
                        st.success(reward_msg.replace('<b>', '**').replace('</b>', '**'))
                        send_telegram_message(reward_msg)
                    else:
                        st.success(f"Ого! {partner} тоже выполнил(а) это. Галочка ВМЕСТЕ получена! 🎉")
                        send_telegram_message(f"🎉 <b>Ура!</b> Вы оба выполнили: <b>{final_ritual}</b>!\nГалочка ВМЕСТЕ получена! ✨\n🔥 Ваша серия: {new_streak} дней!")
                else:
                    st.success("Отлично! Галочка поставлена. Ждем партнера ✨")
                    send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, теперь твоя очередь! ✨")
            else:
                new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
                new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
                sheet.append_row([date_input, final_ritual, new_fox, new_bear, "❌"])
                st.success(f"Записано в историю! Ждем партнера ✨")
                send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, теперь твоя очередь! ✨")

    st.subheader("📖 Наша история")
    if records:
        df_hist = pd.DataFrame(records).iloc[::-1]
        st.dataframe(df_hist, use_container_width=True)


# ================= Вкладка 2: СТАТИСТИКА =================
with tab2:
    if records:
        df_stats = pd.DataFrame(records)
        df_stats['Дата'] = pd.to_datetime(df_stats['Дата'])
        df_joint = df_stats[df_stats['Вместе ✨'] == '✅']
        
        if not df_joint.empty:
            st.subheader("🏆 Любимые ритуалы")
            st.write("Сколько дней мы соблюдали каждую привычку вместе:")
            # Столбчатая диаграмма
            ritual_counts = df_joint['Ритуал'].value_counts().reset_index()
            ritual_counts.columns = ['Ритуал', 'Дней']
            
            bar_chart = alt.Chart(ritual_counts).mark_bar(color='#9370DB').encode(
                x=alt.X('Дней:Q', title='Дней выполнено'),
                y=alt.Y('Ритуал:N', sort='-x', title=''),
                tooltip=['Ритуал', 'Дней']
            ).properties(height=300)
            st.altair_chart(bar_chart, use_container_width=True)

            st.divider()
            
            st.subheader("🔥 Тепловая карта")
            st.write("Интенсивность наших совместных ритуалов по дням:")
            # Данные для тепловой карты
            heatmap_data = df_joint.groupby('Дата').size().reset_index(name='Количество')
            
            heat_chart = alt.Chart(heatmap_data).mark_rect(rx=3, ry=3, stroke=bg_color, strokeWidth=2).encode(
                x=alt.X('date(Дата):O', title='День месяца'),
                y=alt.Y('month(Дата):N', title='Месяц'),
                color=alt.Color('Количество:Q', scale=alt.Scale(scheme='purples'), legend=None),
                tooltip=[alt.Tooltip('Дата:T', title='Дата', format='%Y-%m-%d'), alt.Tooltip('Количество:Q', title='Ритуалов выполнено')]
            ).properties(height=200)
            st.altair_chart(heat_chart, use_container_width=True)
            
        else:
            st.info("Здесь появится красивая аналитика, как только вы выполните первый ритуал ВМЕСТЕ! ✨")
    else:
        st.info("История пока пуста. Пора создавать традиции!")
