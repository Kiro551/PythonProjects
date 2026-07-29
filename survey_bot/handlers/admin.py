import csv
import io
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError

from filters import IsAdmin
from states import AdminStates, AdminBroadcastStates, CategorySurveyStates
from database.repositories import UserRepository, SettingsRepository, CategoryRepository
from keyboards.inline import get_admin_menu, get_broadcast_target_keyboard, get_degree_keyboard
from scheduler.tasks import scheduler

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    await message.answer("🛠 Админ-панель:", reply_markup=get_admin_menu())

@router.message(Command("users"))
async def cmd_users(message: Message):
    users = await UserRepository.get_all_non_admin_users()
    count = len(users)
    if count == 0:
        await message.answer("Пока нет пользователей.")
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID"])
    for u_id in users: writer.writerow([u_id])
    
    file = BufferedInputFile(output.getvalue().encode('utf-8'), filename="users_list.csv")
    await message.answer_document(file, caption=f"Всего пользователей (без админов): {count}")

# --- НАСТРОЙКИ (Без изменений, кроме добавления broadcast) ---
@router.callback_query(F.data == "edit_text")
async def process_edit_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.editing_text)
    await callback.message.edit_text("Введите новый текст опроса:")

@router.callback_query(F.data == "edit_welcome")
async def process_edit_welcome(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.editing_welcome)
    await callback.message.edit_text("Введите новое приветствие:")

@router.callback_query(F.data == "edit_link")
async def process_edit_link(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.editing_link)
    await callback.message.edit_text("Введите новую ссылку:")

@router.callback_query(F.data == "set_time")
async def process_set_time(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.setting_time)
    await callback.message.edit_text("Введите дату и время (ГГГГ-ММ-ДД ЧЧ:ММ):")

@router.message(AdminStates.editing_text)
async def save_text(message: Message, state: FSMContext):
    await SettingsRepository.update_setting('message_text', message.text)
    await state.clear()
    await message.answer("✅ Текст обновлен!", reply_markup=get_admin_menu())

@router.message(AdminStates.editing_welcome)
async def save_welcome(message: Message, state: FSMContext):
    await SettingsRepository.update_setting('welcome_text', message.text)
    await state.clear()
    await message.answer("✅ Приветствие обновлено!", reply_markup=get_admin_menu())

@router.message(AdminStates.editing_link)
async def save_link(message: Message, state: FSMContext):
    await SettingsRepository.update_setting('survey_link', message.text)
    await state.clear()
    await message.answer("✅ Ссылка обновлена!", reply_markup=get_admin_menu())

@router.message(AdminStates.setting_time)
async def save_time(message: Message, state: FSMContext, bot: Bot):
    try:
        dt = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        await SettingsRepository.update_setting('scheduled_time', dt)
        from scheduler.tasks import broadcast_survey
        scheduler.add_job(broadcast_survey, 'date', run_date=dt, args=[bot])
        await state.clear()
        await message.answer(f"✅ Рассылка запланирована на {dt.strftime('%d.%m.%Y в %H:%M')}", reply_markup=get_admin_menu())
    except ValueError:
        await message.answer("❌ Неверный формат.")

# --- НОВАЯ ЛОГИКА: РАССЫЛКА ОПРОСА ПО КАТЕГОРИЯМ ---

@router.callback_query(F.data == "broadcast_survey")
async def start_broadcast_menu(callback: CallbackQuery):
    kb = await get_broadcast_target_keyboard()
    await callback.message.edit_text("📢 Кому отправить опрос по категориям?", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("bcast_"))
async def process_broadcast_target(callback: CallbackQuery, bot: Bot):
    target = callback.data.split("_")[1]
    
    # Определяем список получателей
    if target == "all":
        users = await UserRepository.get_all_non_admin_users()
        target_name = "всем пользователям"
    elif target == "null":
        users = await UserRepository.get_users_without_category()
        target_name = "пользователям без категории"
    elif target == "cat":
        cat_id = int(callback.data.split("_")[2])
        # Для рассылки по корневой категории (Бакалавр/Магистр) 
        # мы должны найти всех, чья specialization (level 1) имеет этот parent_id
        # Для простоты и скорости, давайте брать всех, у кого category_id совпадает с ID корня 
        # ИЛИ чей parent_id равен этому корню. 
        # Но в БД мы храним только level 1 (факультет). 
        # Поэтому нам нужен специальный запрос.
        users = await get_users_by_root_category(cat_id)
        cat_name = await CategoryRepository.get_category_name(cat_id)
        target_name = f"категории: {cat_name}"
    else:
        await callback.answer("Ошибка", show_alert=True)
        return

    if not users:
        await callback.message.edit_text(f"⚠️ Нет пользователей для рассылки ({target_name}).", reply_markup=get_admin_menu())
        await callback.answer()
        return

    # Запускаем саму рассылку
    await callback.message.edit_text(f"🚀 Начинаю рассылку опроса для: {target_name} ({len(users)} чел.)...")
    
    success = 0
    kb = await get_degree_keyboard() # Клавиатура с выбором степени
    text = "🎓 Пожалуйста, пройдите короткий опрос и уточните вашу степень обучения:"
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text, reply_markup=kb)
            success += 1
        except TelegramForbiddenError:
            pass
        except Exception:
            pass
            
    await callback.message.answer(f"✅ Рассылка завершена! Доставлено: {success} из {len(users)}.", reply_markup=get_admin_menu())
    await callback.answer()

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery):
    await callback.message.edit_text("Рассылка отменена.", reply_markup=get_admin_menu())
    await callback.answer()

# Вспомогательная функция для поиска пользователей по корневой категории
async def get_users_by_root_category(root_cat_id: int) -> list[int]:
    """Находит всех пользователей, чья выбранная категория (факультет) принадлежит корню (степени)"""
    async with aiosqlite.connect(settings.DB_NAME) as db:
        # Находим все ID дочерних категорий (факультетов) для данной степени
        cursor = await db.execute("SELECT id FROM categories WHERE parent_id = ?", (root_cat_id,))
        child_ids = [row[0] for row in await cursor.fetchall()]
        
        if not child_ids:
            return []
            
        placeholders = ','.join('?' for _ in child_ids)
        admin_placeholders = ','.join('?' for _ in settings.ADMIN_IDS)
        
        query = f"""
            SELECT user_id FROM users 
            WHERE category_id IN ({placeholders}) 
            AND user_id NOT IN ({admin_placeholders})
        """
        cursor = await db.execute(query, (*child_ids, *settings.ADMIN_IDS))
        return [row[0] for row in await cursor.fetchall()]

# Не забываем импорт для вспомогательной функции
import aiosqlite
from config import settings