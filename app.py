import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import pandas as pd

# Настройка страницы
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

# --- БОКОВОЕ МЕНЮ И НАСТРОЙКИ ---
st.sidebar.title("🎨 Настройки")
bg_color = st.sidebar.color_picker("Выбрать цвет фона", "#f6f3f8")

# CSS для красивого дизайна и исправления контраста (чтобы буквы не сливались)
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color} !important; }}
    h1, h2, h3, p, label {{ color: #2c3e50 !important; font-family: 'Georgia', serif; }}
    /* Делаем поля ввода и таблицы белыми для читаемости */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {{ background-color: #ffffff !important; color: #000000 !important; }}
    [data-testid="stDataFrame"] {{ background-color: #ffffff !important; }}
    </style>
""", unsafe_allow_html=True)

# --- ПРИВЕТСТВЕННЫЙ ЭКРАН (ПРОФИЛИ) ---
# Проверяем, выбран ли уже профиль
if "user" not in st.query_params:
    st.title("Привет! Кто ты? 👋")
    st.write("Выбери свой профиль (настраивается один раз для этого устройства):")
    
    col1, col2 = st.columns(2)
    if col1.button("Я Лисичка 🦊", use_container_width=True):
        st.query_params["user"] = "fox"
        st.rerun()
    if col2.button("Я Мишка 🐻", use_container_width=True):
        st.query_params["user"] = "bear"
        st.rerun()
    st.stop() # Останавливаем загрузку остального кода, пока не выберут профиль

# Определяем текущего пользователя
user_code = st.query_params["user"]
current_user = "Лисичка 🦊" if user_code == "fox" else "Мишка 🐻"
partner = "Мишка 🐻" if user_code == "fox" else "Лисичка 🦊"

# Кнопка сброса профиля в боковом меню
st.sidebar.write(f"Текущий профиль: **{current_user}**")
if st.sidebar.button("Сменить профиль"):
    st.query_params.clear()
    st.rerun()


# --- ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ---
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["json_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(credentials)

try:
    client = init_connection()
    sheet = client.open("Наши ритуалы").sheet1 
except Exception as e:
    st.error(f"Ошибка подключения к базе: {e}")
    st.stop()


# --- ОСНОВНОЕ ПРИЛОЖЕНИЕ ---
st.title("✨ Наши Ритуалы")
st.write(f"С возвращением, **{current_user}**! Чем поделишься сегодня?")
st.divider()

# Форма заполнения
with st.form("habit_form"):
    today = datetime.now().strftime("%Y-%m-%d")
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.text_input("Дата", value=today)
    with col2:
        # Добавлены новые привычки!
        rituals_list = [
            "🧘‍♀️ Медитация", "⚡️ Зарядка", "📖 Чтение", 
            "🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога"
        ]
        ritual = st.selectbox("Какой ритуал выполнили?", rituals_list)
    
    submitted = st.form_submit_button("Я выполнил(а)! Сохранить ✨")
    
    if submitted:
        # УМНАЯ ЛОГИКА "ВМЕСТЕ"
        records = sheet.get_all_records()
        match_idx = None
        existing_fox = "❌"
        existing_bear = "❌"
        
        # Ищем, отмечал ли уже партнер этот ритуал сегодня
        for i, row in enumerate(records):
            if str(row.get('Дата', '')) == date_input and row.get('Ритуал', '') == ritual:
                match_idx = i + 2 # +2 из-за заголовков таблицы
                existing_fox = row.get('Лисичка 🦊', '❌')
                existing_bear = row.get('Мишка 🐻', '❌')
                break
        
        if match_idx:
            # Строка уже есть! Обновляем данные
            new_fox = "✅" if current_user == "Лисичка 🦊" else existing_fox
            new_bear = "✅" if current_user == "Мишка 🐻" else existing_bear
            
            # Проверяем, выполнили ли оба
            new_together = "✅" if (new_fox == "✅" and new_bear == "✅") else "❌"
            
            # Записываем обновления
            sheet.update_cell(match_idx, 3, new_fox)
            sheet.update_cell(match_idx, 4, new_bear)
            sheet.update_cell(match_idx, 5, new_together)
            
            if new_together == "✅":
                st.success(f"Ого! {partner} тоже выполнил(а) это сегодня. Галочка ВМЕСТЕ получена! 🎉")
                st.balloons()
            else:
                st.success("Отлично! Данные обновлены. Ждем партнера ✨")
        else:
            # Записей за сегодня еще нет, создаем новую
            new_fox = "✅" if current_user == "Лисичка 🦊" else "❌"
            new_bear = "✅" if current_user == "Мишка 🐻" else "❌"
            
            sheet.append_row([date_input, ritual, new_fox, new_bear, "❌"])
            st.success("Ура! Записано в историю. Теперь ждем, когда отметится партнер ✨")

st.divider()
st.subheader("📖 Наша история")
try:
    data = sheet.get_all_records()
    if data:
        # Показываем самые свежие записи сверху
        df = pd.DataFrame(data).iloc[::-1]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Пока нет записей. Сделайте первый шаг!")
except Exception as e:
    st.warning(f"Не удалось загрузить историю. Ошибка: {e}")
