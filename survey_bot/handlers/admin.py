import csv
import io
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from filters import IsAdmin
from states import AdminStates
from database.repositories import UserRepository, SettingsRepository
from keyboards.inline import get_admin_menu
from scheduler.tasks import scheduler

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    await message.answer("🛠 Админ-панель:", reply_markup=get_admin_menu())

@router.message(Command("users"))
async def cmd_users(message: Message):
    users = await UserRepository.get_all_users()
    count = len(users)
    
    if count == 0:
        await message.answer("Пока нет зарегистрированных пользователей.")
        return

    # Генерируем CSV файл со списком пользователей
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID"])
    for u_id in users:
        writer.writerow([u_id])
    
    file = BufferedInputFile(output.getvalue().encode('utf-8'), filename="users_list.csv")
    await message.answer_document(file, caption=f"Всего пользователей: {count}")

# --- FSM для настроек ---
@router.callback_query(F.data == "edit_text")
async def process_edit_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.editing_text)
    await callback.message.edit_text("Введите новый текст сообщения для рассылки:")

@router.callback_query(F.data == "edit_link")
async def process_edit_link(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.editing_link)
    await callback.message.edit_text("Введите новую ссылку на Google Форму:")

@router.callback_query(F.data == "set_time")
async def process_set_time(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.setting_time)
    await callback.message.edit_text("Введите дату и время рассылки в формате `ГГГГ-ММ-ДД ЧЧ:ММ` (например, 2023-12-31 15:00):", parse_mode="Markdown")

# Обработка ввода данных от админа
@router.message(AdminStates.editing_text)
async def save_text(message: Message, state: FSMContext):
    await SettingsRepository.update_setting('message_text', message.text)
    await state.clear()
    await message.answer("✅ Текст успешно обновлен!", reply_markup=get_admin_menu())

@router.message(AdminStates.editing_link)
async def save_link(message: Message, state: FSMContext):
    await SettingsRepository.update_setting('survey_link', message.text)
    await state.clear()
    await message.answer("✅ Ссылка успешно обновлена!", reply_markup=get_admin_menu())

@router.message(AdminStates.setting_time)
async def save_time(message: Message, state: FSMContext, bot: Bot):
    try:
        # Парсим дату
        dt = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        await SettingsRepository.update_setting('scheduled_time', dt)
        
        # Добавляем задачу в планировщик
        from scheduler.tasks import broadcast_survey
        scheduler.add_job(broadcast_survey, 'date', run_date=dt, args=[bot])
        
        await state.clear()
        await message.answer(f"✅ Рассылка запланирована на {dt.strftime('%d.%m.%Y в %H:%M')}", reply_markup=get_admin_menu())
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте еще раз (ГГГГ-ММ-ДД ЧЧ:ММ):")