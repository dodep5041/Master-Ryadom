
from aiogram.fsm.state import State, StatesGroup


class ApplicationStates(StatesGroup):
    choosing_service = State()
    entering_description = State()
    uploading_photo = State()
    entering_city = State()
    entering_district = State()
    entering_name = State()
    entering_contact = State()
    accepting_privacy = State()
