from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    entering_email = State()
    entering_password = State()
