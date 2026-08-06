import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.repositories import UserRepository, SettingsRepository
from config import settings as app_settings

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

async def broadcast_survey(bot: Bot):
    """Функция рассылки опроса всем пользователям."""
    settings = await SettingsRepository.get_settings()
    text = settings.get('message_text', 'Текст не задан.')
    link = settings.get('survey_link', 'Ссылка не задана.')
    full_message = f"{text}\n\n👉 {link}"
    
    users = await UserRepository.get_all_non_admin_users() 
    success_count = 0
    
    if not users:
        for admin_id in app_settings.ADMIN_IDS:
            await bot.send_message(admin_id, "⚠️ Рассылка не выполнена: в базе данных нет пользователей.")
        return
        
    for user_id in users:
        try:
            await bot.send_message(user_id, full_message)
            success_count += 1
        except TelegramForbiddenError:
            pass
        except Exception as e:
            logging.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    report_text = f"📊 Рассылка завершена.\nУспешно доставлено: {success_count} из {len(users)}."
    for admin_id in app_settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, report_text)
        except Exception as e:
            logging.error(f"Не удалось отправить отчет админу {admin_id}: {e}")