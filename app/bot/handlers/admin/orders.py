from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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

@router.callback_query(F.data == "admin_orders")
async def list_open_orders(callback: CallbackQuery, shop: dict):
    # Zeige nur offene Bestellungen (pending) oder die letzten 5 bezahlten
    res = supabase.table("orders").select("*").eq("shop_id", shop['id']).order("created_at", desc=True).limit(10).execute()
    orders = res.data

    if not orders:
        await callback.answer("Keine Bestellungen vorhanden.", show_alert=True)
        return

    text = "📋 **Bestell-Übersicht**\nKlicke auf eine ID zum Bearbeiten:\n"
    kb_rows = []
    
    for o in orders:
        status_icon = "⏳" if o['status'] == 'pending' else "✅"
        btn_text = f"{status_icon} ID: {str(o['id'])[:6]}... ({o['total_amount']}€)"
        kb_rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"manage_order_{o['id']}")])

    kb_rows.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="admin_dashboard")])
    
    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data.startswith("manage_order_"))
async def view_order_details(callback: CallbackQuery, shop: dict):
    order_id = callback.data.split("_")[2]
    res = supabase.table("orders").select("*").eq("id", order_id).single().execute()
    order = res.data

    # Kundendetails holen
    customer_id = order['customer_telegram_id']
    
    # Items laden für Vorschau
    items_res = supabase.table("order_items").select("product_name").eq("order_id", order_id).execute()
    item_names = ", ".join([i['product_name'] for i in items_res.data]) if items_res.data else "Unbekannt"

    text = (
        f"🧾 **Bestellung: {str(order['id'])[:8]}**\n\n"
        f"👤 Kunde ID: `{customer_id}`\n"
        f"📦 Produkte: {item_names}\n"
        f"💰 Betrag: **{order['total_amount']}€**\n"
        f"💳 Methode: {order['payment_method']}\n"
        f"📅 Datum: {order['created_at'][:10]}\n"
        f"📊 Status: **{order['status'].upper()}**\n"
    )

    kb_rows = []
    if order['status'] == 'pending':
        kb_rows.append([InlineKeyboardButton(text="✅ Zahlung bestätigen & Ausliefern", callback_data=f"approve_order_{order['id']}")])
        kb_rows.append([InlineKeyboardButton(text="❌ Bestellung stornieren", callback_data=f"cancel_order_{order['id']}")])
    
    kb_rows.append([InlineKeyboardButton(text="🔙 Zurück", callback_data="admin_orders")])

    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data.startswith("approve_order_"))
async def approve_and_deliver(callback: CallbackQuery, shop: dict):
    order_id = callback.data.split("_")[2]
    
    # 1. Status Update auf 'paid'
    supabase.table("orders").update({"status": "paid"}).eq("id", order_id).execute()
    
    # 2. Daten laden
    order = supabase.table("orders").select("*").eq("id", order_id).single().execute().data
    items = supabase.table("order_items").select("*").eq("order_id", order_id).execute().data
    customer_id = order['customer_telegram_id']
    
    delivered_content = []
    missing_stock = []

    # 3. Ware zuteilen (Digitale Auslieferung)
    for item in items:
        # Versuche einen unbenutzten Key für das Produkt zu finden (FIFO)
        key_res = supabase.table("product_keys").select("*")\
            .eq("shop_id", shop['id'])\
            .eq("product_id", item['product_id'])\
            .eq("is_used", False)\
            .limit(1)\
            .execute()
        
        if key_res.data:
            key = key_res.data[0]
            # Key als benutzt markieren
            supabase.table("product_keys").update({"is_used": True}).eq("id", key['id']).execute()
            
            delivered_content.append(f"📦 **{item['product_name']}:**\n`{key['content']}`")
        else:
            missing_stock.append(item['product_name'])

    # 4. Nachricht an Kunden senden
    try:
        if delivered_content:
            msg = f"✅ **Zahlung bestätigt! Hier ist deine Bestellung:**\n\n" + "\n\n".join(delivered_content)
            await callback.bot.send_message(chat_id=customer_id, text=msg, parse_mode="Markdown")
        
        if missing_stock:
            # Fallback Nachricht bei fehlendem Lagerbestand
            msg_missing = (
                f"👋 **Hallo!** Deine Zahlung für Order #{str(order_id)[:8]} wurde bestätigt.\n\n"
                f"⚠️ Für folgende Produkte füllt der Admin gerade das Lager auf: "
                f"**{', '.join(missing_stock)}**\n\n"
                f"Du erhältst diese Kürze separat nachgesendet."
            )
            await callback.bot.send_message(chat_id=customer_id, text=msg_missing, parse_mode="Markdown")
            
            # Admin warnen
            await callback.answer(f"⚠️ ACHTUNG: Kein Lagerbestand für {len(missing_stock)} Produkte! Bitte manuell nachsenden.", show_alert=True)
        else:
            await callback.answer("Bestellung bestätigt & vollständig ausgeliefert!", show_alert=True)

    except Exception as e:
        await callback.answer(f"Status geändert, aber Senden fehlgeschlagen (Bot blockiert?): {e}", show_alert=True)
    
    # Liste aktualisieren
    await list_open_orders(callback, shop)

@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery, shop: dict):
    order_id = callback.data.split("_")[2]
    supabase.table("orders").update({"status": "cancelled"}).eq("id", order_id).execute()
    
    await callback.answer("Bestellung storniert.", show_alert=True)
    await list_open_orders(callback, shop)
