from aiogram.fsm.state import State, StatesGroup


class System(StatesGroup):
    default = State()


class ProfileSetup(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()


class FoodLogging(StatesGroup):
    name = State()
    amount = State()
