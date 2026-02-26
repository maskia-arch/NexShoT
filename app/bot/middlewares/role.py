from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.core.database import supabase

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        shop = data.get("shop")

        if not user or not shop:
            data["role"] = "anonymous"
            data["is_admin"] = False
            return await handler(event, data)

        if user.id == shop["owner_telegram_id"]:
            data["role"] = "owner"
            data["is_admin"] = True
            return await handler(event, data)

        response = supabase.table("shop_admins").select("role").eq("shop_id", shop["id"]).eq("telegram_user_id", user.id).execute()

        if response.data:
            data["role"] = response.data[0]["role"]
            data["is_admin"] = True
        else:
            data["role"] = "customer"
            data["is_admin"] = False

        return await handler(event, data)
