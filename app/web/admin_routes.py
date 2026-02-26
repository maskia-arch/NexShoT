from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.core.database import supabase
from app.core.config import settings
from app.core.security import encrypt_token
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Optional
from aiogram import Bot

templates = Jinja2Templates(directory="app/web/templates")
router = APIRouter(prefix="/admin")

class TierUpdate(BaseModel):
    shop_id: str
    new_tier: str
    days: Optional[int] = 30

class TransferShop(BaseModel):
    shop_id: str
    new_owner_id: int
    new_bot_token: str

class PlatformConfigUpdate(BaseModel):
    pro_price_ltc: Optional[float] = None
    ultra_price_ltc: Optional[float] = None
    pro_label: Optional[str] = None
    ultra_label: Optional[str] = None
    wallet_btc: Optional[str] = None
    wallet_ltc: Optional[str] = None
    wallet_eth: Optional[str] = None
    wallet_sol: Optional[str] = None

@router.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request, secret: str):
    if secret != settings.ADMIN_SECRET:
        return HTMLResponse(content="<h1>403 Forbidden</h1>", status_code=403)
    return templates.TemplateResponse("dashboard.html", {"request": request, "api_url": settings.WEBHOOK_HOST})

@router.get("/api/overview")
async def get_overview(x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    shops = supabase.table("shops").select("*").order("created_at", desc=True).execute()
    total_shops = len(shops.data)
    active_shops = sum(1 for s in shops.data if s['status'] == 'active')
    return {
        "total_shops": total_shops,
        "active_shops": active_shops,
        "shops": shops.data
    }

@router.get("/api/shop_details/{shop_id}")
async def get_shop_details(shop_id: str, x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    shop = supabase.table("shops").select("*").eq("id", shop_id).single().execute()
    products = supabase.table("products").select("*").eq("shop_id", shop_id).execute()
    orders = supabase.table("orders").select("*").eq("shop_id", shop_id).order("created_at", desc=True).execute()
    return {
        "shop": shop.data,
        "products": products.data,
        "orders": orders.data
    }

@router.get("/api/config")
async def get_config(x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    res = supabase.table("platform_config").select("*").eq("id", 1).single().execute()
    return res.data

@router.patch("/api/config")
async def update_config(update: PlatformConfigUpdate, x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    res = supabase.table("platform_config").update(update_data).eq("id", 1).execute()
    return res.data

@router.post("/api/grant_access")
async def grant_access(update: TierUpdate, x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    end_date = datetime.now(timezone.utc) + timedelta(days=update.days)
    update_payload = {
        "tier": update.new_tier,
        "subscription_end": end_date.isoformat(),
        "status": "active"
    }
    res = supabase.table("shops").update(update_payload).eq("id", update.shop_id).execute()
    return {"status": "success", "expires": end_date, "data": res.data}

@router.post("/api/ban_shop/{shop_id}")
async def ban_shop(shop_id: str, x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    supabase.table("shops").update({"status": "banned"}).eq("id", shop_id).execute()
    return {"status": "banned", "id": shop_id}

@router.post("/api/transfer_shop")
async def transfer_shop(data: TransferShop, x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    
    encrypted_token = encrypt_token(data.new_bot_token)
    
    update_payload = {
        "owner_telegram_id": data.new_owner_id,
        "bot_token": encrypted_token,
        "bot_username": "PENDING_UPDATE"
    }
    
    supabase.table("shops").update(update_payload).eq("id", data.shop_id).execute()
    
    new_bot = Bot(token=data.new_bot_token)
    webhook_url = f"{settings.WEBHOOK_HOST.rstrip('/')}/webhook/{data.shop_id}"
    try:
        await new_bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            secret_token=settings.ADMIN_SECRET[:32]
        )
    except Exception:
        pass
    finally:
        await new_bot.session.close()
    
    return {"status": "transferred", "new_owner": data.new_owner_id}

@router.delete("/api/delete_shop/{shop_id}")
async def delete_shop_completely(shop_id: str, x_admin_secret: str = Header(None)):
    if x_admin_secret != settings.ADMIN_SECRET: 
        raise HTTPException(403)
    
    supabase.table("shops").delete().eq("id", shop_id).execute()
    
    return {"status": "deleted", "id": shop_id}
