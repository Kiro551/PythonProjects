from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст опроса", callback_data="edit_text"),
         InlineKeyboardButton(text="👋 Изменить приветствие", callback_data="edit_welcome")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data="edit_link"),
         InlineKeyboardButton(text="⏰ Задать время рассылки", callback_data="set_time")]
    ])