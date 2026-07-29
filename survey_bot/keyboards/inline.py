from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.repositories import CategoryRepository

def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Текст опроса", callback_data="edit_text"),
         InlineKeyboardButton(text="👋 Приветствие", callback_data="edit_welcome")],
        [InlineKeyboardButton(text="🔗 Ссылка", callback_data="edit_link"),
         InlineKeyboardButton(text="⏰ Время рассылки", callback_data="set_time")],
        [InlineKeyboardButton(text="📢 Рассылка опроса по категориям", callback_data="broadcast_survey")]
    ])

async def get_degree_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора степени (Бакалавр/Магистр)"""
    roots = await CategoryRepository.get_root_categories()
    keyboard = []
    for cat_id, name in roots:
        # Callback data: sel_deg_1, sel_deg_2 и т.д.
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"sel_deg_{cat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_specialization_keyboard(parent_id: int) -> InlineKeyboardMarkup:
    """Кнопки выбора факультета/направления"""
    children = await CategoryRepository.get_child_categories(parent_id)
    keyboard = []
    for cat_id, name in children:
        # Callback data: sel_spec_3, sel_spec_4 и т.д.
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"sel_spec_{cat_id}")])
    
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_degrees")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для админа: кому сделать рассылку"""
    roots = await CategoryRepository.get_root_categories()
    keyboard = [
        [InlineKeyboardButton(text="👥 Всем (у кого нет категории)", callback_data="bcast_null")],
        [InlineKeyboardButton(text="🌍 Всем пользователям", callback_data="bcast_all")]
    ]
    # Добавляем корневые категории для точечной рассылки
    for cat_id, name in roots:
        keyboard.append([InlineKeyboardButton(text=f"🎓 Только: {name}", callback_data=f"bcast_cat_{cat_id}")])
        
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)