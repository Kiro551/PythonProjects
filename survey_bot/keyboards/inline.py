from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст", callback_data="edit_text"),
         InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data="edit_link")],
        [InlineKeyboardButton(text="⏰ Задать время рассылки", callback_data="set_time")]
    ])