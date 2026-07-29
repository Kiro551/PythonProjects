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
                category_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        ''')
        
        # Таблица настроек
        await db.execute('''
            CREATE TABLE IF NOT EXISTS survey_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                survey_link TEXT,
                message_text TEXT,
                welcome_text TEXT,
                scheduled_time TIMESTAMP
            )
        ''')
        await db.execute('''
            INSERT OR IGNORE INTO survey_settings (id, survey_link, message_text, welcome_text, scheduled_time) 
            VALUES (1, 'Ссылка не задана', 'Текст не задан', 'Добро пожаловать!', NULL)
        ''')

        # Таблица категорий
        await db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                level INTEGER DEFAULT 0, 
                FOREIGN KEY(parent_id) REFERENCES categories(id)
            )
        ''')

        # НОВАЯ Таблица опросов по категориям
        await db.execute('''
            CREATE TABLE IF NOT EXISTS category_surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER UNIQUE,
                survey_text TEXT,
                survey_link TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        ''')

        # === МИГРАЦИИ ===
        cursor = await db.execute("PRAGMA table_info(users)")
        if 'category_id' not in [row[1] for row in await cursor.fetchall()]:
            await db.execute("ALTER TABLE users ADD COLUMN category_id INTEGER")
            print("✅ Миграция: добавлена колонка category_id в users")

        cursor = await db.execute("PRAGMA table_info(survey_settings)")
        if 'welcome_text' not in [row[1] for row in await cursor.fetchall()]:
            await db.execute("ALTER TABLE survey_settings ADD COLUMN welcome_text TEXT DEFAULT 'Добро пожаловать!'")

        # === ЗАПОЛНЕНИЕ КАТЕГОРИЙ ПО УМОЛЧАНИЮ ===
        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        count = (await cursor.fetchone())[0]
        
        if count == 0:
            print("🌱 База категорий пуста. Заполняем начальными данными...")
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Бакалавриат', NULL, 0)")
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Магистратура', NULL, 0)")
            
            cursor = await db.execute("SELECT id, name FROM categories WHERE level = 0")
            degrees = {row[1]: row[0] for row in await cursor.fetchall()}
            
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Факультет 1', ?, 1)", (degrees['Бакалавриат'],))
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Факультет 2', ?, 1)", (degrees['Бакалавриат'],))
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Направление 1', ?, 1)", (degrees['Магистратура'],))
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Направление 2', ?, 1)", (degrees['Магистратура'],))
            print("✅ Категории успешно созданы!")

        await db.commit()