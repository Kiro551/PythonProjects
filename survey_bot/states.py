from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    editing_text = State()
    editing_link = State()
    editing_welcome = State()
    setting_time = State()

class FeedbackStates(StatesGroup):
    waiting_for_message = State()

class CategorySurveyStates(StatesGroup):
    choosing_degree = State()
    choosing_specialization = State()

class AdminBroadcastStates(StatesGroup):
    choosing_type = State()              # Выбор типа рассылки
    waiting_for_target_category = State() # Выбор категории
    waiting_for_custom_text = State()     # Ожидание ввода кастомного текста