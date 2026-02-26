from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.core.database import supabase

router = Router()

class TeamStates(StatesGroup):
    waiting_for_admin_id = State()

async def safe_ui_update(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_team")
async def show_team_management(callback: CallbackQuery, shop: dict):
    res = supabase.table("shop_admins").select("*").eq("shop_id", shop['id']).execute()
    admins = res.data

    text = (
        f"👥 **Team-Verwaltung**\n\n"
        f"Hier kannst du zusätzliche Moderatoren hinzufügen, die Produkte verwalten und Bestellungen einsehen können.\n\n"
        f"Aktuelle Team-Mitglieder: `{len(admins)}`"
    )

    kb_rows = []
    for adm in admins:
        kb_rows.append([
            InlineKeyboardButton(text=f"👤 ID: {adm['telegram_user_id']}", callback_data=f"view_admin_{adm['id']}")
        ])

    kb_rows.append([InlineKeyboardButton(text="➕ Admin hinzufügen", callback_data="add_team_member")])
    kb_rows.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="admin_dashboard")])

    await safe_ui_update(callback, text, InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer()

@router.callback_query(F.data == "add_team_member")
async def start_add_team(callback: CallbackQuery, state: FSMContext, shop: dict):
    if shop['tier'] == 'demo':
        await callback.answer("🚫 Multi-Admin Support ist erst ab dem Pro-Abo verfügbar.", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        "🆔 Bitte sende mir die **Telegram User ID** der Person, die du als Admin hinzufügen möchtest.\n\n"
        "Tipp: Die Person kann @userinfobot nutzen, um ihre ID herauszufinden."
    )
    await state.set_state(TeamStates.waiting_for_admin_id)
    await callback.answer()

@router.message(TeamStates.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext, shop: dict):
    try:
        new_admin_id = int(message.text.strip())
        
        supabase.table("shop_admins").insert({
            "shop_id": shop['id'],
            "telegram_user_id": new_admin_id,
            "role": "moderator"
        }).execute()

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Zurück", callback_data="admin_team")]])
        await message.answer(f"✅ User `{new_admin_id}` wurde als Moderator hinzugefügt!", reply_markup=kb)
        await state.clear()
    except ValueError:
        await message.answer("❌ Bitte sende eine gültige numerische ID.")
    except Exception:
        await message.answer("❌ Dieser User ist bereits Admin oder ein Fehler ist aufgetreten.")
        await state.clear()

@router.callback_query(F.data.startswith("view_admin_"))
async def view_admin(callback: CallbackQuery, shop: dict):
    admin_db_id = callback.data.split("_")[2]
    res = supabase.table("shop_admins").select("*").eq("id", admin_db_id).single().execute()
    adm = res.data

    text = f"👤 **Admin-Details**\n\nID: `{adm['telegram_user_id']}`\nRolle: {adm['role']}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Admin entfernen", callback_data=f"remove_adm_{adm['id']}")],
        [InlineKeyboardButton(text="🔙 Zurück", callback_data="admin_team")]
    ])

    await safe_ui_update(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data.startswith("remove_adm_"))
async def remove_admin(callback: CallbackQuery, shop: dict):
    admin_db_id = callback.data.split("_")[2]
    supabase.table("shop_admins").delete().eq("id", admin_db_id).execute()
    
    await callback.answer("Admin entfernt.", show_alert=True)
    await show_team_management(callback, shop)
