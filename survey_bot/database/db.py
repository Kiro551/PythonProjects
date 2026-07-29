import aiosqlite
from config import settings

async def init_db():
    async with aiosqlite.connect(settings.DB_NAME) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица настроек опроса
        await db.execute('''
            CREATE TABLE IF NOT EXISTS survey_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                survey_link TEXT,
                message_text TEXT,
                welcome_text TEXT,
                scheduled_time TIMESTAMP
            )
        ''')
        
        # Инициализируем пустую запись настроек, если её нет
        await db.execute('''
            INSERT OR IGNORE INTO survey_settings (id, survey_link, message_text, welcome_text, scheduled_time) 
            VALUES (1, 'Ссылка не задана', 'Текст не задан', 'Добро пожаловать! Я бот для прохождения опросов.', NULL)
        ''')
        
        # === БЕЗОПАСНАЯ МИГРАЦИЯ ===
        # Проверяем, есть ли уже колонка welcome_text (для уже существующих БД)
        cursor = await db.execute("PRAGMA table_info(survey_settings)")
        columns = [row[1] for row in await cursor.fetchall()]
        
        if 'welcome_text' not in columns:
            await db.execute("ALTER TABLE survey_settings ADD COLUMN welcome_text TEXT DEFAULT 'Добро пожаловать! Я бот для прохождения опросов.'")
            print("✅ Миграция БД: добавлена колонка welcome_text")
            
        await db.commit()