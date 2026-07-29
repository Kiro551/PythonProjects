from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, SettingsRepository
from keyboards.reply import get_user_main_menu
from keyboards.inline import get_degree_keyboard, get_specialization_keyboard
from states import FeedbackStates, CategorySurveyStates

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
async def send_survey(message: Message):
    settings = await SettingsRepository.get_settings()
    text = settings.get('message_text', 'Текст не задан.')
    link = settings.get('survey_link', 'Ссылка не задана.')
    await message.answer(f"{text}\n\n👉 {link}")


@router.message(F.text == "💬 Обратная связь")
async def start_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer("Напишите ваше сообщение. Для отмены: /start")


# --- ОБРАБОТКА ВЫБОРА КАТЕГОРИЙ ---

@router.callback_query(F.data.startswith("sel_deg_"), CategorySurveyStates.choosing_degree)
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


@router.callback_query(F.data.startswith("sel_spec_"), CategorySurveyStates.choosing_specialization)
async def process_spec_selection(callback: CallbackQuery, state: FSMContext):
    spec_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Сохраняем финальный выбор в БД
    await UserRepository.update_user_category(user_id, spec_id)
    await state.clear()
    
    # Получаем название выбранной категории для красивого сообщения
    from database.repositories import CategoryRepository
    cat_name = await CategoryRepository.get_category_name(spec_id)
    
    await callback.message.edit_text(f"✅ Спасибо! Вы выбрали: **{cat_name}**", parse_mode="Markdown")
    await callback.answer()