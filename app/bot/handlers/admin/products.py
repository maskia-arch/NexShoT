from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.core.database import supabase
from app.services.tier_manager import check_limit

router = Router()

class ProductState(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_content = State()

class StockState(StatesGroup):
    waiting_for_keys = State()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_products")
async def list_products(callback: CallbackQuery, shop: dict):
    response = supabase.table("products").select("id, name, price").eq("shop_id", shop['id']).execute()
    products = response.data

    text = f"📦 **Produktverwaltung**\nAnzahl: {len(products)}"
    kb_rows = []
    for p in products:
        count_res = supabase.table("product_keys").select("id", count="exact").eq("product_id", p['id']).eq("is_used", False).execute()
        stock = count_res.count if count_res.count is not None else 0
        
        kb_rows.append([InlineKeyboardButton(text=f"✏️ {p['name']} ({stock} Stk.)", callback_data=f"edit_prod_{p['id']}")])
    
    kb_rows.append([InlineKeyboardButton(text="➕ Neues Produkt", callback_data="add_product")])
    kb_rows.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="admin_dashboard")])

    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data == "add_product")
async def start_add_product(callback: CallbackQuery, state: FSMContext, shop: dict):
    allowed = await check_limit(shop['id'], "products")
    if not allowed:
        await callback.answer("🚫 Limit erreicht! Upgrade erforderlich.", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer("🏷 Wie soll das Produkt heißen?")
    await state.set_state(ProductState.waiting_for_name)
    await callback.answer()

@router.message(ProductState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Welchen Preis hat das Produkt? (z.B. 19.99)")
    await state.set_state(ProductState.waiting_for_price)

@router.message(ProductState.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        await state.update_data(price=price)
        await message.answer(
            "🖼 **Produkt-Content & Bild**\n\n"
            "Sende mir jetzt eine Beschreibung (Text) **ODER** lade ein Foto hoch."
        )
        await state.set_state(ProductState.waiting_for_content)
    except ValueError:
        await message.answer("Bitte gib eine gültige Zahl ein.")

@router.message(ProductState.waiting_for_content)
async def process_content(message: Message, state: FSMContext, shop: dict):
    data = await state.get_data()
    file_id = None
    description = message.text or message.caption or "Keine Beschreibung"

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id

    new_product = {
        "shop_id": shop['id'],
        "name": data['name'],
        "price": data['price'],
        "description": description,
        "file_id": file_id,
        "is_active": True
    }
    
    supabase.table("products").insert(new_product).execute()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zur Übersicht", callback_data="admin_products")]])
    await message.answer(f"✅ Produkt **{data['name']}** erstellt!", reply_markup=kb)
    await state.clear()

@router.callback_query(F.data.startswith("edit_prod_"))
async def edit_product_menu(callback: CallbackQuery, shop: dict):
    product_id = callback.data.split("_")[2]
    p = supabase.table("products").select("*").eq("id", product_id).single().execute().data
    
    count_res = supabase.table("product_keys").select("id", count="exact").eq("product_id", product_id).eq("is_used", False).execute()
    stock = count_res.count if count_res.count is not None else 0

    text = f"✏️ **Produkt bearbeiten**\n\nName: {p['name']}\nPreis: {p['price']}€\n📦 Lagerbestand: **{stock} Keys**"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Ware auffüllen (Keys)", callback_data=f"add_stock_{product_id}")],
        [InlineKeyboardButton(text="🗑 Produkt löschen", callback_data=f"delete_prod_{product_id}")],
        [InlineKeyboardButton(text="🔙 Zurück", callback_data="admin_products")]
    ])
    
    await safe_ui_update(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data.startswith("add_stock_"))
async def start_add_stock(callback: CallbackQuery, state: FSMContext):
    product_id = callback.data.split("_")[2]
    await state.update_data(product_id=product_id)
    
    await callback.message.delete()
    await callback.message.answer(
        "📦 **Lager auffüllen**\n\n"
        "Sende mir jetzt die Keys, Links oder Daten.\n"
        "👉 **Format:** Eine Zeile pro Verkaufseinheit.\n\n"
        "Beispiel:\nKey-1234\nKey-5678\nhttps://download.link/x"
    )
    await state.set_state(StockState.waiting_for_keys)
    await callback.answer()

@router.message(StockState.waiting_for_keys)
async def process_keys(message: Message, state: FSMContext, shop: dict):
    data = await state.get_data()
    product_id = data['product_id']
    raw_text = message.text
    
    keys = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    if not keys:
        await message.answer("⚠️ Keine gültigen Zeilen gefunden.")
        return

    insert_data = [{"shop_id": shop['id'], "product_id": product_id, "content": k} for k in keys]
    supabase.table("product_keys").insert(insert_data).execute()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zum Produkt", callback_data=f"edit_prod_{product_id}")], [InlineKeyboardButton(text="📦 Alle Produkte", callback_data="admin_products")]])
    await message.answer(f"✅ **{len(keys)}** Einheiten erfolgreich eingelagert!", reply_markup=kb)
    await state.clear()

@router.callback_query(F.data.startswith("delete_prod_"))
async def delete_product(callback: CallbackQuery, shop: dict):
    product_id = callback.data.split("_")[2]
    supabase.table("products").delete().eq("id", product_id).execute()
    await callback.answer("Produkt gelöscht.", show_alert=True)
    await list_products(callback, shop)
