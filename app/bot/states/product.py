from aiogram.fsm.state import StatesGroup, State

class ProductState(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_content = State()
