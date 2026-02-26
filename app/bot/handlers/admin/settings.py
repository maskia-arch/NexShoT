from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.core.database import supabase

router = Router()

class SettingStates(StatesGroup):
    waiting_for_welcome_text = State()
    waiting_for_currency = State()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_settings")
async def show_settings(callback: CallbackQuery, shop: dict):
    config = shop.get('config', {})
    welcome_text = config.get('welcome_text', 'Nicht gesetzt')
    currency = config.get('currency', 'EUR')

    text = (
        f"⚙️ **Shop-Einstellungen**\n\n"
        f"👋 **Willkommenstext:**\n_{welcome_text}_\n\n"
        f"💰 **Währung:** `{currency}`\n\n"
        f"Wähle einen Bereich zum Bearbeiten:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Willkommenstext ändern", callback_data="set_welcome_text")],
        [InlineKeyboardButton(text="💱 Währung ändern", callback_data="set_currency")],
        [InlineKeyboardButton(text="🔙 Dashboard", callback_data="admin_dashboard")]
    ])

    await safe_ui_update(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data == "set_welcome_text")
async def start_welcome_text(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("✍️ Sende mir jetzt den neuen Willkommenstext für deine Kunden:")
    await state.set_state(SettingStates.waiting_for_welcome_text)
    await callback.answer()

@router.message(SettingStates.waiting_for_welcome_text)
async def process_welcome_text(message: Message, state: FSMContext, shop: dict):
    new_text = message.text
    config = shop.get('config', {})
    config['welcome_text'] = new_text

    supabase.table("shops").update({"config": config}).eq("id", shop['id']).execute()

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zurück", callback_data="admin_settings")]])
    await message.answer("✅ Willkommenstext wurde aktualisiert!", reply_markup=kb)
    await state.clear()

@router.callback_query(F.data == "set_currency")
async def start_currency(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("💱 Bitte gib das Währungssymbol oder Kürzel ein (z.B. EUR, USD, BTC):")
    await state.set_state(SettingStates.waiting_for_currency)
    await callback.answer()

@router.message(SettingStates.waiting_for_currency)
async def process_currency(message: Message, state: FSMContext, shop: dict):
    new_currency = message.text.upper()[:5]
    config = shop.get('config', {})
    config['currency'] = new_currency

    supabase.table("shops").update({"config": config}).eq("id", shop['id']).execute()

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zurück", callback_data="admin_settings")]])
    await message.answer(f"✅ Währung auf `{new_currency}` gesetzt!", reply_markup=kb)
    await state.clear()
