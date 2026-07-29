from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database.repositories import UserRepository, SettingsRepository
from keyboards.reply import get_user_main_menu
from states import FeedbackStates

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Добавляем в БД (если пользователя уже нет, он добавится; если есть — проигнорируется)
    await UserRepository.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "unknown",
        first_name=message.from_user.first_name or "unknown"
    )
    
    # <-- ИЗМЕНЕНИЕ: Берем приветствие из БД -->
    settings = await SettingsRepository.get_settings()
    welcome_text = settings.get('welcome_text', 'Добро пожаловать! Я бот для прохождения опросов.')
    
    await message.answer(welcome_text, reply_markup=get_user_main_menu())

@router.message(F.text == "📝 Пройти опрос")
async def send_survey(message: Message):
    settings = await SettingsRepository.get_settings()
    text = settings.get('message_text', 'Текст не задан администратором.')
    link = settings.get('survey_link', 'Ссылка не задана администратором.')
    
    await message.answer(f"{text}\n\n👉 {link}")

@router.message(F.text == "💬 Обратная связь")
async def start_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer("Напишите ваше сообщение или опишите проблему. Чтобы отменить, нажмите /start.")