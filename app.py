import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
import altair as alt

def send_telegram_message(text):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except Exception:
        pass 

def get_streak(records):
    if not records: return 0
    df = pd.DataFrame(records)
    if 'Вместе ✨' not in df.columns: return 0
    df_together = df[df['Вместе ✨'] == '✅']
    if df_together.empty: return 0
    
    df_together['Дата'] = pd.to_datetime(df_together['Дата']).dt.date
    dates = sorted(df_together['Дата'].unique(), reverse=True)
    
    today = datetime.now().date()
    if dates[0] != today and dates[0] != (today - timedelta(days=1)): return 0
        
    streak = 1
    curr = dates[0]
    for d in dates[1:]:
        if d == curr - timedelta(days=1):
            streak += 1
            curr = d
        else:
            break
    return streak

st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

if "theme" not in st.query_params:
    st.query_params["theme"] = "dark" 

st.sidebar.title("⚙️ Настройки")
theme_choice = st.sidebar.radio("Оформление:", ["Темная тема 🌙", "Светлая тема ☀️"], index=0 if st.query_params["theme"] == "dark" else 1)

if theme_choice == "Темная тема 🌙":
    st.query_params["theme"] = "dark"
    bg_color, text_color, input_bg = "#000000", "#ffffff", "#111111"
else:
    st.query_params["theme"] = "light"
    bg_color, text_color, input_bg = "#ffffff", "#000000", "#f9f9f9"

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
    .stTabs [data-baseweb="tab-list"] button {{ color: {text_color} !important; }}
    </style>
""", unsafe_allow_html=True)

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
    return gspread.authorize(credentials)

try:
    client = init_connection()
    sheet = client.open("Наши ритуалы").sheet1 
    records = sheet.get_all_records()
except Exception as e:
    st.error(f"Ошибка базы данных: {e}")
    st.stop()

current_streak = get_streak(records)

col_title, col_streak = st.columns([3, 1])
with col_title: st.title("✨ Наши Ритуалы")
with col_streak: st.metric(label="Дней подряд", value=f"🔥 {current_streak}")
st.divider()

tab1, tab2 = st.tabs(["📝 Трекер", "📊 Статистика"])

with tab1:
    base_rituals = ["🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога", "🎮 Совместные игры"]
    history_rituals = [str(row['Ритуал']) for row in records if row.get('Ритуал')]
    all_rituals = sorted(list(set(base_rituals + history_rituals)))

    with st.form("habit_form"):
        date_input = st.text_input("Дата", value=datetime.now().strftime("%Y-%m-%d"))
        selected_ritual = st.selectbox("Что выполнили?", all_rituals)
        custom_ritual = st.text_input("ИЛИ впишите новый ритуал:")
        
        # НОВОЕ ПОЛЕ: ТАЙНОЕ ПОСЛАНИЕ
        secret_message = st.text_area("💌 Оставить тайное послание партнеру (необязательно):", placeholder="Оно откроется, когда партнер тоже выполнит этот ритуал...")
        
        submitted = st.form_submit_button("Я выполнил(а)! Сохранить ✨")
        
        if submitted:
            raw_ritual = custom_ritual.strip()
            if raw_ritual:
                parts = raw_ritual.split()
                final_ritual = f"{parts.pop()} {' '.join(parts)}" if len(parts) > 1 and ord(parts[-1][0]) > 10000 else raw_ritual
            else:
                final_ritual = selected_ritual
                
            match_idx, existing_fox, existing_bear = None, "❌", "❌"
            partner_msg = ""
            
            for i, row in enumerate(records):
                if str(row.get('Дата', '')) == date_input and str(row.get('Ритуал', '')) == final_ritual:
                    match_idx = i + 2 
                    existing_fox = row.get('Лисичка 🦊', '❌')
                    existing_bear = row.get('Мишка 🐻', '❌')
                    
                    # Читаем послание партнера
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
                
                # Записываем наше послание
                my_col_idx = 6 if current_user == "Лисичка 🦊" else 7
                if secret_message.strip():
                    sheet.update_cell(match_idx, my_col_idx, secret_message.strip())
                
                if new_together == "✅":
                    st.balloons()
                    st.success(f"Ого! {partner} тоже выполнил(а) это. Галочка ВМЕСТЕ получена! 🎉")
                    
                    # ПОКАЗЫВАЕМ СЕКРЕТНОЕ ПОСЛАНИЕ
                    if partner_msg:
                        st.info(f"💌 **Вам тайное послание от {partner}:**\n\n*{partner_msg}*")
                        send_telegram_message(f"💌 <b>Тайное послание прочитано!</b> {current_user} увидел(а) твою записку.")
                        
                    new_streak = get_streak(sheet.get_all_records())
                    if new_streak > 0 and new_streak % 7 == 0:
                        chooser = "Лисичка 🦊" if (new_streak // 7) % 2 != 0 else "Мишка 🐻"
                        st.success(f"🏆 Непрерывное занятие {new_streak} дней!\n\nНаграду выбирает: **{chooser}**!")
                        send_telegram_message(f"🏆 <b>Ура, вы разблокировали награду!</b>\nСерия: {new_streak} дней!\nНаграду выбирает: <b>{chooser}</b>!")
                else:
                    st.success("Отлично! Галочка поставлена. Ждем партнера ✨")
            else:
                new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
                new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
                fox_msg = secret_message.strip() if current_user == "Лисичка 🦊" else ""
                bear_msg = secret_message.strip() if current_user == "Мишка 🐻" else ""
                
                sheet.append_row([date_input, final_ritual, new_fox, new_bear, "❌", fox_msg, bear_msg])
                st.success(f"Записано! Ждем партнера ✨")
                if secret_message.strip():
                    st.info("🤫 Твое тайное послание надежно спрятано. Партнер увидит его, когда выполнит ритуал!")

    st.subheader("📖 Наша история")
    if records:
        df_hist = pd.DataFrame(records).iloc[::-1]
        # Прячем колонки с посланиями из общей таблицы, чтобы сохранить интригу
        if 'Послание Лисички' in df_hist.columns: df_hist = df_hist.drop(columns=['Послание Лисички'])
        if 'Послание Мишки' in df_hist.columns: df_hist = df_hist.drop(columns=['Послание Мишки'])
        st.dataframe(df_hist, use_container_width=True)

with tab2:
    if records:
        df_stats = pd.DataFrame(records)
        df_stats['Дата'] = pd.to_datetime(df_stats['Дата'])
        df_joint = df_stats[df_stats['Вместе ✨'] == '✅']
        
        if not df_joint.empty:
            st.subheader("🏆 Любимые ритуалы")
            ritual_counts = df_joint['Ритуал'].value_counts().reset_index()
            ritual_counts.columns = ['Ритуал', 'Дней']
            
            # ИСПРАВЛЕННЫЙ ГРАФИК (Снизу вверх, только целые числа)
            bar_chart = alt.Chart(ritual_counts).mark_bar(color='#9370DB', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X('Ритуал:N', title='', sort='-y', axis=alt.Axis(labelAngle=0)), # Горизонтальный текст снизу
                y=alt.Y('Дней:Q', title='Дней выполнено', axis=alt.Axis(tickMinStep=1, format='d')), # Только целые числа
                tooltip=['Ритуал', 'Дней']
            ).properties(height=350)
            st.altair_chart(bar_chart, use_container_width=True)

            st.divider()
            st.subheader("🔥 Тепловая карта")
            heatmap_data = df_joint.groupby('Дата').size().reset_index(name='Количество')
            
            # ИСПРАВЛЕННАЯ ТЕПЛОВАЯ КАРТА (безопасные углы)
            heat_chart = alt.Chart(heatmap_data).mark_rect(cornerRadius=3).encode(
                x=alt.X('date(Дата):O', title='День'),
                y=alt.Y('month(Дата):N', title='Месяц'),
                color=alt.Color('Количество:Q', scale=alt.Scale(scheme='purples'), legend=None),
                tooltip=[alt.Tooltip('Дата:T', title='Дата', format='%Y-%m-%d'), alt.Tooltip('Количество:Q', title='Ритуалов')]
            ).properties(height=200)
            st.altair_chart(heat_chart, use_container_width=True)
