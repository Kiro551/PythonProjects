from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    editing_text = State()
    editing_link = State()
    editing_welcome = State()  # <-- НОВОЕ СОСТОЯНИЕ
    setting_time = State()

class FeedbackStates(StatesGroup):
    waiting_for_message = State()