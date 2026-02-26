from app.core.database import supabase

async def add_shop_admin(shop_id: str, telegram_user_id: int, role: str = "moderator") -> bool:
    data = {
        "shop_id": shop_id,
        "telegram_user_id": telegram_user_id,
        "role": role
    }
    try:
        supabase.table("shop_admins").insert(data).execute()
        return True
    except Exception:
        return False

async def remove_shop_admin(shop_id: str, telegram_user_id: int) -> bool:
    try:
        supabase.table("shop_admins").delete().eq("shop_id", shop_id).eq("telegram_user_id", telegram_user_id).execute()
        return True
    except Exception:
        return False

async def get_shop_admins(shop_id: str) -> list:
    response = supabase.table("shop_admins").select("*").eq("shop_id", shop_id).execute()
    return response.data

async def is_admin(shop_id: str, telegram_user_id: int) -> bool:
    response = supabase.table("shop_admins").select("id").eq("shop_id", shop_id).eq("telegram_user_id", telegram_user_id).execute()
    return bool(response.data)
