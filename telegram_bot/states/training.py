from aiogram.fsm.state import State, StatesGroup


class TrainingStates(StatesGroup):
    # Text is a search query, or one set ("60 10") while an exercise is open.
    active = State()
