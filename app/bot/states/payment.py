from aiogram.fsm.state import StatesGroup, State

class PaymentState(StatesGroup):
    waiting_for_address = State()

class CheckoutState(StatesGroup):
    waiting_for_payment_method = State()
    waiting_for_customer_address = State()
    confirm_order = State()
