from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_user_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Пройти опрос"), KeyboardButton(text="💬 Обратная связь")]
    ], resize_keyboard=True)