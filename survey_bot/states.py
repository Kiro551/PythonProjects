from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    editing_text = State()
    editing_link = State()
    editing_welcome = State()
    setting_time = State()

class FeedbackStates(StatesGroup):
    waiting_for_message = State()

# НОВЫЕ СОСТОЯНИЯ
class CategorySurveyStates(StatesGroup):
    choosing_degree = State()
    choosing_specialization = State()

class AdminBroadcastStates(StatesGroup):
    waiting_for_target_category = State() # Ожидание выбора категории для рассылки