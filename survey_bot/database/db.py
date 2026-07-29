import aiosqlite
from config import settings

async def init_db():
    async with aiosqlite.connect(settings.DB_NAME) as db:
        # 1. Таблица пользователей (добавляем category_id)
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
        
        # 2. Таблица настроек (без изменений)
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

        # 3. НОВАЯ Таблица категорий (иерархическая)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                level INTEGER DEFAULT 0, 
                FOREIGN KEY(parent_id) REFERENCES categories(id)
            )
        ''')
        
        # === МИГРАЦИИ ===
        # Добавляем category_id, если её нет
        cursor = await db.execute("PRAGMA table_info(users)")
        if 'category_id' not in [row[1] for row in await cursor.fetchall()]:
            await db.execute("ALTER TABLE users ADD COLUMN category_id INTEGER")
            print("✅ Миграция: добавлена колонка category_id в users")

        # === ЗАПОЛНЕНИЕ КАТЕГОРИЙ ПО УМОЛЧАНИЮ ===
        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        count = (await cursor.fetchone())[0]
        
        if count == 0:
            print("🌱 База категорий пуста. Заполняем начальными данными...")
            # Уровень 0: Корневые (Степени)
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Бакалавриат', NULL, 0)")
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Магистратура', NULL, 0)")
            
            # Получаем ID степеней
            cursor = await db.execute("SELECT id, name FROM categories WHERE level = 0")
            degrees = {row[1]: row[0] for row in await cursor.fetchall()}
            
            # Уровень 1: Факультеты и Направления
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Факультет 1', ?, 1)", (degrees['Бакалавриат'],))
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Факультет 2', ?, 1)", (degrees['Бакалавриат'],))
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Направление 1', ?, 1)", (degrees['Магистратура'],))
            await db.execute("INSERT INTO categories (name, parent_id, level) VALUES ('Направление 2', ?, 1)", (degrees['Магистратура'],))
            
            print("✅ Категории успешно созданы!")

        # Миграция welcome_text (из прошлого шага)
        cursor = await db.execute("PRAGMA table_info(survey_settings)")
        if 'welcome_text' not in [row[1] for row in await cursor.fetchall()]:
            await db.execute("ALTER TABLE survey_settings ADD COLUMN welcome_text TEXT DEFAULT 'Добро пожаловать!'")
            
        await db.commit()