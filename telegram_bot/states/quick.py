from aiogram.fsm.state import State, StatesGroup


class QuickStates(StatesGroup):
    food_search = State()
    food_amount = State()
    sleep_bed = State()
    sleep_wake = State()
