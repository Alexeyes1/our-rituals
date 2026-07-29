import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
import pandas as pd

# Настройка страницы
st.set_page_config(page_title="Наши Ритуалы", page_icon="✨", layout="centered")

# Лавандовый дизайн
st.markdown("""
    <style>
    .stApp { background-color: #f6f3f8; }
    h1, h2, h3, p, div { color: #3b3142; font-family: 'Georgia', serif; }
    </style>
""", unsafe_allow_html=True)

st.title("✨ Наши Еженедельные Ритуалы")
st.write("Традиции Лисички 🦊 и Мишки 🐻, которые мы создаем вместе")
st.divider()

# Подключение к Гугл Таблице
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["json_key"])
    credentials = Credentials.from_service_account_info(key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(credentials)

try:
    client = init_connection()
    # ВАЖНО: Имя таблицы в точности как на вашем скриншоте
    sheet = client.open("Наши ритуалы").sheet1 
except Exception as e:
    st.error("Ошибка подключения к таблице. Проверьте секреты (Secrets).")
    st.stop()

st.subheader("📝 Отметить выполнение")
with st.form("habit_form"):
    today = datetime.now().strftime("%Y-%m-%d")
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.text_input("Дата", value=today)
    with col2:
        ritual = st.selectbox("Какой ритуал?", ["🎤 Пение", "💬 Разговор по душам", "🌲 Прогулка", "🧘‍♂️ Совместная йога"])
    
    st.write("Кто участвовал?")
    col3, col4, col5 = st.columns(3)
    with col3:
        fox_done = st.checkbox("Лисичка 🦊")
    with col4:
        bear_done = st.checkbox("Мишка 🐻")
    with col5:
        we_done = st.checkbox("Вместе ✨")
    
    submitted = st.form_submit_button("Сохранить в нашу историю ✨")
    
    if submitted:
        # Превращаем галочки в эмодзи для таблицы
        fox_val = "✅" if fox_done else "❌"
        bear_val = "✅" if bear_done else "❌"
        we_val = "✅" if we_done else "❌"
        
        # Отправляем 5 колонок ровно в том порядке, как у вас в таблице
        sheet.append_row([date_input, ritual, fox_val, bear_val, we_val])
        st.success("Ура! Традиция сохранена в нашу историю 🎉")
        st.balloons()

st.divider()
st.subheader("📖 Наша история")
try:
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Пока нет записей. Отметьте ваш первый ритуал!")
except Exception:
    st.warning("Не удалось загрузить историю. Проверьте названия колонок в таблице.")
