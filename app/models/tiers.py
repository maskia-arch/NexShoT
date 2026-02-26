from pydantic import BaseModel

class TierLimits(BaseModel):
    products: int
    payments: int
    admins: int
    broadcasts_allowed: bool

class Tier(BaseModel):
    name: str
    limits: TierLimits
    days_valid: int
