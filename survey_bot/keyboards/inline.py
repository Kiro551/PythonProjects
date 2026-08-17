from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.repositories import CategoryRepository

def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Текст опроса", callback_data="edit_text"),
         InlineKeyboardButton(text="👋 Приветствие", callback_data="edit_welcome")],
        [InlineKeyboardButton(text="🔗 Ссылка", callback_data="edit_link"),
         InlineKeyboardButton(text="⏰ Время рассылки", callback_data="set_time")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast_menu")],
        [InlineKeyboardButton(text="🎓 Опросы по категориям", callback_data="category_surveys_menu")]
    ])

async def get_degree_keyboard() -> InlineKeyboardMarkup:
    roots = await CategoryRepository.get_root_categories()
    keyboard = []
    for cat_id, name in roots:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"sel_deg_{cat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_specialization_keyboard(parent_id: int) -> InlineKeyboardMarkup:
    children = await CategoryRepository.get_child_categories(parent_id)
    keyboard = []
    for cat_id, name in children:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"sel_spec_{cat_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_degrees")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Уточнить данные студентов", callback_data="bcast_type_survey")],
        [InlineKeyboardButton(text="✉️ Кастомный опрос", callback_data="bcast_type_custom")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
    ])

async def get_broadcast_target_keyboard(broadcast_type: str) -> InlineKeyboardMarkup:
    roots = await CategoryRepository.get_root_categories()
    keyboard = [
        [InlineKeyboardButton(text="👥 Всем (у кого нет категории)", callback_data=f"bcast_target_null_{broadcast_type}")],
        [InlineKeyboardButton(text="🌍 Всем пользователям", callback_data=f"bcast_target_all_{broadcast_type}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
    ]
    for cat_id, name in roots:
        keyboard.append([InlineKeyboardButton(text=f"🎓 Только: {name}", callback_data=f"bcast_target_cat_{cat_id}_{broadcast_type}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_category_surveys_menu() -> InlineKeyboardMarkup:
    """Меню выбора категории для настройки опроса"""
    roots = await CategoryRepository.get_root_categories()
    keyboard = []
    for cat_id, name in roots:
        keyboard.append([InlineKeyboardButton(text=f"🎓 {name}", callback_data=f"cat_survey_{cat_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_course_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора курса обучения"""
    builder = InlineKeyboardBuilder()
    for course in range(1, 5):  # Курсы от 1 до 4
        builder.button(text=f"{course} курс", callback_data=f"sel_course_{course}")
    builder.adjust(2)
    return builder.as_markup()

def get_category_survey_edit_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Кнопки редактирования опроса для конкретной категории"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_cat_survey_text_{category_id}")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data=f"edit_cat_survey_link_{category_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="category_surveys_menu")]
    ])

def get_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить текст опроса", callback_data="edit_text")
    builder.button(text="✏️ Изменить приветствие", callback_data="edit_welcome")
    builder.button(text="🔗 Изменить ссылку", callback_data="edit_link")
    builder.button(text="⏰ Установить время рассылки", callback_data="set_time")
    builder.button(text="📢 Рассылка", callback_data="broadcast_menu")
    builder.button(text="🎓 Опросы по категориям", callback_data="category_surveys_menu")
    builder.button(text="📊 Статус пользователей", callback_data="users_status_menu")  # НОВАЯ КНОПКА
    builder.adjust(1)
    return builder.as_markup()