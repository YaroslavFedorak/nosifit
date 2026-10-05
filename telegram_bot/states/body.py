from aiogram.fsm.state import State, StatesGroup


class WaterStates(StatesGroup):
    entering_amount = State()


class WeightStates(StatesGroup):
    entering_weight = State()
