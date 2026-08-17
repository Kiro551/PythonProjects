import aiosqlite
from datetime import datetime
from typing import Union, List, Dict, Any, Tuple, Optional
from config import settings


class BaseRepository:
    """Базовый класс с общими методами для работы с БД"""
    
    @staticmethod
    async def _execute_query(query: str, params: tuple = (), fetch_all: bool = False, row_factory=None):
        """Универсальный метод для выполнения SQL-запросов"""
        async with aiosqlite.connect(settings.DB_NAME) as db:
            if row_factory:
                db.row_factory = row_factory
            cursor = await db.execute(query, params)
            await db.commit()
            if fetch_all:
                return await cursor.fetchall()
            elif query.strip().upper().startswith("SELECT"):
                return await cursor.fetchone()
            return None
    
    @staticmethod
    def _filter_admins(base_query: str, params: tuple = ()) -> Tuple[str, tuple]:
        """Фильтрует администраторов из запроса (убирает дублирование)"""
        if not settings.ADMIN_IDS:
            return base_query, params
        
        placeholders = ",".join("?" for _ in settings.ADMIN_IDS)
        filtered_query = f"{base_query} AND user_id NOT IN ({placeholders})"
        filtered_params = params + tuple(settings.ADMIN_IDS)
        return filtered_query, filtered_params


class CategoryRepository(BaseRepository):
    @staticmethod
    async def get_root_categories() -> List[Tuple[int, str]]:
        return await BaseRepository._execute_query(
            "SELECT id, name FROM categories WHERE level = 0",
            fetch_all=True
        )
    
    @staticmethod
    async def get_child_categories(parent_id: int) -> List[Tuple[int, str]]:
        return await BaseRepository._execute_query(
            "SELECT id, name FROM categories WHERE parent_id = ?",
            (parent_id,),
            fetch_all=True
        )
    
    @staticmethod
    async def get_category_name(cat_id: int) -> str:
        row = await BaseRepository._execute_query(
            "SELECT name FROM categories WHERE id = ?",
            (cat_id,)
        )
        return row[0] if row else "Неизвестно"
    
    @staticmethod
    async def get_parent_category(cat_id: int) -> Optional[int]:
        row = await BaseRepository._execute_query(
            "SELECT parent_id FROM categories WHERE id = ?",
            (cat_id,)
        )
        return row[0] if row else None


class CategorySurveyRepository(BaseRepository):
    @staticmethod
    async def get_survey_for_category(category_id: int) -> Optional[Dict[str, str]]:
        row = await BaseRepository._execute_query(
            "SELECT survey_text, survey_link FROM category_surveys WHERE category_id = ?",
            (category_id,),
            row_factory=aiosqlite.Row
        )
        return dict(row) if row else None
    
    @staticmethod
    async def update_survey(category_id: int, survey_text: str, survey_link: str):
        await BaseRepository._execute_query(
            """INSERT INTO category_surveys (category_id, survey_text, survey_link) 
               VALUES (?, ?, ?)
               ON CONFLICT(category_id) DO UPDATE SET 
               survey_text = excluded.survey_text, 
               survey_link = excluded.survey_link""",
            (category_id, survey_text, survey_link)
        )


class UserRepository(BaseRepository):
    @staticmethod
    async def add_user(user_id: int, username: str, first_name: str):
        await BaseRepository._execute_query(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
    
    @staticmethod
    async def update_user_category(user_id: int, category_id: int):
        await BaseRepository._execute_query(
            "UPDATE users SET category_id = ? WHERE user_id = ?",
            (category_id, user_id)
        )
    
    @staticmethod
    async def update_user_course(user_id: int, course: int):
        """Обновляет курс пользователя"""
        await BaseRepository._execute_query(
            "UPDATE users SET course = ? WHERE user_id = ?",
            (course, user_id)
        )
    
    @staticmethod
    async def get_user_category(user_id: int) -> Optional[int]:
        row = await BaseRepository._execute_query(
            "SELECT category_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        return row[0] if row else None
    
    @staticmethod
    async def get_user_course(user_id: int) -> Optional[int]:
        """Получает курс пользователя"""
        row = await BaseRepository._execute_query(
            "SELECT course FROM users WHERE user_id = ?",
            (user_id,)
        )
        return row[0] if row else None
    
    @staticmethod
    async def get_all_non_admin_users() -> List[int]:
        query = "SELECT user_id FROM users WHERE 1=1"
        query, params = BaseRepository._filter_admins(query)
        rows = await BaseRepository._execute_query(query, params, fetch_all=True)
        return [row[0] for row in rows]
    
    @staticmethod
    async def get_users_by_category(category_id: int) -> List[int]:
        query = "SELECT user_id FROM users WHERE category_id = ?"
        query, params = BaseRepository._filter_admins(query, (category_id,))
        rows = await BaseRepository._execute_query(query, params, fetch_all=True)
        return [row[0] for row in rows]
    
    @staticmethod
    async def get_users_without_category() -> List[int]:
        query = "SELECT user_id FROM users WHERE category_id IS NULL"
        query, params = BaseRepository._filter_admins(query)
        rows = await BaseRepository._execute_query(query, params, fetch_all=True)
        return [row[0] for row in rows]
    
    @staticmethod
    async def get_users_by_root_category(root_cat_id: int) -> List[int]:
        """Находит всех пользователей, чья выбранная категория принадлежит корню (степени)"""
        cursor = await BaseRepository._execute_query(
            "SELECT id FROM categories WHERE parent_id = ?",
            (root_cat_id,),
            fetch_all=True
        )
        child_ids = [row[0] for row in cursor]
        
        if not child_ids:
            return []
        
        placeholders = ",".join("?" for _ in child_ids)
        query = f"SELECT user_id FROM users WHERE category_id IN ({placeholders})"
        query, params = BaseRepository._filter_admins(query, tuple(child_ids))
        rows = await BaseRepository._execute_query(query, params, fetch_all=True)
        return [row[0] for row in rows]
    
    @staticmethod
    async def get_all_users_with_status() -> List[Dict[str, Any]]:
        """Получает всех пользователей с детальной информацией о статусе"""
        query = """
            SELECT 
                u.user_id,
                u.username,
                u.first_name,
                u.course,
                u.joined_at,
                parent.name as degree,
                child.name as faculty
            FROM users u
            LEFT JOIN categories child ON u.category_id = child.id
            LEFT JOIN categories parent ON child.parent_id = parent.id
            WHERE 1=1
        """
        query, params = BaseRepository._filter_admins(query)
        rows = await BaseRepository._execute_query(query, params, fetch_all=True, row_factory=aiosqlite.Row)
        return [dict(row) for row in rows]


class SettingsRepository(BaseRepository):
    @staticmethod
    async def get_settings() -> Dict[str, Any]:
        row = await BaseRepository._execute_query(
            "SELECT survey_link, message_text, welcome_text, scheduled_time FROM survey_settings WHERE id = 1",
            row_factory=aiosqlite.Row
        )
        return dict(row) if row else {}
    
    @staticmethod
    async def update_setting(field: str, value: Union[str, datetime, None]):
        await BaseRepository._execute_query(
            f"UPDATE survey_settings SET {field} = ? WHERE id = 1",
            (value,)
        )