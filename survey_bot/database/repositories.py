import aiosqlite
from datetime import datetime
from typing import Union, List, Dict, Any
from config import settings

class UserRepository:
    @staticmethod
    async def add_user(user_id: int, username: str, first_name: str):
        async with aiosqlite.connect(settings.DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            await db.commit()

    @staticmethod
    async def get_all_users() -> List[int]:
        async with aiosqlite.connect(settings.DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]

    @staticmethod
    async def get_users_count() -> int:
        async with aiosqlite.connect(settings.DB_NAME) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0] if row else 0


class SettingsRepository:
    @staticmethod
    async def get_settings() -> Dict[str, Any]:
        async with aiosqlite.connect(settings.DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT survey_link, message_text, scheduled_time FROM survey_settings WHERE id = 1")
            row = await cursor.fetchone()
            return dict(row) if row else {}

    @staticmethod
    async def update_setting(field: str, value: Union[str, datetime, None]):
        async with aiosqlite.connect(settings.DB_NAME) as db:
            await db.execute(f"UPDATE survey_settings SET {field} = ? WHERE id = 1", (value,))
            await db.commit()