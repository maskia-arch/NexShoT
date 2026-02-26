from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from collections import Counter
from app.core.database import supabase

router = Router()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "checkout_start")
async def start_checkout(callback: CallbackQuery, state: FSMContext, shop: dict):
    data = await state.get_data()
    cart_ids = data.get("cart", [])

    if not cart_ids:
        await callback.answer("Dein Warenkorb ist leer.", show_alert=True)
        return

    res = supabase.table("products").select("price").in_("id", cart_ids).execute()
    total = sum(item['price'] for item in res.data)
    await state.update_data(total_amount=total)

    text = (
        f"🏁 **Checkout**\n\n"
        f"Gesamtsumme: **{total:.2f}€**\n\n"
        f"Wähle deine bevorzugte Zahlungsmethode:"
    )

    pay_configs = supabase.table("payment_configs").select("method").eq("shop_id", shop['id']).eq("is_active", True).execute()
    
    kb_rows = []
    if pay_configs.data:
        for pc in pay_configs.data:
            kb_rows.append([InlineKeyboardButton(text=f"💳 {pc['method']}", callback_data=f"pay_{pc['method']}")])
    else:
        kb_rows.append([InlineKeyboardButton(text="🔄 Manuelle Anfrage", callback_data="pay_manual")])

    kb_rows.append([InlineKeyboardButton(text="🔙 Zurück zum Warenkorb", callback_data="cart_show")])

    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def process_payment_choice(callback: CallbackQuery, state: FSMContext, shop: dict):
    method = callback.data.split("_")[1]
    data = await state.get_data()
    cart_ids = data.get("cart", [])
    total = data.get("total_amount", 0)
    customer_id = callback.from_user.id

    order_res = supabase.table("orders").insert({
        "shop_id": shop['id'],
        "customer_telegram_id": customer_id,
        "total_amount": total,
        "payment_method": method,
        "status": "pending"
    }).execute()
    
    if not order_res.data:
        await callback.answer("Fehler bei der Bestellung.", show_alert=True)
        return

    order_id = order_res.data[0]['id']

    products = supabase.table("products").select("*").in_("id", cart_ids).execute().data
    items_data = []
    counts = Counter(cart_ids)
    
    for p in products:
        quantity = counts[str(p['id'])]
        for _ in range(quantity):
            items_data.append({
                "order_id": order_id,
                "product_id": p['id'],
                "price_at_purchase": p['price'],
                "product_name": p['name']
            })
            
    if items_data:
        supabase.table("order_items").insert(items_data).execute()

    wallet_res = supabase.table("payment_configs").select("wallet_address").eq("shop_id", shop['id']).eq("method", method).execute()
    wallet_address = wallet_res.data[0]['wallet_address'] if wallet_res.data else None

    if wallet_address:
        text = (
            f"💳 **Zahlung: {method}**\n\n"
            f"Bitte sende **{total:.2f}€** (in {method}) an:\n"
            f"`{wallet_address}`\n\n"
            f"Bestell-ID: `{str(order_id)[:8]}`\n\n"
            f"⚠️ WICHTIG: Klicke unten auf 'Ich habe bezahlt', sobald du gesendet hast."
        )
    else:
        text = (
            f"✅ **Bestellung aufgegeben!**\n\n"
            f"Bestell-ID: `{str(order_id)[:8]}`\n"
            f"Gesamt: **{total:.2f}€**\n\n"
            f"Der Admin wurde benachrichtigt und wird dir die Zahlungsdetails für {method} senden."
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ich habe bezahlt", callback_data=f"confirm_pay_{order_id}")],
        [InlineKeyboardButton(text="🏠 Hauptmenü", callback_data="shop_start")]
    ])

    await safe_ui_update(callback, text, kb)
    await callback.answer()
    
    await state.update_data(cart=[])

@router.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_payment_request(callback: CallbackQuery, shop: dict):
    order_id = callback.data.split("_")[2]
    
    try:
        admin_text = (
            f"🔔 **Neue Zahlung gemeldet!**\n\n"
            f"Kunde: @{callback.from_user.username}\n"
            f"Order: `{str(order_id)[:8]}`\n"
            f"Bitte prüfe den Geldeingang im Dashboard."
        )
        await callback.bot.send_message(chat_id=shop['owner_telegram_id'], text=admin_text)
    except Exception:
        pass 

    await callback.message.edit_text(
        "✅ **Bestätigung gesendet!**\n\n"
        "Wir prüfen deine Zahlung. Sobald das erledigt ist, erhältst du deine Ware direkt hier im Chat.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Hauptmenü", callback_data="shop_start")]])
    )
