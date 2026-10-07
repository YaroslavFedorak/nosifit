from aiogram.fsm.state import State, StatesGroup


class RegisterStates(StatesGroup):
    entering_email = State()
    entering_code = State()
