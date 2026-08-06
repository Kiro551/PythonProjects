import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(ENV_PATH)

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int]
    DB_NAME: str = "survey_bot.db"

    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        elif isinstance(v, int):
            return [v]
        elif isinstance(v, list):
            return [int(x) for x in v]
        return v

    model_config = SettingsConfigDict(env_file=ENV_PATH, env_file_encoding='utf-8')

settings = Settings()

# Cколько админов загрузилось + их ID
print(f"✅ Настройки загружены. Администраторов в системе: {len(settings.ADMIN_IDS)}")
print(f"   Список ID админов: {settings.ADMIN_IDS}")