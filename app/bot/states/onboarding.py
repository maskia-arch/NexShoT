from aiogram.fsm.state import StatesGroup, State

class SetupShop(StatesGroup):
    waiting_for_token = State()
