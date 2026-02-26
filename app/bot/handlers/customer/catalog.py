from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from app.core.database import supabase

router = Router()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup, is_photo: bool = False, file_id: str = None):
    """
    Intelligente UI-Steuerung: Editiert Text, tauscht Medien aus oder 
    löscht/sendet neu, um den Chatverlauf sauber zu halten.
    """
    current_has_photo = bool(callback.message.photo)
    
    try:
        if is_photo:
            if current_has_photo:
                # Foto gegen Foto tauschen
                await callback.message.edit_media(
                    media=InputMediaPhoto(media=file_id, caption=text, parse_mode="Markdown"),
                    reply_markup=reply_markup
                )
            else:
                # Von Text zu Foto: Löschen und neu senden
                await callback.message.delete()
                await callback.message.answer_photo(photo=file_id, caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            if current_has_photo:
                # Von Foto zu Text: Löschen und neu senden
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
            else:
                # Text zu Text: Editieren
                await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        # Fallback: Falls Editieren fehlschlägt, neu senden
        if is_photo:
            await callback.message.answer_photo(photo=file_id, caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "catalog_list")
async def show_catalog(callback: CallbackQuery, shop: dict):
    res = supabase.table("products").select("*").eq("shop_id", shop['id']).eq("is_active", True).execute()
    products = res.data

    if not products:
        await callback.answer("🏠 Aktuell keine Produkte verfügbar.", show_alert=True)
        return

    text = f"📂 **Katalog: {shop['bot_username']}**\nWähle ein Produkt aus:"
    kb_rows = [[InlineKeyboardButton(text=f"{p['name']} — {p['price']}€", callback_data=f"prod_view_{p['id']}")] for p in products]
    kb_rows.append([InlineKeyboardButton(text="🛒 Warenkorb", callback_data="cart_show")])
    kb_rows.append([InlineKeyboardButton(text="🔙 Hauptmenü", callback_data="shop_start")])
    
    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data.startswith("prod_view_"))
async def view_product(callback: CallbackQuery, shop: dict):
    product_id = callback.data.split("_")[2]
    res = supabase.table("products").select("*").eq("id", product_id).single().execute()
    p = res.data
    
    text = (
        f"🏷 **{p['name']}**\n\n"
        f"{p.get('description', 'Keine Beschreibung verfügbar.')}\n\n"
        f"💰 Preis: **{p['price']}€**"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 In den Warenkorb", callback_data=f"cart_add_{p['id']}")],
        [InlineKeyboardButton(text="🔙 Zurück zum Katalog", callback_data="catalog_list")]
    ])

    if p.get('file_id'):
        await safe_ui_update(callback, text, kb, is_photo=True, file_id=p['file_id'])
    else:
        await safe_ui_update(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart_callback(callback: CallbackQuery, state: FSMContext):
    """
    Fügt Produkt zum Warenkorb hinzu und nutzt ein kurzes Overlay-Banner (Toast),
    statt eine neue Nachricht zu senden.
    """
    product_id = callback.data.split("_")[2]
    data = await state.get_data()
    cart = data.get("cart", [])
    cart.append(product_id)
    await state.update_data(cart=cart)
    
    # show_alert=False erzeugt einen Toast (kleiner Banner oben), der von selbst verschwindet
    await callback.answer("✅ Zum Warenkorb hinzugefügt!", show_alert=False)

@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery, shop: dict):
    customer_id = callback.from_user.id
    res = supabase.table("orders").select("*").eq("shop_id", shop['id']).eq("customer_telegram_id", customer_id).order("created_at", desc=True).limit(5).execute()
    orders = res.data

    if not orders:
        await callback.answer("Keine Bestellungen gefunden.", show_alert=True)
        return

    text = "📦 **Deine letzten Bestellungen:**\n\n"
    for o in orders:
        status_emoji = "✅" if o['status'] == 'paid' else "⏳"
        text += f"{status_emoji} ID: `{str(o['id'])[:8]}` - {o['total_amount']}€\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zurück", callback_data="shop_start")]])
    await safe_ui_update(callback, text, kb)
    await callback.answer()
