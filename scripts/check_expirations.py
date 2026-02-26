import asyncio
import httpx
from datetime import datetime, timezone
from aiogram import Bot
from app.core.config import settings
from app.core.database import supabase

async def check_expired_shops():
    # 1. Aktuelle Zeit in UTC holen
    now = datetime.now(timezone.utc).isoformat()
    
    # 2. Suche alle aktiven Demo-Shops, deren trial_end überschritten ist
    # Wir filtern nach status = 'active' und tier = 'demo'
    response = (
        supabase.table("shops")
        .select("id, owner_telegram_id, bot_username, trial_end")
        .eq("status", "active")
        .eq("tier", "demo")
        .lt("trial_end", now)
        .execute()
    )
    
    expired_shops = response.data
    
    if not expired_shops:
        print(f"[{datetime.now()}] Keine abgelaufenen Demo-Shops gefunden.")
        return

    print(f"[{datetime.now()}] Verarbeite {len(expired_shops)} abgelaufene Shops...")
    
    # Master Bot Instanz, um Benachrichtigungen zu senden
    master_bot = Bot(token=settings.MASTER_BOT_TOKEN)

    for shop in expired_shops:
        shop_id = shop['id']
        owner_id = shop['owner_telegram_id']
        username = shop['bot_username']

        # 3. Shop Status in DB auf 'expired' setzen
        supabase.table("shops").update({"status": "expired"}).eq("id", shop_id).execute()
        
        # 4. Webhook für diesen Bot entfernen (optional, spart Traffic)
        # Wir versuchen es, falls der Token noch valide ist
        shop_full_data = supabase.table("shops").select("bot_token").eq("id", shop_id).single().execute()
        if shop_full_data.data:
            try:
                async with httpx.AsyncClient() as client:
                    token = shop_full_data.data['bot_token']
                    await client.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
            except Exception as e:
                print(f"Konnte Webhook für @{username} nicht löschen: {e}")

        # 5. Besitzer via Master-Bot informieren
        try:
            message_text = (
                f"⚠️ **Deine Demo-Phase ist abgelaufen!**\n\n"
                f"Dein Shop @{username} wurde automatisch deaktiviert.\n"
                f"Um den Shop wieder zu reaktivieren und alle Features zu nutzen, "
                f"wähle bitte ein Abo im Master-Bot aus."
            )
            await master_bot.send_message(chat_id=owner_id, text=message_text, parse_mode="Markdown")
            print(f"✅ Shop @{username} deaktiviert und Besitzer benachrichtigt.")
        except Exception as e:
            print(f"❌ Nachricht an Besitzer von @{username} fehlgeschlagen: {e}")

    await master_bot.session.close()

if __name__ == "__main__":
    # Skript ausführen
    asyncio.run(check_expired_shops())
