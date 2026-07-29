import aiosqlite
from datetime import datetime
from typing import Union, List, Dict, Any, Tuple
from config import settings
from typing import Optional

class CategoryRepository:
    @staticmethod
    async def get_root_categories() -> List[Tuple[int, str]]:
        """Получить корневые категории (Бакалавриат, Магистратура)"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            cursor = await db.execute("SELECT id, name FROM categories WHERE level = 0")
            return await cursor.fetchall()

    @staticmethod
    async def get_child_categories(parent_id: int) -> List[Tuple[int, str]]:
        """Получить дочерние категории (Факультеты/Направления)"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            cursor = await db.execute("SELECT id, name FROM categories WHERE parent_id = ?", (parent_id,))
            return await cursor.fetchall()

    @staticmethod
    async def get_all_categories() -> List[Tuple[int, str, int]]:
        """Получить все категории (id, name, level)"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            cursor = await db.execute("SELECT id, name, level FROM categories")
            return await cursor.fetchall()

    @staticmethod
    async def get_category_name(cat_id: int) -> str:
        async with aiosqlite.connect(settings.DB_NAME) as db:
            cursor = await db.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
            row = await cursor.fetchone()
            return row[0] if row else "Неизвестно"

class UserRepository:
    @staticmethod
    async def get_user_category(user_id: int) -> Optional[int]:
        """Возвращает ID категории пользователя или None, если она не выбрана"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            cursor = await db.execute("SELECT category_id FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            # row[0] будет None, если колонка пустая
            return row[0] if row else None
        
    @staticmethod
    async def add_user(user_id: int, username: str, first_name: str):
        async with aiosqlite.connect(settings.DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            await db.commit()

    @staticmethod
    async def update_user_category(user_id: int, category_id: int):
        async with aiosqlite.connect(settings.DB_NAME) as db:
            await db.execute("UPDATE users SET category_id = ? WHERE user_id = ?", (category_id, user_id))
            await db.commit()

    @staticmethod
    async def get_all_non_admin_users() -> List[int]:
        """Все пользователи, кроме админов"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            # Исключаем ID админов из списка
            placeholders = ','.join('?' for _ in settings.ADMIN_IDS)
            query = f"SELECT user_id FROM users WHERE user_id NOT IN ({placeholders})"
            cursor = await db.execute(query, settings.ADMIN_IDS)
            return [row[0] for row in await cursor.fetchall()]

    @staticmethod
    async def get_users_by_category(category_id: int) -> List[int]:
        """Пользователи конкретной категории (исключая админов)"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            placeholders = ','.join('?' for _ in settings.ADMIN_IDS)
            query = f"SELECT user_id FROM users WHERE category_id = ? AND user_id NOT IN ({placeholders})"
            cursor = await db.execute(query, (category_id, *settings.ADMIN_IDS))
            return [row[0] for row in await cursor.fetchall()]

    @staticmethod
    async def get_users_without_category() -> List[int]:
        """Пользователи, которые еще не выбрали категорию"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            placeholders = ','.join('?' for _ in settings.ADMIN_IDS)
            query = f"SELECT user_id FROM users WHERE category_id IS NULL AND user_id NOT IN ({placeholders})"
            cursor = await db.execute(query, settings.ADMIN_IDS)
            return [row[0] for row in await cursor.fetchall()]

class SettingsRepository:
    @staticmethod
    async def get_settings() -> Dict[str, Any]:
        async with aiosqlite.connect(settings.DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT survey_link, message_text, welcome_text, scheduled_time FROM survey_settings WHERE id = 1")
            row = await cursor.fetchone()
            return dict(row) if row else {}

    @staticmethod
    async def update_setting(field: str, value: Union[str, datetime, None]):
        async with aiosqlite.connect(settings.DB_NAME) as db:
            await db.execute(f"UPDATE survey_settings SET {field} = ? WHERE id = 1", (value,))
            await db.commit()