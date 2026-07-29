import re
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states import FeedbackStates
from config import settings
from filters import IsAdmin  # <-- Импортируем наш фильтр
from keyboards.reply import get_user_main_menu

router = Router()

# 1. Студент отправляет сообщение
@router.message(FeedbackStates.waiting_for_message)
async def process_feedback(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    user_id = message.from_user.id
    
    admin_text = f"📩 Сообщение от {username} (ID: {user_id}):\n\n{message.text}"
    
    # Отправляем сообщение ВСЕМ админам из списка
    for admin_id in settings.ADMIN_IDS:
        await bot.send_message(admin_id, admin_text)
        
    await message.answer("Спасибо! Ваше сообщение передано администратору.", reply_markup=get_user_main_menu())

# 2. Админ отвечает на сообщение студента
# ИСПРАВЛЕНИЕ: Используем готовый фильтр IsAdmin() вместо сравнения со списком
@router.message(F.reply_to_message, IsAdmin())
async def admin_reply(message: Message, bot: Bot):
    replied_msg = message.reply_to_message
    
    # Проверяем, что админ отвечает именно на сообщение обратной связи (ищем паттерн ID)
    if replied_msg.text and "ID:" in replied_msg.text:
        match = re.search(r"ID: (\d+)", replied_msg.text)
        if match:
            target_user_id = int(match.group(1))
            try:
                await bot.send_message(target_user_id, f"💬 Ответ от администратора:\n\n{message.text}")
                await message.answer("✅ Ответ успешно отправлен пользователю.")
            except Exception as e:
                await message.answer(f"❌ Не удалось отправить ответ (возможно, пользователь заблокировал бота). Ошибка: {e}")
            return
            
    await message.answer("⚠️ Это не похоже на сообщение обратной связи. Ответьте на сообщение, начинающееся с '📩 Сообщение от...'")