from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.core.database import supabase

class TenantMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        token = bot.token
        
        response = supabase.table("shops").select("*").eq("bot_token", token).execute()
        
        if not response.data:
            return
        
        shop = response.data[0]
        
        if shop.get("status") != "active":
            return

        data["shop"] = shop
        
        return await handler(event, data)
