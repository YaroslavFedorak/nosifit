from aiogram.fsm.state import State, StatesGroup


class NutritionStates(StatesGroup):
    choosing_meal = State()
    searching_product = State()
    entering_amount = State()
    reviewing = State()
