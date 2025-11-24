import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
from typing import Dict, List, Tuple

# 🔑 ЗАМЕНИТЕ НА ВАШ DEEPSEEK API КЛЮЧ
DEEPSEEK_API_KEY = "sk-333eb062315a4bf5a7e01747053c38b3"

# 🖼️ ЗАМЕНИТЕ НА ССЫЛКУ ВАШЕГО ЛОГОТИПА (или оставьте пустым для эмодзи)
APP_LOGO_URL = "https://ferlenguas.ru/wp-content/uploads/2025/11/logo.png"  # Например: "https://raw.githubusercontent.com/your-repo/logo.png"


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('language_tutor.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                native_language TEXT,
                interface_language TEXT DEFAULT 'russian',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица изучения языков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_languages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                target_language TEXT,
                level TEXT DEFAULT 'beginner',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Таблица сессий обучения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                target_language TEXT,
                session_type TEXT,
                duration_minutes INTEGER,
                exercises_completed INTEGER,
                score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Таблица прогресса
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                target_language TEXT,
                vocabulary_learned INTEGER DEFAULT 0,
                grammar_exercises INTEGER DEFAULT 0,
                conversation_practice INTEGER DEFAULT 0,
                total_time INTEGER DEFAULT 0,
                last_studied TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        self.conn.commit()


class LanguageTutor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # Языки для изучения
        self.target_languages = {
            "english": {"name": "Английский", "flag": "🇬🇧", "code": "en"},
            "spanish": {"name": "Испанский", "flag": "🇪🇸", "code": "es"},
            "french": {"name": "Французский", "flag": "🇫🇷", "code": "fr"},
            "german": {"name": "Немецкий", "flag": "🇩🇪", "code": "de"},
            "chinese": {"name": "Китайский", "flag": "🇨🇳", "code": "zh"},
            "japanese": {"name": "Японский", "flag": "🇯🇵", "code": "ja"},
            "russian": {"name": "Русский", "flag": "🇷🇺", "code": "ru"},
            "korean": {"name": "Корейский", "flag": "🇰🇷", "code": "ko"},
            "italian": {"name": "Итальянский", "flag": "🇮🇹", "code": "it"},
            "arabic": {"name": "Арабский", "flag": "🇸🇦", "code": "ar"},
            "portuguese": {"name": "Португальский", "flag": "🇵🇹", "code": "pt"},
            "turkish": {"name": "Турецкий", "flag": "🇹🇷", "code": "tr"},
            "hindi": {"name": "Хинди", "flag": "🇮🇳", "code": "hi"},
            "dutch": {"name": "Нидерландский", "flag": "🇳🇱", "code": "nl"},
            "swedish": {"name": "Шведский", "flag": "🇸🇪", "code": "sv"},
            "norwegian": {"name": "Норвежский", "flag": "🇳🇴", "code": "no"},
            "danish": {"name": "Датский", "flag": "🇩🇰", "code": "da"},
            "finnish": {"name": "Финский", "flag": "🇫🇮", "code": "fi"},
            "polish": {"name": "Польский", "flag": "🇵🇱", "code": "pl"},
            "czech": {"name": "Чешский", "flag": "🇨🇿", "code": "cs"},
            "hungarian": {"name": "Венгерский", "flag": "🇭🇺", "code": "hu"},
            "greek": {"name": "Греческий", "flag": "🇬🇷", "code": "el"},
            "hebrew": {"name": "Иврит", "flag": "🇮🇱", "code": "he"},
            "thai": {"name": "Тайский", "flag": "🇹🇭", "code": "th"},
            "vietnamese": {"name": "Вьетнамский", "flag": "🇻🇳", "code": "vi"},
            "indonesian": {"name": "Индонезийский", "flag": "🇮🇩", "code": "id"},
            "malay": {"name": "Малайский", "flag": "🇲🇾", "code": "ms"},
            "filipino": {"name": "Филиппинский", "flag": "🇵🇭", "code": "tl"},
            "ukrainian": {"name": "Украинский", "flag": "🇺🇦", "code": "uk"},
            "belarusian": {"name": "Белорусский", "flag": "🇧🇾", "code": "be"},
            "bulgarian": {"name": "Болгарский", "flag": "🇧🇬", "code": "bg"},
            "romanian": {"name": "Румынский", "flag": "🇷🇴", "code": "ro"},
            "serbian": {"name": "Сербский", "flag": "🇷🇸", "code": "sr"},
            "croatian": {"name": "Хорватский", "flag": "🇭🇷", "code": "hr"},
            "slovak": {"name": "Словацкий", "flag": "🇸🇰", "code": "sk"},
            "slovenian": {"name": "Словенский", "flag": "🇸🇮", "code": "sl"},
            "lithuanian": {"name": "Литовский", "flag": "🇱🇹", "code": "lt"},
            "latvian": {"name": "Латышский", "flag": "🇱🇻", "code": "lv"},
            "estonian": {"name": "Эстонский", "flag": "🇪🇪", "code": "et"},
            "icelandic": {"name": "Исландский", "flag": "🇮🇸", "code": "is"},
            "maltese": {"name": "Мальтийский", "flag": "🇲🇹", "code": "mt"},
            "georgian": {"name": "Грузинский", "flag": "🇬🇪", "code": "ka"},
            "armenian": {"name": "Армянский", "flag": "🇦🇲", "code": "hy"},
            "azerbaijani": {"name": "Азербайджанский", "flag": "🇦🇿", "code": "az"},
            "kazakh": {"name": "Казахский", "flag": "🇰🇿", "code": "kk"},
            "uzbek": {"name": "Узбекский", "flag": "🇺🇿", "code": "uz"},
            "kyrgyz": {"name": "Киргизский", "flag": "🇰🇬", "code": "ky"},
            "turkmen": {"name": "Туркменский", "flag": "🇹🇲", "code": "tk"},
            "tajik": {"name": "Таджикский", "flag": "🇹🇯", "code": "tg"},
            "mongolian": {"name": "Монгольский", "flag": "🇲🇳", "code": "mn"},
            "persian": {"name": "Персидский", "flag": "🇮🇷", "code": "fa"},
            "urdu": {"name": "Урду", "flag": "🇵🇰", "code": "ur"},
            "bengali": {"name": "Бенгальский", "flag": "🇧🇩", "code": "bn"},
            "punjabi": {"name": "Панджаби", "flag": "🇮🇳", "code": "pa"},
            "tamil": {"name": "Тамильский", "flag": "🇮🇳", "code": "ta"},
            "telugu": {"name": "Телугу", "flag": "🇮🇳", "code": "te"},
            "marathi": {"name": "Маратхи", "flag": "🇮🇳", "code": "mr"},
            "gujarati": {"name": "Гуджарати", "flag": "🇮🇳", "code": "gu"},
            "kannada": {"name": "Каннада", "flag": "🇮🇳", "code": "kn"},
            "malayalam": {"name": "Малаялам", "flag": "🇮🇳", "code": "ml"},
            "sinhala": {"name": "Сингальский", "flag": "🇱🇰", "code": "si"},
            "nepali": {"name": "Непальский", "flag": "🇳🇵", "code": "ne"},
            "burmese": {"name": "Бирманский", "flag": "🇲🇲", "code": "my"},
            "khmer": {"name": "Кхмерский", "flag": "🇰🇭", "code": "km"},
            "lao": {"name": "Лаосский", "flag": "🇱🇦", "code": "lo"},
            "swahili": {"name": "Суахили", "flag": "🇰🇪", "code": "sw"},
            "yoruba": {"name": "Йоруба", "flag": "🇳🇬", "code": "yo"},
            "igbo": {"name": "Игбо", "flag": "🇳🇬", "code": "ig"},
            "hausa": {"name": "Хауса", "flag": "🇳🇬", "code": "ha"},
            "amharic": {"name": "Амхарский", "flag": "🇪🇹", "code": "am"},
            "somali": {"name": "Сомали", "flag": "🇸🇴", "code": "so"},
            "zulu": {"name": "Зулу", "flag": "🇿🇦", "code": "zu"},
            "afrikaans": {"name": "Африкаанс", "flag": "🇿🇦", "code": "af"},
            "albanian": {"name": "Албанский", "flag": "🇦🇱", "code": "sq"},
            "basque": {"name": "Баскский", "flag": "🇪🇸", "code": "eu"},
            "catalan": {"name": "Каталанский", "flag": "🇪🇸", "code": "ca"},
            "galician": {"name": "Галисийский", "flag": "🇪🇸", "code": "gl"},
            "welsh": {"name": "Валлийский", "flag": "🏴", "code": "cy"},
            "irish": {"name": "Ирландский", "flag": "🇮🇪", "code": "ga"},
            "scottish_gaelic": {"name": "Шотландский гэльский", "flag": "🏴", "code": "gd"},
            "breton": {"name": "Бретонский", "flag": "🇫🇷", "code": "br"},
            "esperanto": {"name": "Эсперанто", "flag": "🟢", "code": "eo"},
            "latin": {"name": "Латинский", "flag": "🏛️", "code": "la"},
            "ancient_greek": {"name": "Древнегреческий", "flag": "🏛️", "code": "grc"},
            "sanskrit": {"name": "Санскрит", "flag": "🇮🇳", "code": "sa"}
        }

        # Языки интерфейса
        self.interface_languages = {
            "russian": {"name": "Русский", "emoji": "🇷🇺"},
            "english": {"name": "English", "emoji": "🇬🇧"},
            "spanish": {"name": "Español", "emoji": "🇪🇸"},
            "french": {"name": "Français", "emoji": "🇫🇷"}
        }

        # Уровни владения
        self.levels = {
            "beginner": {"name": "Начинающий (A1)", "emoji": ""},
            "elementary": {"name": "Элементарный (A2)", "emoji": ""},
            "intermediate": {"name": "Средний (B1-B2)", "emoji": ""},
            "advanced": {"name": "Продвинутый (C1-C2)", "emoji": ""}
        }

    def get_system_prompt(self, target_language: str, interface_language: str, level: str) -> str:
        """Создает системный промпт для репетитора"""

        prompts = {
            "russian": f"""Ты - профессиональный репетитор по {self.target_languages[target_language]['name']}. 
Уровень студента: {self.levels[level]['name']}.

Твои обязанности:
1. Объясняй грамматику простыми словами с примерами
2. Приводи примеры использования слов и выражений
3. Исправляй ошибки и подробно объясняй почему они ошибки
4. Задавай практические вопросы для закрепления материала
5. Будь терпеливым, поддерживающим и мотивирующим
6. Используй смесь русского и {self.target_languages[target_language]['name']} языка в зависимости от уровня студента
7. Структурируй информацию четко и понятно
8. Предлагай дополнительные упражнения для практики

Отвечай на русском языке, но включай примеры и практические задания на изучаемом языке.""",

            "english": f"""You are a professional {self.target_languages[target_language]['name']} tutor.
Student level: {level}.

Your responsibilities:
1. Explain grammar in simple terms with examples
2. Provide examples of word and expression usage
3. Correct mistakes and explain why they are mistakes
4. Ask practical questions to reinforce material
5. Be patient, supportive and motivating
6. Use a mix of English and {self.target_languages[target_language]['name']} depending on student level
7. Structure information clearly and understandably
8. Suggest additional exercises for practice

Respond in English, but include examples and practical exercises in the target language."""
        }

        return prompts.get(interface_language, prompts["russian"])

    def send_message(self, message: str, target_language: str, interface_language: str,
                     level: str, conversation_history: List[Dict]) -> str:
        """Отправляет сообщение в DeepSeek API"""

        system_prompt = self.get_system_prompt(target_language, interface_language, level)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500
        }

        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            return f"Ошибка при обращении к API: {str(e)}"
        except Exception as e:
            return f"Произошла ошибка: {str(e)}"


class UserStatistics:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_user_stats(self, user_id: int) -> Dict:
        """Получает полную статистику пользователя"""
        cursor = self.db.conn.cursor()

        # Общая статистика
        cursor.execute('''
            SELECT COUNT(*) as total_sessions,
                   SUM(duration_minutes) as total_time,
                   SUM(exercises_completed) as total_exercises,
                   AVG(score) as avg_score
            FROM study_sessions 
            WHERE user_id = ?
        ''', (user_id,))
        total_stats = cursor.fetchone()

        # Статистика по языкам
        cursor.execute('''
            SELECT target_language, 
                   COUNT(*) as sessions,
                   SUM(duration_minutes) as time,
                   SUM(exercises_completed) as exercises,
                   AVG(score) as avg_score
            FROM study_sessions 
            WHERE user_id = ?
            GROUP BY target_language
            ORDER BY time DESC
        ''', (user_id,))
        language_stats = cursor.fetchall()

        # Прогресс за последние 30 дней
        cursor.execute('''
            SELECT DATE(created_at) as date,
                   SUM(duration_minutes) as daily_time,
                   SUM(exercises_completed) as daily_exercises
            FROM study_sessions 
            WHERE user_id = ? AND created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (user_id,))
        progress_data = cursor.fetchall()

        # Типы сессий
        cursor.execute('''
            SELECT session_type, COUNT(*) as count
            FROM study_sessions 
            WHERE user_id = ?
            GROUP BY session_type
        ''', (user_id,))
        session_types = cursor.fetchall()

        return {
            "total_sessions": total_stats[0] or 0,
            "total_time": total_stats[1] or 0,
            "total_exercises": total_stats[2] or 0,
            "avg_score": total_stats[3] or 0,
            "language_stats": language_stats,
            "progress_data": progress_data,
            "session_types": session_types
        }

    def get_streak(self, user_id: int) -> int:
        """Вычисляет текущую серию дней обучения"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            WITH dates AS (
                SELECT DISTINCT DATE(created_at) as study_date
                FROM study_sessions 
                WHERE user_id = ?
                ORDER BY study_date DESC
            ),
            streaks AS (
                SELECT study_date,
                       JULIANDAY(study_date) - JULIANDAY(LAG(study_date, 1, study_date) OVER (ORDER BY study_date DESC)) as diff
                FROM dates
            )
            SELECT COUNT(*) as streak
            FROM streaks
            WHERE diff = 1
            ORDER BY study_date DESC
            LIMIT 1
        ''', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0


def init_session_state():
    """Инициализация состояния сессии"""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "db" not in st.session_state:
        st.session_state.db = DatabaseManager()
    if "tutor" not in st.session_state:
        st.session_state.tutor = LanguageTutor(DEEPSEEK_API_KEY)
    if "stats" not in st.session_state:
        st.session_state.stats = UserStatistics(st.session_state.db)
    if "current_language" not in st.session_state:
        st.session_state.current_language = "english"
    if "current_level" not in st.session_state:
        st.session_state.current_level = "beginner"


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email: str) -> bool:
    """Простая валидация email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def register_user(username: str, email: str, password: str, native_language: str, interface_language: str) -> bool:
    """Регистрация нового пользователя"""
    try:
        cursor = st.session_state.db.conn.cursor()

        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            return False

        # Создаем пользователя
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, native_language, interface_language) VALUES (?, ?, ?, ?, ?)",
            (username, email, hash_password(password), native_language, interface_language)
        )

        user_id = cursor.lastrowid

        # Добавляем языки по умолчанию
        default_languages = ["english", "spanish", "french"]
        for lang in default_languages:
            cursor.execute(
                "INSERT INTO user_languages (user_id, target_language) VALUES (?, ?)",
                (user_id, lang)
            )

        st.session_state.db.conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка при регистрации: {str(e)}")
        return False


def login_user(username: str, password: str) -> bool:
    """Авторизация пользователя"""
    try:
        cursor = st.session_state.db.conn.cursor()
        cursor.execute(
            "SELECT id, username, interface_language FROM users WHERE username = ? AND password_hash = ?",
            (username, hash_password(password))
        )
        user = cursor.fetchone()

        if user:
            st.session_state.user = {
                "id": user[0],
                "username": user[1],
                "interface_language": user[2]
            }
            return True
        return False
    except Exception as e:
        st.error(f"Ошибка при входе: {str(e)}")
        return False


def get_user_languages(user_id: int) -> List[str]:
    """Получает языки пользователя"""
    cursor = st.session_state.db.conn.cursor()
    cursor.execute(
        "SELECT target_language FROM user_languages WHERE user_id = ? AND is_active = TRUE",
        (user_id,)
    )
    return [row[0] for row in cursor.fetchall()]


def add_user_language(user_id: int, language: str):
    """Добавляет язык для изучения"""
    try:
        cursor = st.session_state.db.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO user_languages (user_id, target_language) VALUES (?, ?)",
            (user_id, language)
        )
        st.session_state.db.conn.commit()
    except Exception as e:
        st.error(f"Ошибка при добавлении языка: {str(e)}")


def record_study_session(user_id: int, target_language: str, session_type: str,
                         duration: int, exercises: int, score: int = 0):
    """Записывает сессию обучения"""
    try:
        cursor = st.session_state.db.conn.cursor()
        cursor.execute('''
            INSERT INTO study_sessions (user_id, target_language, session_type, duration_minutes, exercises_completed, score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, target_language, session_type, duration, exercises, score))
        st.session_state.db.conn.commit()
    except Exception as e:
        st.error(f"Ошибка при записи сессии: {str(e)}")


def get_logo_html():
    """Генерирует HTML для отображения логотипа"""
    if APP_LOGO_URL:
        return f"""
        <div class="sidebar-header">
            <div class="sidebar-logo-container">
                <img src="{APP_LOGO_URL}" 
                     class="sidebar-logo-img" 
                     alt="Логотип Языковой Репетитор"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div class="sidebar-logo-fallback">🎓</div>
            </div>
            <h1 class="sidebar-title">Языковой Репетитор FERAIS</h1>
            <p class="sidebar-subtitle">Ваш личный учитель языков</p>
        </div>
        """
    else:
        return """
        <div class="sidebar-header">
            <div class="sidebar-logo-container">
                <div class="sidebar-logo-emoji">🎓</div>
            </div>
            <h1 class="sidebar-title">Языковой Репетитор FERAIS</h1>
            <p class="sidebar-subtitle">Ваш личный учитель языков</p>
        </div>
        """


def render_sidebar():
    """Боковая панель с настройками"""
    with st.sidebar:
        # Логотип и название приложения
        logo_html = get_logo_html()
        st.markdown(logo_html, unsafe_allow_html=True)

        # Информация о пользователе
        st.markdown(f"""
        <div class="user-card">
            <div class="user-name">👤 {st.session_state.user['username']}</div>
            <div class="user-status">Активный ученик</div>
        </div>
        """, unsafe_allow_html=True)

        st.header("⚙️ Настройки обучения")

        # Выбор языка для изучения
        user_languages = get_user_languages(st.session_state.user["id"])
        target_language = st.selectbox(
            "Язык для изучения",
            options=user_languages,
            format_func=lambda
                x: f"{st.session_state.tutor.target_languages[x]['flag']} {st.session_state.tutor.target_languages[x]['name']}",
            key="language_selector"
        )

        # Добавление нового языка
        with st.expander("➕ Добавить язык"):
            available_languages = [lang for lang in st.session_state.tutor.target_languages.keys() if
                                   lang not in user_languages]
            if available_languages:
                new_lang = st.selectbox(
                    "Выберите язык",
                    options=available_languages,
                    format_func=lambda
                        x: f"{st.session_state.tutor.target_languages[x]['flag']} {st.session_state.tutor.target_languages[x]['name']}"
                )
                if st.button("Добавить язык", key="add_lang_btn"):
                    add_user_language(st.session_state.user["id"], new_lang)
                    st.success(f"Язык {st.session_state.tutor.target_languages[new_lang]['name']} добавлен!")
                    st.rerun()
            else:
                st.info("Вы изучаете все доступные языки!")

        # Уровень владения
        level = st.selectbox(
            "Ваш уровень",
            options=list(st.session_state.tutor.levels.keys()),
            format_func=lambda
                x: f"{st.session_state.tutor.levels[x]['emoji']} {st.session_state.tutor.levels[x]['name']}",
            key="level_selector"
        )

        st.session_state.current_language = target_language
        st.session_state.current_level = level

        st.divider()

        # Быстрые действия
        st.header("Быстрые действия")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="grammar-btn">', unsafe_allow_html=True)
            if st.button("Грамматика", use_container_width=True, key="grammar_btn"):
                start_grammar_session(target_language, level)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="vocab-btn">', unsafe_allow_html=True)
            if st.button("Словарь", use_container_width=True, key="vocab_btn"):
                start_vocabulary_session(target_language, level)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="dialogue-btn">', unsafe_allow_html=True)
            if st.button("Диалог", use_container_width=True, key="dialogue_btn"):
                start_conversation_session(target_language, level)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="test-btn">', unsafe_allow_html=True)
            if st.button("Тест", use_container_width=True, key="test_btn"):
                start_test_session(target_language, level)
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # Текущий прогресс
        stats = st.session_state.stats.get_user_stats(st.session_state.user["id"])
        streak = st.session_state.stats.get_streak(st.session_state.user["id"])

        st.markdown(f"""
        <div class="progress-card">
            <div class="progress-title">📈 Текущий прогресс</div>
            <div class="progress-stats">{stats['total_time']} мин • {streak} дн</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Выйти", use_container_width=True, key="logout_btn"):
            st.session_state.user = None
            st.session_state.conversation = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def render_learning_interface():
    """Основной интерфейс обучения"""
    st.header(f"{st.session_state.tutor.target_languages[st.session_state.current_language]['flag']} "
              f"Обучение {st.session_state.tutor.target_languages[st.session_state.current_language]['name']}")

    # Чат с репетитором
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.conversation[-10:]:  # Показываем последние 10 сообщений
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

    # Ввод сообщения
    if prompt := st.chat_input("Задайте вопрос репетитору..."):
        handle_user_message(
            prompt,
            st.session_state.current_language,
            st.session_state.user["interface_language"],
            st.session_state.current_level
        )


def handle_user_message(message: str, target_language: str, interface_language: str, level: str):
    """Обработка сообщения пользователя"""
    st.session_state.conversation.append({"role": "user", "content": message})

    with st.spinner("Репетитор думает..."):
        response = st.session_state.tutor.send_message(
            message, target_language, interface_language, level,
            st.session_state.conversation[:-1]
        )
        st.session_state.conversation.append({"role": "assistant", "content": response})

    # Записываем сессию
    record_study_session(
        st.session_state.user["id"],
        target_language,
        "conversation",
        3,  # предполагаемая длительность
        1  # одно упражнение (вопрос-ответ)
    )

    st.rerun()


def start_grammar_session(target_language: str, level: str):
    """Начинает сессию по грамматике"""
    prompt = "Объясни грамматическую тему и дай 3-5 практических упражнений с ответами"
    handle_user_message(prompt, target_language, st.session_state.user["interface_language"], level)
    record_study_session(st.session_state.user["id"], target_language, "grammar", 10, 5, 85)


def start_conversation_session(target_language: str, level: str):
    """Начинает сессию разговорной практики"""
    prompt = "Начни диалог для практики разговорной речи. Задавай вопросы и жди моих ответов"
    handle_user_message(prompt, target_language, st.session_state.user["interface_language"], level)
    record_study_session(st.session_state.user["id"], target_language, "conversation", 15, 8, 90)


def start_vocabulary_session(target_language: str, level: str):
    """Начинает сессию по изучению слов"""
    prompt = "Представь 10 новых слов с переводами, примерами использования и упражнениями для запоминания"
    handle_user_message(prompt, target_language, st.session_state.user["interface_language"], level)
    record_study_session(st.session_state.user["id"], target_language, "vocabulary", 12, 10, 88)


def start_test_session(target_language: str, level: str):
    """Начинает тестовую сессию"""
    prompt = "Проведи небольшой тест из 5 вопросов по пройденному материалу. Задавай вопросы по одному и проверяй ответы"
    handle_user_message(prompt, target_language, st.session_state.user["interface_language"], level)
    record_study_session(st.session_state.user["id"], target_language, "test", 8, 5, 0)


def dashboard_page():
    """Главная панель управления"""
    st.title(f"Добро пожаловать, {st.session_state.user['username']}!")

    # Быстрая статистика
    stats = st.session_state.stats.get_user_stats(st.session_state.user["id"])
    streak = st.session_state.stats.get_streak(st.session_state.user["id"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Всего сессий", stats["total_sessions"])
    with col2:
        st.metric("Время обучения", f"{stats['total_time']} мин")
    with col3:
        st.metric("Упражнения", stats["total_exercises"])
    with col4:
        st.metric("Дней подряд", streak)

    # Основной интерфейс
    col_main, col_side = st.columns([2, 1])

    with col_side:
        render_sidebar()

    with col_main:
        render_learning_interface()


def statistics_page():
    """Страница статистики"""
    st.title("📊 Ваша статистика")

    stats = st.session_state.stats.get_user_stats(st.session_state.user["id"])

    # Основные метрики
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Общая статистика")
        st.metric("Всего времени", f"{stats['total_time']} минут")
        st.metric("Сессий обучения", stats['total_sessions'])
        st.metric("Упражнений выполнено", stats['total_exercises'])
        st.metric("Средний балл", f"{stats['avg_score']:.1f}")

    with col2:
        st.subheader("Прогресс по языкам")
        for lang, sessions, time, exercises, score in stats['language_stats']:
            st.write(f"{st.session_state.tutor.target_languages[lang]['flag']} "
                     f"{st.session_state.tutor.target_languages[lang]['name']}: "
                     f"{time} мин, {exercises} упр.")

    # Графики
    if stats['progress_data']:
        st.subheader("Прогресс за 30 дней")
        dates = [item[0] for item in stats['progress_data']]
        times = [item[1] for item in stats['progress_data']]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=times, fill='tozeroy', name='Время обучения (мин)'))
        fig.update_layout(title="Ежедневное время обучения", height=300)
        st.plotly_chart(fig, use_container_width=True)


def login_register_page():
    """Страница входа и регистрации"""
    # Логотип на странице входа
    logo_html = get_logo_html()
    st.markdown(logo_html, unsafe_allow_html=True)

    st.markdown("### Изучайте языки с искусственным интеллектом как ваш личный репетитор!")

    tab1, tab2 = st.tabs(["🔐 Вход", "📝 Регистрация"])

    with tab1:
        with st.form("login_form"):
            st.subheader("Вход в систему")
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")

            if submitted:
                if not username or not password:
                    st.error("Пожалуйста, заполните все поля")
                elif login_user(username, password):
                    st.success(f"Добро пожаловать, {username}!")
                    st.rerun()
                else:
                    st.error("Неверное имя пользователя или пароль")

    with tab2:
        with st.form("register_form"):
            st.subheader("Регистрация")
            col1, col2 = st.columns(2)

            with col1:
                new_username = st.text_input("Имя пользователя*")
                new_email = st.text_input("Email*")
                native_language = st.selectbox(
                    "Родной язык*",
                    options=list(st.session_state.tutor.target_languages.keys()),
                    format_func=lambda
                        x: f"{st.session_state.tutor.target_languages[x]['flag']} {st.session_state.tutor.target_languages[x]['name']}"
                )

            with col2:
                new_password = st.text_input("Пароль*", type="password")
                confirm_password = st.text_input("Подтвердите пароль*", type="password")
                interface_language = st.selectbox(
                    "Язык интерфейса*",
                    options=list(st.session_state.tutor.interface_languages.keys()),
                    format_func=lambda
                        x: f"{st.session_state.tutor.interface_languages[x]['emoji']} {st.session_state.tutor.interface_languages[x]['name']}"
                )

            submitted = st.form_submit_button("Зарегистрироваться")

            if submitted:
                # Валидация
                if not all([new_username, new_email, new_password, confirm_password]):
                    st.error("Пожалуйста, заполните все обязательные поля*")
                elif new_password != confirm_password:
                    st.error("Пароли не совпадают")
                elif len(new_password) < 6:
                    st.error("Пароль должен содержать минимум 6 символов")
                elif not validate_email(new_email):
                    st.error("Пожалуйста, введите корректный email")
                else:
                    if register_user(new_username, new_email, new_password, native_language, interface_language):
                        st.success("Регистрация успешна! Теперь войдите в систему.")
                    else:
                        st.error("Пользователь с таким именем или email уже существует")


def main():
    """Главная функция приложения"""
    st.set_page_config(
        page_title="AI Языковой Репетитор",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS стили для всего приложения
    st.markdown("""
    <style>
    /* Основные стили для кнопок */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        margin: 4px 0 !important;
        width: 100% !important;
    }

    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
    }



    /* Стили для кнопок в формах */
    .stForm button {
        background: linear-gradient(135deg, #00b894 0%, #00a085 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 14px 28px !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }

    .stForm button:hover {
        background: linear-gradient(135deg, #00a085 0%, #00b894 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 184, 148, 0.4) !important;
    }

    /* Адаптивность для мобильных устройств */
    @media (max-width: 768px) {
        .stButton button {
            padding: 14px 16px !important;
            font-size: 14px !important;
        }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
    }

        /* Стили для карточки пользователя */
    .user-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }

    .user-name {
        font-size: 1.2rem;
        font-weight: bold;
    }

    .user-status {
        font-size: 0.8rem;
        opacity: 0.9;
    }


    /* Стили для карточки прогресса */
    .progress-card {
        background: linear-gradient(135deg, #a8e6cf 0%, #dcedc1 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: #2d3436;
        text-align: center;
        border: 1px solid var(--border-color);
    }

    .progress-title {
        font-size: 0.9rem;
        font-weight: bold;
    }

    .progress-stats {
        font-size: 0.8rem;
    }

    /* Стили для логотипа и заголовка */
    .sidebar-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 1.5rem;
    }

    .sidebar-logo-container {
        margin-bottom: 0.5rem;
        position: relative;
    }

    .sidebar-logo-img {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid var(--accent-color);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .sidebar-logo-emoji {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }

    .sidebar-logo-fallback {
        font-size: 3rem;
        margin-bottom: 0.5rem;
        display: none;
    }

    .sidebar-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin: 0;
        color: var(--text-primary);
    }

    .sidebar-subtitle {
        font-size: 0.9rem;
        margin: 0.2rem 0 0 0;
        color: var(--text-secondary);
    }

    /* Стили для метрик и карточек */
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }

    /* Стили для метрик - всегда белый текст */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border-radius: 10px !important;
    padding: 15px !important;
}


    </style>
    """, unsafe_allow_html=True)

    # Инициализация
    init_session_state()

    # Проверка API ключа
    if DEEPSEEK_API_KEY == "sk-your-deepseek-api-key-here":
        st.error("⚠️ Пожалуйста, установите ваш DeepSeek API ключ в переменной DEEPSEEK_API_KEY")
        st.info("Получите ключ на: https://platform.deepseek.com")
        return

    # Навигация
    if st.session_state.user is None:
        login_register_page()
    else:
        # Вкладки для авторизованных пользователей
        tab1, tab2 = st.tabs(["🎓 Обучение", "📊 Статистика"])

        with tab1:
            dashboard_page()

        with tab2:
            statistics_page()


if __name__ == "__main__":
    main()