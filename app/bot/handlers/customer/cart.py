from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.core.database import supabase

router = Router()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    """
    Sorgt für eine saubere UI im Warenkorb.
    Entfernt Fotos (falls vorhanden) und editiert den Text.
    """
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "cart_show")
async def show_cart(callback: CallbackQuery, state: FSMContext, shop: dict):
    data = await state.get_data()
    cart_ids = data.get("cart", [])

    if not cart_ids:
        await callback.answer("🛒 Dein Warenkorb ist noch leer.", show_alert=True)
        return

    # Produkte aus DB laden
    response = supabase.table("products").select("id, name, price").in_("id", cart_ids).execute()
    products = response.data
    
    # Zähle Vorkommen (für Mengen)
    from collections import Counter
    counts = Counter(cart_ids)

    total = 0
    kb_rows = []
    text = "🛒 **Dein Warenkorb**\n\n"

    for p in products:
        count = counts[str(p['id'])]
        subtotal = p['price'] * count
        total += subtotal
        text += f"• {p['name']} (x{count}) — **{subtotal:.2f}€**\n"
        
        # Button zum Entfernen einzelner Items
        kb_rows.append([
            InlineKeyboardButton(text=f"❌ {p['name']} entfernen", callback_data=f"cart_remove_{p['id']}")
        ])

    text += f"\nGesamtsumme: **{total:.2f}€**"

    kb_rows.append([InlineKeyboardButton(text="💳 Zur Kasse", callback_data="checkout_start")])
    kb_rows.append([InlineKeyboardButton(text="➕ Mehr Produkte", callback_data="catalog_list")])
    kb_rows.append([InlineKeyboardButton(text="🗑 Warenkorb leeren", callback_data="cart_clear")])

    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data.startswith("cart_remove_"))
async def remove_item(callback: CallbackQuery, state: FSMContext, shop: dict):
    product_id = callback.data.split("_")[2]
    data = await state.get_data()
    cart = data.get("cart", [])

    if product_id in cart:
        cart.remove(product_id)
        await state.update_data(cart=cart)
        await callback.answer("Entfernt.")
        
        if not cart:
            await safe_ui_update(callback, "🛒 Dein Warenkorb ist jetzt leer.", 
                InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zum Shop", callback_data="shop_start")]]))
        else:
            await show_cart(callback, state, shop)
    else:
        await callback.answer("Fehler beim Entfernen.")

@router.callback_query(F.data == "cart_clear")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cart=[])
    await callback.answer("Warenkorb wurde geleert.")
    await safe_ui_update(callback, "🛒 Dein Warenkorb ist jetzt leer.", 
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zum Shop", callback_data="shop_start")]]))
