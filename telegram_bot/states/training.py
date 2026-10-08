from aiogram.fsm.state import State, StatesGroup


class TrainingStates(StatesGroup):
    searching = State()  # text: exercise name
    weight = State()  # text: kg
    count = State()  # text: reps or seconds
