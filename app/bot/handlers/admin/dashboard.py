from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.core.database import supabase

router = Router()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    """
    Hält das Admin-Interface sauber. Löscht Fotos, falls vorhanden,
    und editiert ansonsten den bestehenden Text.
    """
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_dashboard")
async def show_admin_dashboard(callback: CallbackQuery, shop: dict):
    # Statistiken für den Admin laden
    # Wir nutzen count="exact", um die Anzahl performant zu holen
    orders_res = supabase.table("orders").select("id", count="exact").eq("shop_id", shop['id']).execute()
    products_res = supabase.table("products").select("id", count="exact").eq("shop_id", shop['id']).execute()
    
    order_count = orders_res.count or 0
    product_count = products_res.count or 0

    text = (
        f"🛠 **Admin Control Panel**\n\n"
        f"🤖 Shop: @{shop['bot_username']}\n"
        f"💎 Abo: **{shop['tier'].upper()}**\n"
        f"📊 Status: {shop['status'].capitalize()}\n\n"
        f"📦 Produkte: `{product_count}`\n"
        f"🛒 Bestellungen: `{order_count}`\n\n"
        f"Was möchtest du verwalten?"
    )

    # Das Menü wurde um 'admin_payments' erweitert und strukturiert
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Produkte & Lager", callback_data="admin_products"),
            InlineKeyboardButton(text="📊 Bestellungen", callback_data="admin_orders")
        ],
        [
            InlineKeyboardButton(text="💳 Zahlungen (Wallets)", callback_data="admin_payments"),
            InlineKeyboardButton(text="⚙️ Einstellungen", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="👥 Team / Admins", callback_data="admin_team"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="👁 Zum Shop (Kunden-Ansicht)", callback_data="shop_start")
        ]
    ])

    await safe_ui_update(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_check(callback: CallbackQuery, shop: dict):
    """Prüft, ob der Shop das Recht für Broadcasts hat (Pro/Ultra Feature)"""
    if shop['tier'] == 'demo':
        await callback.answer(
            "🚫 Feature gesperrt!\nBroadcasts sind erst ab dem Pro-Abo verfügbar.", 
            show_alert=True
        )
    else:
        # Hier könnte später die Logik für Rundnachrichten an alle Kunden stehen
        # Fürs erste nur ein Platzhalter
        await callback.answer("Broadcast-Modul: Hier kannst du Nachrichten an alle Kunden senden (Coming Soon).", show_alert=True)
