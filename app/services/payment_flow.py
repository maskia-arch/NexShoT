from app.core.database import supabase

async def create_order(shop_id: str, customer_id: int, cart_items: list, payment_method: str, customer_address: str) -> dict:
    product_ids = [item for item in cart_items]
    response = supabase.table("products").select("price").in_("id", product_ids).execute()
    
    total_amount = sum(float(p['price']) for p in response.data)
    
    order_data = {
        "shop_id": shop_id,
        "customer_telegram_id": customer_id,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "status": "pending",
        "tx_hash": customer_address
    }
    
    result = supabase.table("orders").insert(order_data).execute()
    return result.data[0] if result.data else None

async def get_payment_methods(shop_id: str) -> list:
    response = supabase.table("payment_configs").select("*").eq("shop_id", shop_id).eq("is_active", True).execute()
    return response.data

async def add_payment_method(shop_id: str, provider: str, details: dict) -> bool:
    data = {
        "shop_id": shop_id,
        "provider": provider,
        "details": details,
        "is_active": True
    }
    try:
        supabase.table("payment_configs").insert(data).execute()
        return True
    except Exception:
        return False
