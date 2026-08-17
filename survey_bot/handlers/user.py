from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, SettingsRepository
from keyboards.reply import get_user_main_menu
from keyboards.inline import get_degree_keyboard, get_specialization_keyboard, get_course_keyboard
from states import FeedbackStates, CategorySurveyStates
from database.repositories import CategorySurveyRepository, CategoryRepository

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # 1. Добавляем/обновляем пользователя в БД
    await UserRepository.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "unknown",
        first_name=message.from_user.first_name or "unknown"
    )
    
    # 2. Получаем настройки
    settings = await SettingsRepository.get_settings()
    welcome_text = settings.get('welcome_text', 'Добро пожаловать!')
    
    # 3. Проверяем, выбрал ли пользователь категорию
    user_category = await UserRepository.get_user_category(message.from_user.id)
    
    if user_category is None:
        # Если категория НЕ выбрана - сразу запускаем опрос по категориям
        await message.answer(welcome_text)
        await start_category_survey(message, state)
    else:
        # Если категория УЖЕ выбрана - просто показываем приветствие и меню
        await message.answer(welcome_text, reply_markup=get_user_main_menu())

async def start_category_survey(message_or_query, state: FSMContext):
    """Универсальная функция запуска опроса по категориям"""
    await state.set_state(CategorySurveyStates.choosing_degree)
    kb = await get_degree_keyboard()
    
    text = "🎓 Пожалуйста, уточните вашу степень обучения:"
    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(text, reply_markup=kb)
    else:
        await message_or_query.answer(text, reply_markup=kb)

@router.message(F.text == "📝 Пройти опрос")
async def send_survey(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Получаем категорию пользователя
    user_category = await UserRepository.get_user_category(user_id)
    
    if user_category is None:
        # У пользователя нет категории — предлагаем уточнить данные
        await message.answer("📋 Пожалуйста, уточните ваши данные, чтобы мы могли подобрать подходящий опрос.")
        await start_category_survey(message, state)
        return
    
    # Определяем корневую категорию (степень)
    parent_cat_id = await CategoryRepository.get_parent_category(user_category)
    root_cat_id = parent_cat_id if parent_cat_id else user_category
    
    # Получаем опрос для этой категории
    survey = await CategorySurveyRepository.get_survey_for_category(root_cat_id)
    
    if not survey or not survey.get('survey_text') or not survey.get('survey_link'):
        # Опрос не настроен
        await message.answer("⚠️ Нет опросов для прохождения.")
        return
    
    # Отправляем опрос
    text = survey['survey_text']
    link = survey['survey_link']
    await message.answer(f"{text}\n\n👉 {link}")

@router.message(F.text == "💬 Обратная связь")
async def start_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer("Напишите ваше сообщение. Для отмены: /start")

# --- ОБРАБОТКА ВЫБОРА КАТЕГОРИЙ ---

@router.callback_query(F.data.startswith("sel_deg_"))
async def process_degree_selection(callback: CallbackQuery, state: FSMContext):
    degree_id = int(callback.data.split("_")[2])
    
    await state.update_data(degree_id=degree_id)
    await state.set_state(CategorySurveyStates.choosing_specialization)
    
    kb = await get_specialization_keyboard(degree_id)
    await callback.message.edit_text("🏛 Выберите ваш факультет / направление:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "back_to_degrees", CategorySurveyStates.choosing_specialization)
async def back_to_degrees(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CategorySurveyStates.choosing_degree)
    kb = await get_degree_keyboard()
    await callback.message.edit_text("🎓 Пожалуйста, уточните вашу степень обучения:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("sel_spec_"))
async def process_spec_selection(callback: CallbackQuery, state: FSMContext):
    spec_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Сохраняем финальный выбор категории в БД
    await UserRepository.update_user_category(user_id, spec_id)
    
    # Переходим к выбору курса
    await state.update_data(spec_id=spec_id)
    await state.set_state(CategorySurveyStates.choosing_course)
    
    kb = await get_course_keyboard()
    await callback.message.edit_text("📚 Выберите ваш курс обучения:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("sel_course_"), CategorySurveyStates.choosing_course)
async def process_course_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор курса и завершает опрос"""
    course = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Сохраняем курс в БД
    await UserRepository.update_user_course(user_id, course)
    await state.clear()
    
    # Получаем данные для красивого сообщения
    data = await state.get_data()
    spec_id = data.get('spec_id')
    cat_name = await CategoryRepository.get_category_name(spec_id) if spec_id else "Неизвестно"

    await callback.message.edit_text(
        f"✅ Спасибо! Ваши данные сохранены:\n"
        f"🎓 Факультет: <b>{cat_name}</b>\n"
        f"📚 Курс: <b>{course}</b>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_specs", CategorySurveyStates.choosing_course)
async def back_to_specs(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору факультета"""
    await state.set_state(CategorySurveyStates.choosing_specialization)
    data = await state.get_data()
    degree_id = data.get('degree_id')
    kb = await get_specialization_keyboard(degree_id)
    await callback.message.edit_text("🏛 Выберите ваш факультет / направление:", reply_markup=kb)
    await callback.answer()