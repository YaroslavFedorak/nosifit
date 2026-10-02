from aiogram.fsm.state import State, StatesGroup


class NutritionStates(StatesGroup):
    choosing_meal = State()
    browsing_catalog = State()
    searching_product = State()
    entering_amount = State()
    reviewing = State()
    saving = State()
    product_name = State()
    product_kcal = State()
    product_protein = State()
    product_fat = State()
    product_carbs = State()
