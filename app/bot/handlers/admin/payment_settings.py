from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.core.database import supabase

router = Router()

class PaymentState(StatesGroup):
    waiting_for_address = State()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_payments")
async def list_payment_methods(callback: CallbackQuery, shop: dict):
    # Standard Methoden definieren
    methods = ["BTC", "LTC", "ETH", "SOL", "PayPal"]
    
    text = "💳 **Zahlungsmethoden verwalten**\n\nHier kannst du deine Wallets hinterlegen. Diese werden dem Kunden beim Checkout angezeigt."
    kb_rows = []
    
    for m in methods:
        # Prüfen ob schon konfiguriert
        res = supabase.table("payment_configs").select("wallet_address").eq("shop_id", shop['id']).eq("method", m).execute()
        status = "✅" if res.data and res.data[0]['wallet_address'] else "❌"
        kb_rows.append([InlineKeyboardButton(text=f"{status} {m} konfigurieren", callback_data=f"conf_pay_{m}")])

    kb_rows.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="admin_dashboard")])
    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data.startswith("conf_pay_"))
async def configure_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[2]
    await state.update_data(method=method)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✍️ Bitte sende mir jetzt die **{method}-Adresse** (oder PayPal Email), die den Kunden angezeigt werden soll:"
    )
    await state.set_state(PaymentState.waiting_for_address)
    await callback.answer()

@router.message(PaymentState.waiting_for_address)
async def save_address(message: Message, state: FSMContext, shop: dict):
    data = await state.get_data()
    method = data['method']
    address = message.text.strip()

    # Upsert Logic (Einfügen oder Aktualisieren)
    data = {
        "shop_id": shop['id'],
        "method": method,
        "wallet_address": address,
        "is_active": True
    }
    
    # Supabase Upsert
    supabase.table("payment_configs").upsert(data, on_conflict="shop_id, method").execute()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zur Übersicht", callback_data="admin_payments")]])
    await message.answer(f"✅ Adresse für **{method}** gespeichert!", reply_markup=kb)
    await state.clear()
