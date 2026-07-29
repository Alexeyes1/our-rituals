import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import pandas as pd

# Настройка страницы
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

# --- 1. СТРОГИЙ ЧБ ДИЗАЙН И ФИКС СБРОСА ЦВЕТА ---
# Запоминаем выбор темы в адресной строке, чтобы не слетало при обновлении
if "theme" not in st.query_params:
    st.query_params["theme"] = "dark" 

st.sidebar.title("⚙️ Настройки")
theme_choice = st.sidebar.radio(
    "Оформление:", 
    ["Темная тема 🌙", "Светлая тема ☀️"], 
    index=0 if st.query_params["theme"] == "dark" else 1
)

# Инверсия цветов
if theme_choice == "Темная тема 🌙":
    st.query_params["theme"] = "dark"
    bg_color = "#000000"       # Строгий черный фон
    text_color = "#ffffff"     # Белый текст
    input_bg = "#1a1a1a"       # Чуть серый для полей ввода, чтобы их было видно
else:
    st.query_params["theme"] = "light"
    bg_color = "#ffffff"       # Строгий белый фон
    text_color = "#000000"     # Черный текст
    input_bg = "#f0f0f0"       # Светло-серый для полей

# Применяем стили (CSS)
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color} !important; }}
    h1, h2, h3, p, label, div {{ color: {text_color} !important; font-family: 'Arial', sans-serif; }}
    /* Настраиваем контраст полей ввода и таблиц */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {{ 
        background-color: {input_bg} !important; 
        color: {text_color} !important; 
        border: 1px solid {text_color} !important;
    }}
    [data-testid="stDataFrame"] {{ background-color: {input_bg} !important; }}
    hr {{ border-color: {text_color} !important; opacity: 0.3; }}
    </style>
""", unsafe_allow_html=True)


# --- 2. ПРОФИЛИ (ЗАПОМИНАЮТСЯ) ---
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


# --- 3. ПОДКЛЮЧЕНИЕ К БАЗЕ ---
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["json_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(credentials)

try:
    client = init_connection()
    sheet = client.open("Наши ритуалы").sheet1 
    records = sheet.get_all_records() # Читаем историю
except Exception as e:
    st.error(f"Ошибка базы данных: {e}")
    st.stop()

st.title("✨ Наши Ритуалы")
st.divider()


# --- 4. УМНОЕ ДОБАВЛЕНИЕ НОВЫХ РИТУАЛОВ ---
# Базовые ритуалы (добавил медитацию, чтение и зарядку по вашей просьбе)
base_rituals = ["🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога"]

# Сканируем базу: ищем все новые ритуалы, которые вы когда-либо вписывали
history_rituals = []
for row in records:
    if row.get('Ритуал'):
        history_rituals.append(str(row['Ритуал']))

# Объединяем списки и удаляем дубликаты
all_rituals = list(set(base_rituals + history_rituals))
all_rituals.sort() # Выстраиваем по алфавиту


# --- 5. ФОРМА СОХРАНЕНИЯ ---
st.subheader("📝 Отметить выполнение")
with st.form("habit_form"):
    today = datetime.now().strftime("%Y-%m-%d")
    date_input = st.text_input("Дата", value=today)
    
    st.write("Что выполнили?")
    # Выпадающий список из всех известных ритуалов
    selected_ritual = st.selectbox("Выберите из списка:", all_rituals)
    
    # Поле для создания нового!
    custom_ritual = st.text_input("ИЛИ впишите новый ритуал (он сохранится в список навсегда):", placeholder="Например: 🎮 Совместные игры")
    
    submitted = st.form_submit_button("Я выполнил(а)! Сохранить ✨")
    
    if submitted:
        # Если вписали свой текст - берем его, если нет - берем из выпадающего списка
        final_ritual = custom_ritual.strip() if custom_ritual.strip() else selected_ritual
        
        match_idx = None
        existing_fox = "❌"
        existing_bear = "❌"
        
        # Умная проверка: отмечал ли партнер это сегодня?
        for i, row in enumerate(records):
            if str(row.get('Дата', '')) == date_input and str(row.get('Ритуал', '')) == final_ritual:
                match_idx = i + 2 
                existing_fox = row.get('Лисичка 🦊', '❌')
                existing_bear = row.get('Мишка 🐻', '❌')
                break
        
        if match_idx:
            # Обновляем существующую запись
            new_fox = "✅" if current_user == "Лисичка 🦊" else existing_fox
            new_bear = "✅" if current_user == "Мишка 🐻" else existing_bear
            new_together = "✅" if (new_fox == "✅" and new_bear == "✅") else "❌"
            
            sheet.update_cell(match_idx, 3, new_fox)
            sheet.update_cell(match_idx, 4, new_bear)
            sheet.update_cell(match_idx, 5, new_together)
            
            if new_together == "✅":
                st.success(f"Ого! {partner} тоже выполнил(а) это. Галочка ВМЕСТЕ получена! 🎉")
                st.balloons()
            else:
                st.success("Отлично! Галочка поставлена. Ждем партнера ✨")
        else:
            # Создаем новую запись на сегодня
            new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
            new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
            
            sheet.append_row([date_input, final_ritual, new_fox, new_bear, "❌"])
            st.success(f"Записано в историю! Если это новый ритуал, он теперь будет в списке всегда. Ждем партнера ✨")

st.divider()
st.subheader("📖 Наша история")
if records:
    df = pd.DataFrame(records).iloc[::-1] # Переворачиваем, чтобы свежие были сверху
    st.dataframe(df, use_container_width=True)
else:
    st.info("Пока нет записей.")
