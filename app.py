import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import pandas as pd
import requests # НОВАЯ БИБЛИОТЕКА ДЛЯ ТЕЛЕГРАМА

# --- ФУНКЦИЯ ДЛЯ ТЕЛЕГРАМА ---
def send_telegram_message(text):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# 1. Настройка страницы
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

# --- 2. СТРОГИЙ ЧБ ДИЗАЙН И ФИКС ЦВЕТОВ ---
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
    h1, h2, h3, p, label, span {{ color: {text_color} !important; font-family: 'Arial', sans-serif; }}
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid {text_color} !important;
    }}
    
    .stTextInput input::placeholder {{ color: {text_color} !important; opacity: 0.5 !important; }}
    
    div[data-baseweb="popover"] > div, ul[role="listbox"] {{ background-color: {input_bg} !important; }}
    li[role="option"] {{ background-color: {input_bg} !important; color: {text_color} !important; }}
    li[role="option"]:hover {{ background-color: {text_color} !important; color: {bg_color} !important; }}
    
    div[data-testid="stFormSubmitButton"] button {{ background-color: {text_color} !important; border: 2px solid {text_color} !important; }}
    div[data-testid="stFormSubmitButton"] button p {{ color: {bg_color} !important; font-weight: bold !important; }}
    div[data-testid="stFormSubmitButton"] button:hover {{ opacity: 0.8; }}
    svg {{ fill: {text_color} !important; }}
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


# --- 4. ПОДКЛЮЧЕНИЕ К БАЗЕ ---
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


# --- 5. УМНОЕ ДОБАВЛЕНИЕ НОВЫХ РИТУАЛОВ ---
base_rituals = ["🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога"]

history_rituals = [str(row['Ритуал']) for row in records if row.get('Ритуал')]
all_rituals = list(set(base_rituals + history_rituals))
all_rituals.sort()

st.title("✨ Наши Ритуалы")
st.divider()

# --- 6. ФОРМА СОХРАНЕНИЯ ---
st.subheader("📝 Отметить выполнение")
with st.form("habit_form"):
    today = datetime.now().strftime("%Y-%m-%d")
    date_input = st.text_input("Дата", value=today)
    
    st.write("Что выполнили?")
    selected_ritual = st.selectbox("Выберите из списка:", all_rituals)
    custom_ritual = st.text_input("ИЛИ впишите новый (он сохранится в список навсегда):", placeholder="Например: Совместные игры 🎮")
    
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
                st.success(f"Ого! {partner} тоже выполнил(а) это. Галочка ВМЕСТЕ получена! 🎉")
                st.balloons()
                # УВЕДОМЛЕНИЕ О СОВМЕСТНОМ ВЫПОЛНЕНИЙ
                send_telegram_message(f"🎉 <b>Ура!</b> Вы оба выполнили: <b>{final_ritual}</b>!\nГалочка ВМЕСТЕ получена! ✨")
            else:
                st.success("Отлично! Галочка поставлена. Ждем партнера ✨")
                # УВЕДОМЛЕНИЕ ДЛЯ ПАРТНЕРА
                send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, теперь твоя очередь! ✨")
        else:
            new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
            new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
            
            sheet.append_row([date_input, final_ritual, new_fox, new_bear, "❌"])
            st.success(f"Записано в историю! Ждем партнера ✨")
            # УВЕДОМЛЕНИЕ ДЛЯ ПАРТНЕРА (когда создается новая запись)
            send_telegram_message(f"<b>{current_user}</b> только что выполнил(а):\n👉 <b>{final_ritual}</b>\n\n{partner}, теперь твоя очередь! ✨")

st.divider()
st.subheader("📖 Наша история")
if records:
    df = pd.DataFrame(records).iloc[::-1]
    st.dataframe(df, use_container_width=True)
else:
    st.info("Пока нет записей.")
