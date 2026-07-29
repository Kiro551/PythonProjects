import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.db import init_db
from scheduler.tasks import scheduler

# Импортируем роутеры
from handlers import user, admin, feedback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    await init_db()
    logging.info("База данных готова.")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры (порядок важен! feedback должен быть до user, если есть пересечения, но тут они раздельны)
    dp.include_router(admin.router)
    dp.include_router(feedback.router)
    dp.include_router(user.router)

    # Запускаем планировщик
    scheduler.start()
    logging.info("Планировщик запущен.")

    logging.info("Бот запущен.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        scheduler.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")