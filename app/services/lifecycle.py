from datetime import datetime, timezone
from app.core.database import supabase

async def check_expired_demos():
    now = datetime.now(timezone.utc).isoformat()
    
    response = supabase.table("shops").select("id").eq("status", "active").lt("trial_end", now).execute()
    expired_shops = response.data
    
    if not expired_shops:
        return 0
        
    count = 0
    for shop in expired_shops:
        supabase.table("shops").update({"status": "expired"}).eq("id", shop['id']).execute()
        count += 1
        
    return count

async def upgrade_shop(shop_id: str, new_tier: str) -> bool:
    if new_tier not in ["pro", "master"]:
        return False
        
    data = {
        "tier": new_tier,
        "trial_end": None,
        "status": "active"
    }
    
    try:
        supabase.table("shops").update(data).eq("id", shop_id).execute()
        return True
    except Exception:
        return False
