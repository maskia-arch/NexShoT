from fastapi import FastAPI, Header, HTTPException
from aiogram import Bot, Router
from aiogram.types import Update
from app.bot.loader import dp
from app.core.config import settings
from app.core.database import supabase
from app.core.security import decrypt_token
from app.bot.middlewares.tenant import TenantMiddleware
from app.bot.middlewares.role import RoleMiddleware

from app.bot.handlers import onboarding
from app.bot.handlers.admin import dashboard, products, settings as shop_settings, team, orders, payment_settings
from app.bot.handlers.customer import start, catalog, cart, checkout
from app.web import admin_routes

app = FastAPI()
app.include_router(admin_routes.router)

@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "alive", "service": "NexusShop SaaS"}

master_router = Router()
master_router.include_router(onboarding.router)

shop_router = Router()
shop_router.include_routers(
    start.router, catalog.router, cart.router, checkout.router,
    dashboard.router, products.router, shop_settings.router, team.router, 
    orders.router, payment_settings.router
)

@app.on_event("startup")
async def on_startup():
    shop_router.message.middleware(TenantMiddleware())
    shop_router.callback_query.middleware(TenantMiddleware())
    shop_router.message.middleware(RoleMiddleware())
    shop_router.callback_query.middleware(RoleMiddleware())
    
    dp.include_router(master_router)
    dp.include_router(shop_router)

    master_bot = Bot(token=settings.MASTER_BOT_TOKEN)
    master_id = settings.MASTER_BOT_TOKEN.split(':')[0]
    webhook_url = f"{settings.WEBHOOK_HOST.rstrip('/')}/webhook/{master_id}"
    
    try:
        await master_bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            secret_token=settings.ADMIN_SECRET[:32]
        )
    except Exception:
        pass
    finally:
        await master_bot.session.close()

@app.post("/webhook/{identifier}")
async def bot_webhook(
    identifier: str, 
    update: dict, 
    x_telegram_bot_api_secret_token: str = Header(None)
):
    if x_telegram_bot_api_secret_token != settings.ADMIN_SECRET[:32]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if identifier == settings.MASTER_BOT_TOKEN.split(':')[0]:
        token = settings.MASTER_BOT_TOKEN
    else:
        res = supabase.table("shops").select("bot_token").eq("id", identifier).single().execute()
        if not res.data:
            raise HTTPException(status_code=404)
        token = decrypt_token(res.data['bot_token'])
    
    bot = Bot(token=token)
    try:
        await dp.feed_update(bot=bot, update=Update(**update))
    finally:
        await bot.session.close()
    
    return {"status": "ok"}
