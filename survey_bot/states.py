from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    editing_text = State()
    editing_link = State()
    setting_time = State()  # Ожидает формат ГГГГ-ММ-ДД ЧЧ:ММ

class FeedbackStates(StatesGroup):
    waiting_for_message = State()