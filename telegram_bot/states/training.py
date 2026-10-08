from aiogram.fsm.state import State, StatesGroup


class TrainingStates(StatesGroup):
    searching = State()  # text: exercise name
    sets = State()  # text: how many sets
    count = State()  # text: reps or seconds of the current set
    weight = State()  # text: kg of the current set
