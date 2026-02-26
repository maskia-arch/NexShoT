from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from app.core.database import supabase

router = Router()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    """
    Hält das Interface sauber. Löscht Fotos (von Produktansichten) 
    und editiert ansonsten den Text.
    """
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.message(CommandStart())
async def cmd_start(message: Message, shop: dict):
    """
    Der erste Kontakt. Wird bei /start aufgerufen.
    """
    user_id = message.from_user.id
    is_admin = (user_id == shop['owner_telegram_id'])
    
    welcome_text = shop['config'].get('welcome_text', 'Willkommen in unserem Shop!')
    
    text = (
        f"👋 {welcome_text}\n\n"
        f"🛒 **Shop:** {shop['bot_username']}\n"
        f"💰 **Währung:** {shop['config'].get('currency', 'EUR')}\n\n"
        "Nutze die Buttons unten, um durch unseren Katalog zu stöbern."
    )

    kb_rows = [
        [InlineKeyboardButton(text="🛍 Katalog öffnen", callback_data="catalog_list")],
        [InlineKeyboardButton(text="📦 Meine Bestellungen", callback_data="my_orders")],
        [InlineKeyboardButton(text="ℹ️ Info & Support", callback_data="shop_info")]
    ]

    # Wenn der Besitzer den Bot startet, bekommt er den Admin-Button angezeigt
    if is_admin:
        kb_rows.append([InlineKeyboardButton(text="⚙️ Admin-Bereich", callback_data="admin_dashboard")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown")

@router.callback_query(F.data == "shop_start")
async def back_to_start(callback: CallbackQuery, shop: dict):
    """
    Callback-Handler, um von überall zum Hauptmenü zurückzukehren.
    """
    user_id = callback.from_user.id
    is_admin = (user_id == shop['owner_telegram_id'])
    
    welcome_text = shop['config'].get('welcome_text', 'Willkommen zurück!')
    
    text = (
        f"🏠 **Hauptmenü**\n\n"
        f"{welcome_text}\n\n"
        "Womit kann ich dir heute helfen?"
    )

    kb_rows = [
        [InlineKeyboardButton(text="🛍 Katalog öffnen", callback_data="catalog_list")],
        [InlineKeyboardButton(text="🛒 Mein Warenkorb", callback_data="cart_show")],
        [InlineKeyboardButton(text="📦 Bestellungen", callback_data="my_orders")]
    ]

    if is_admin:
        kb_rows.append([InlineKeyboardButton(text="⚙️ Admin-Dashboard", callback_data="admin_dashboard")])

    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data == "shop_info")
async def show_info(callback: CallbackQuery, shop: dict):
    """
    Zeigt Informationen über den Shop an.
    """
    text = (
        f"ℹ️ **Informationen zu {shop['bot_username']}**\n\n"
        "Dies ist ein automatisierter Telegram-Shop.\n"
        "Alle Zahlungen sind sicher und digital.\n\n"
        "Bei Fragen wende dich bitte an den Support."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Zurück", callback_data="shop_start")]
    ])
    
    await safe_ui_update(callback, text, kb)
    await callback.answer()
