import csv
import io
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from database.repositories import CategorySurveyRepository

from filters import IsAdmin
from states import AdminStates, AdminBroadcastStates, CategorySurveyStates
from database.repositories import UserRepository, SettingsRepository, CategoryRepository
from keyboards.inline import (
    get_admin_menu, 
    get_broadcast_type_keyboard, 
    get_broadcast_target_keyboard,
    get_degree_keyboard
)
from scheduler.tasks import scheduler
import aiosqlite
from config import settings

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
    for u_id in users:
        writer.writerow([u_id])
    
    file = BufferedInputFile(output.getvalue().encode('utf-8'), filename="users_list.csv")
    await message.answer_document(file, caption=f"Всего пользователей (без админов): {count}")

# --- НАСТРОЙКИ ---
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

# --- НОВАЯ ЛОГИКА: РАССЫЛКА С ДВУМЯ РЕЖИМАМИ ---

@router.callback_query(F.data == "broadcast_menu")
async def start_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню выбора типа рассылки"""
    await state.set_state(AdminBroadcastStates.choosing_type)
    kb = get_broadcast_type_keyboard()
    await callback.message.edit_text("📢 Выберите тип рассылки:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("bcast_type_"), AdminBroadcastStates.choosing_type)
async def process_broadcast_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа рассылки и показывает выбор категорий"""
    broadcast_type = callback.data.split("_")[2]  # 'survey' или 'custom'
    
    # Сохраняем тип рассылки в FSM
    await state.update_data(broadcast_type=broadcast_type)
    await state.set_state(AdminBroadcastStates.waiting_for_target_category)
    
    kb = await get_broadcast_target_keyboard(broadcast_type)
    
    if broadcast_type == "survey":
        text = "🔄 Кому отправить опрос для уточнения данных?"
    else:
        text = "✉️ Кому отправить кастомный опрос?"
    
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("bcast_target_"), AdminBroadcastStates.waiting_for_target_category)
async def process_broadcast_target(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обрабатывает выбор целевой категории и запускает рассылку"""
    parts = callback.data.split("_")
    target = parts[2]  # 'all', 'null', 'cat'
    broadcast_type = parts[-1]  # 'survey' или 'custom'
    
    # Определяем список получателей
    if target == "all":
        users = await UserRepository.get_all_non_admin_users()
        target_name = "всем пользователям"
    elif target == "null":
        users = await UserRepository.get_users_without_category()
        target_name = "пользователям без категории"
    elif target == "cat":
        cat_id = int(parts[3])
        users = await get_users_by_root_category(cat_id)
        cat_name = await CategoryRepository.get_category_name(cat_id)
        target_name = f"категории: {cat_name}"
    else:
        await callback.answer("Ошибка", show_alert=True)
        return

    if not users:
        await callback.message.edit_text(f"⚠️ Нет пользователей для рассылки ({target_name}).", reply_markup=get_admin_menu())
        await state.clear()
        await callback.answer()
        return

    # Сохраняем список пользователей в FSM
    await state.update_data(target_users=users, target_name=target_name)
    
    if broadcast_type == "survey":
        # Режим "Уточнить данные" — сразу запускаем рассылку опроса
        await callback.message.edit_text(f"🚀 Начинаю рассылку опроса для: {target_name} ({len(users)} чел.)...")
        await perform_survey_broadcast(bot, users, target_name, callback.message)
    else:
        # Режим "Кастомный опрос" — просим ввести текст
        await state.set_state(AdminBroadcastStates.waiting_for_custom_text)
        await callback.message.edit_text(f"✉️ Введите текст кастомного опроса для: {target_name} ({len(users)} чел.):")
    
    await callback.answer()

@router.message(AdminBroadcastStates.waiting_for_custom_text)
async def process_custom_text(message: Message, state: FSMContext, bot: Bot):
    """Получает кастомный текст и запускает рассылку"""
    custom_text = message.text
    
    # Получаем данные из FSM
    data = await state.get_data()
    users = data.get('target_users', [])
    target_name = data.get('target_name', 'неизвестно')
    
    await message.answer(f"🚀 Начинаю рассылку кастомного опроса для: {target_name} ({len(users)} чел.)...")
    
    await perform_custom_broadcast(bot, users, custom_text, target_name, message)
    await state.clear()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАССЫЛКИ ---

async def perform_survey_broadcast(bot: Bot, users: list, target_name: str, status_message: Message):
    """Рассылка стандартного опроса с кнопками категорий"""
    success = 0
    kb = await get_degree_keyboard()
    text = "🎓 Пожалуйста, пройдите короткий опрос и уточните вашу степень обучения:"
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text, reply_markup=kb)
            success += 1
        except TelegramForbiddenError:
            pass
        except Exception:
            pass
    
    await status_message.answer(f"✅ Рассылка опроса завершена! Доставлено: {success} из {len(users)}.", reply_markup=get_admin_menu())

async def perform_custom_broadcast(bot: Bot, users: list, custom_text: str, target_name: str, status_message: Message):
    """Рассылка кастомного текста"""
    success = 0
    
    for user_id in users:
        try:
            await bot.send_message(user_id, custom_text)
            success += 1
        except TelegramForbiddenError:
            pass
        except Exception:
            pass
    
    await status_message.answer(f"✅ Кастомная рассылка завершена! Доставлено: {success} из {len(users)}.", reply_markup=get_admin_menu())

async def get_users_by_root_category(root_cat_id: int) -> list[int]:
    """Находит всех пользователей, чья выбранная категория принадлежит корню (степени)"""
    async with aiosqlite.connect(settings.DB_NAME) as db:
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

# --- НАСТРОЙКА ОПРОСОВ ПО КАТЕГОРИЯМ ---

@router.callback_query(F.data == "category_surveys_menu")
async def show_category_surveys_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = await get_category_surveys_menu()
    await callback.message.edit_text("🎓 Выберите категорию для настройки опроса:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 Админ-панель:", reply_markup=get_admin_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("cat_survey_"))
async def show_category_survey_edit(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[2])
    cat_name = await CategoryRepository.get_category_name(cat_id)
    
    # Сохраняем ID категории в FSM
    await state.update_data(editing_category_id=cat_id)
    
    # Получаем текущий опрос
    survey = await CategorySurveyRepository.get_survey_for_category(cat_id)
    
    if survey:
        text = f"🎓 Опрос для категории: **{cat_name}**\n\n"
        text += f"📝 Текст: {survey.get('survey_text', 'Не задан')}\n"
        text += f"🔗 Ссылка: {survey.get('survey_link', 'Не задана')}"
    else:
        text = f"🎓 Опрос для категории: **{cat_name}**\n\n⚠️ Опрос еще не настроен."
    
    kb = get_category_survey_edit_keyboard(cat_id)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_cat_survey_text_"))
async def start_edit_category_survey_text(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[4])
    await state.update_data(editing_category_id=cat_id)
    await state.set_state(AdminStates.editing_category_survey_text)
    await callback.message.edit_text("Введите новый текст опроса для этой категории:")
    await callback.answer()

@router.callback_query(F.data.startswith("edit_cat_survey_link_"))
async def start_edit_category_survey_link(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[4])
    await state.update_data(editing_category_id=cat_id)
    await state.set_state(AdminStates.editing_category_survey_link)
    await callback.message.edit_text("Введите новую ссылку на Google Форму для этой категории:")
    await callback.answer()

@router.message(AdminStates.editing_category_survey_text)
async def save_category_survey_text(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get('editing_category_id')
    
    if not cat_id:
        await message.answer("❌ Ошибка: категория не выбрана.")
        await state.clear()
        return
    
    # Получаем текущую ссылку
    survey = await CategorySurveyRepository.get_survey_for_category(cat_id)
    current_link = survey.get('survey_link', '') if survey else ''
    
    # Сохраняем новый текст
    await CategorySurveyRepository.update_survey(cat_id, message.text, current_link)
    await state.clear()
    
    cat_name = await CategoryRepository.get_category_name(cat_id)
    await message.answer(f"✅ Текст опроса для **{cat_name}** обновлен!", parse_mode="Markdown", reply_markup=get_category_survey_edit_keyboard(cat_id))

@router.message(AdminStates.editing_category_survey_link)
async def save_category_survey_link(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data.get('editing_category_id')
    
    if not cat_id:
        await message.answer("❌ Ошибка: категория не выбрана.")
        await state.clear()
        return
    
    # Получаем текущий текст
    survey = await CategorySurveyRepository.get_survey_for_category(cat_id)
    current_text = survey.get('survey_text', '') if survey else ''
    
    # Сохраняем новую ссылку
    await CategorySurveyRepository.update_survey(cat_id, current_text, message.text)
    await state.clear()
    
    cat_name = await CategoryRepository.get_category_name(cat_id)
    await message.answer(f"✅ Ссылка опроса для **{cat_name}** обновлена!", parse_mode="Markdown", reply_markup=get_category_survey_edit_keyboard(cat_id))

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.", reply_markup=get_admin_menu())
    await callback.answer()