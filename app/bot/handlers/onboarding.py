from datetime import datetime, timedelta, timezone
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.core.config import settings
from app.core.database import supabase
from app.core.security import encrypt_token

router = Router()

class SetupShop(StatesGroup):
    waiting_for_token = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    shop_res = supabase.table("shops").select("*").eq("owner_telegram_id", user_id).execute()
    
    kb_rows = []
    if not shop_res.data:
        kb_rows.append([InlineKeyboardButton(text="🚀 Shop erstellen", callback_data="create_shop")])
    else:
        kb_rows.append([InlineKeyboardButton(text="💎 Upgrade / Abo", callback_data="buy_upgrade")])
        kb_rows.append([InlineKeyboardButton(text="📊 Meine Shops", callback_data="my_shops_list")])
    
    kb_rows.append([InlineKeyboardButton(text="❓ Hilfe", callback_data="help")])
    
    await message.answer(
        "👋 **Willkommen beim NexusShop Builder!**\n\n"
        "Hier erstellst und verwaltest du deine Telegram-Shops.\n\n"
        "1. Erstelle einen Bot bei @BotFather\n"
        "2. Sende mir den API Token\n"
        "3. Verwalte deine Produkte direkt im neuen Bot",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )

@router.callback_query(F.data == "create_shop")
async def start_setup_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Sende mir jetzt den **API Token** von @BotFather.\n"
        "Beispiel: `123456:ABC-DEF...`"
    )
    await state.set_state(SetupShop.waiting_for_token)
    await callback.answer()

@router.message(SetupShop.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()
    user_id = message.from_user.id
    
    try:
        new_bot = Bot(token=token)
        bot_info = await new_bot.get_me()
        
        trial_end = datetime.now(timezone.utc) + timedelta(days=30)
        encrypted_token = encrypt_token(token)
        
        new_shop_data = {
            "owner_telegram_id": user_id,
            "bot_token": encrypted_token,
            "bot_username": bot_info.username,
            "tier": "demo",
            "status": "active",
            "trial_end": trial_end.isoformat(),
            "config": {"welcome_text": f"Willkommen bei {bot_info.first_name}!", "currency": "EUR"}
        }

        res = supabase.table("shops").insert(new_shop_data).execute()
        shop_id = res.data[0]['id']

        webhook_url = f"{settings.WEBHOOK_HOST}/webhook/{shop_id}"
        await new_bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            secret_token=settings.ADMIN_SECRET[:32]
        )
        
        await new_bot.session.close()
        
        await message.answer(
            f"✅ **Online!**\n\n🤖 @{bot_info.username}\n📅 Demo bis: {trial_end.strftime('%d.%m.%Y')}\n\n"
            f"Gehe zu deinem Bot und tippe `/admin`."
        )
        await state.clear()
        
    except Exception:
        await message.answer("❌ Fehler: Token ungültig oder Datenbankfehler.")

@router.callback_query(F.data == "buy_upgrade")
async def show_offers(callback: CallbackQuery):
    conf = supabase.table("platform_config").select("*").eq("id", 1).single().execute().data
    
    text = (
        f"🌟 **Upgrade dein Business**\n\n"
        f"🔹 **{conf['pro_label']}**\n"
        f"• Bis zu 30 Produkte\n"
        f"• 3 Zahlungsmethoden\n"
        f"💰 Preis: **{conf['pro_price_ltc']} LTC**\n\n"
        f"👑 **{conf['ultra_label']}**\n"
        f"• Unbegrenzt Produkte\n"
        f"• Unbegrenzt Zahlungsmethoden\n"
        f"💰 Preis: **{conf['ultra_price_ltc']} LTC**"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Kaufen: {conf['pro_label']}", callback_data="buy_tier_pro")],
        [InlineKeyboardButton(text=f"Kaufen: {conf['ultra_label']}", callback_data="buy_tier_ultra")],
        [InlineKeyboardButton(text="🔙 Zurück", callback_data="start_back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("buy_tier_"))
async def choose_currency(callback: CallbackQuery):
    tier = callback.data.split("_")[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Litecoin (LTC)", callback_data=f"pay_req_LTC_{tier}")],
        [InlineKeyboardButton(text="Bitcoin (BTC)", callback_data=f"pay_req_BTC_{tier}")],
        [InlineKeyboardButton(text="Ethereum (ETH)", callback_data=f"pay_req_ETH_{tier}")],
        [InlineKeyboardButton(text="Solana (SOL)", callback_data=f"pay_req_SOL_{tier}")],
        [InlineKeyboardButton(text="🔙 Abbrechen", callback_data="buy_upgrade")]
    ])
    await callback.message.edit_text(f"Wähle deine Zahlungswährung für **{tier.upper()}**:", reply_markup=kb)

@router.callback_query(F.data.startswith("pay_req_"))
async def show_payment_info(callback: CallbackQuery):
    _, _, coin, tier = callback.data.split("_")
    conf = supabase.table("platform_config").select("*").eq("id", 1).single().execute().data
    
    wallet = conf.get(f"wallet_{coin.lower()}")
    # Preislogik (Beispielhaft LTC als Basis)
    price = conf[f"{tier}_price_ltc"]
    
    text = (
        f"⚠️ **Zahlungsinformationen ({tier.upper()})**\n\n"
        f"Bitte sende den Gegenwert von **{price} LTC** in **{coin}** an:\n\n"
        f"`{wallet}`\n\n"
        f"Klicke erst auf 'Bestätigen', wenn die Transaktion gesendet wurde."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Zahlung bestätigt", callback_data=f"admin_notify_{tier}_{coin}")],
        [InlineKeyboardButton(text="🔙 Zurück", callback_data="buy_upgrade")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("admin_notify_"))
async def notify_super_admin(callback: CallbackQuery):
    _, _, tier, coin = callback.data.split("_")
    user = callback.from_user
    
    # Benachrichtigung an DICH (Super-Admin) über den Bot
    # Nutzt settings.ADMIN_TELEGRAM_ID (muss in .env/config sein)
    admin_msg = (
        f"🔔 **NEUE UPGRADE-ANFRAGE**\n\n"
        f"User: @{user.username} ({user.id})\n"
        f"Paket: **{tier.upper()}**\n"
        f"Währung: {coin}\n\n"
        f"Prüfe den Wallet-Eingang und schalte den User im Dashboard frei."
    )
    
    try:
        # Hier wird eine separate Bot-Instanz oder die aktuelle genutzt, 
        # um dich zu benachrichtigen (ID aus Settings)
        await callback.bot.send_message(chat_id=settings.ADMIN_TELEGRAM_ID, text=admin_msg)
    except:
        pass
    
    await callback.message.edit_text(
        "✅ **Anfrage gesendet!**\n\n"
        "Wir prüfen den Zahlungseingang manuell. Sobald dein Account hochgestuft wurde, "
        "erhältst du eine Nachricht vom System."
    )

@router.callback_query(F.data == "start_back")
async def back_to_start(callback: CallbackQuery):
    await cmd_start(callback.message)
    await callback.message.delete()
