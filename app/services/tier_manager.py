from app.core.database import supabase
from app.models.tiers import Tier, TierLimits

TIER_CONFIG = {
    "demo": Tier(
        name="demo",
        limits=TierLimits(products=3, payments=1, admins=0, broadcasts_allowed=False),
        days_valid=30
    ),
    "pro": Tier(
        name="pro",
        limits=TierLimits(products=30, payments=3, admins=0, broadcasts_allowed=True),
        days_valid=30
    ),
    "ultra": Tier(
        name="ultra",
        limits=TierLimits(products=9999, payments=99, admins=10, broadcasts_allowed=True),
        days_valid=365
    )
}

async def check_limit(shop_id: str, feature: str) -> bool:
    response = supabase.table("shops").select("tier").eq("id", shop_id).execute()
    if not response.data:
        return False
        
    tier_name = response.data[0]['tier']
    tier = TIER_CONFIG.get(tier_name, TIER_CONFIG['demo'])
    limits = tier.limits
    
    if feature == "products":
        count_res = supabase.table("products").select("id", count="exact").eq("shop_id", shop_id).execute()
        count = count_res.count if count_res.count is not None else 0
        return count < limits.products
        
    if feature == "payments":
        count_res = supabase.table("payment_configs").select("id", count="exact").eq("shop_id", shop_id).execute()
        count = count_res.count if count_res.count is not None else 0
        return count < limits.payments

    if feature == "admins":
        if limits.admins == 0:
            return False
        count_res = supabase.table("shop_admins").select("id", count="exact").eq("shop_id", shop_id).execute()
        count = count_res.count if count_res.count is not None else 0
        return count < limits.admins
        
    if feature == "broadcast":
        return limits.broadcasts_allowed

    return True

async def get_shop_tier_details(shop_id: str) -> Tier:
    response = supabase.table("shops").select("tier").eq("id", shop_id).execute()
    if not response.data:
        return TIER_CONFIG["demo"]
    
    tier_name = response.data[0]['tier']
    return TIER_CONFIG.get(tier_name, TIER_CONFIG.get("demo"))
