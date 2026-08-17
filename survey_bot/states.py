from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    editing_text = State()
    editing_link = State()
    editing_welcome = State()
    setting_time = State()
    editing_category_survey_text = State()
    editing_category_survey_link = State()

class FeedbackStates(StatesGroup):
    waiting_for_message = State()

class CategorySurveyStates(StatesGroup):
    choosing_degree = State()
    choosing_specialization = State()
    choosing_course = State()  

class AdminBroadcastStates(StatesGroup):
    choosing_type = State()
    waiting_for_target_category = State()
    waiting_for_custom_text = State()